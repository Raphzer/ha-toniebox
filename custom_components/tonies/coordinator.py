"""Data coordinator for Tonies integration."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from tonies_api.client import TonieAPIClient
from tonies_api.exceptions import ToniesApiError

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_PASSWORD, CONF_USERNAME, DOMAIN, POLLING_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)


class ToniesData:
    """Container for all Tonies data."""

    def __init__(self) -> None:
        self.boxes: list[Any] = []
        # dict[household_id] -> HouseholdWithTonies
        self.households_with_tonies: dict[str, Any] = {}
        # dict[box_id] -> real-time state pushed by WebSocket
        self.ws_state: dict[str, dict] = {}


class ToniesCoordinator(DataUpdateCoordinator[ToniesData]):
    """Central coordinator — polling + WebSocket lifecycle."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=POLLING_INTERVAL_SECONDS),
        )
        self._entry = entry
        self._client: TonieAPIClient | None = None
        self._ws_task: asyncio.Task | None = None
        self.data = ToniesData()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def async_setup(self) -> None:
        """Instantiate the API client (blocking SSL init → thread pool) and boot."""
        username = self._entry.data[CONF_USERNAME]
        password = self._entry.data[CONF_PASSWORD]

        self._client = await self.hass.async_add_executor_job(
            TonieAPIClient, username, password
        )
        await self._client.__aenter__()
        self._client.ws.register_callback(self._on_ws_event)

        await self._async_update_data()

        self._ws_task = self.hass.async_create_background_task(
            self._ws_listener(), "tonies_ws_listener"
        )

    async def async_teardown(self) -> None:
        """Shut down WebSocket and API client."""
        if self._ws_task:
            self._ws_task.cancel()
            try:
                await self._ws_task
            except asyncio.CancelledError:
                pass

        if self._client:
            try:
                await self._client.ws.disconnect()
            except Exception:
                pass
            await self._client.__aexit__(None, None, None)
            self._client = None

    # ------------------------------------------------------------------
    # Polling
    # ------------------------------------------------------------------

    async def _async_update_data(self) -> ToniesData:
        if self._client is None:
            raise UpdateFailed("API client not initialised")
        try:
            self.data.boxes = await self._client.tonies.get_households_boxes()
            _LOGGER.debug(
                "Fetched %d box(es): %s",
                len(self.data.boxes),
                [b.name for b in self.data.boxes],
            )

            households = await self._client.tonies.get_tonies()
            _LOGGER.debug("Fetched %d household(s)", len(households))

            # HouseholdWithTonies extends Household — the id field IS the household id
            self.data.households_with_tonies = {h.id: h for h in households}

            for hwt in households:
                _LOGGER.debug(
                    "Household '%s': %d content tonie(s), %d creative tonie(s)",
                    hwt.name,
                    len(hwt.content_tonies or []),
                    len(hwt.creative_tonies or []),
                )

        except ToniesApiError as err:
            raise UpdateFailed(f"Tonies API error: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}") from err
        return self.data

    # ------------------------------------------------------------------
    # WebSocket lifecycle — TNG boxes only
    # ------------------------------------------------------------------

    async def _ws_connect(self) -> None:
        """Connect with non-blocking SSL — certifi certs loaded in thread pool."""
        import certifi

        def _read_certs() -> bytes:
            with open(certifi.where(), "rb") as f:
                return f.read()

        certs_data: bytes = await self.hass.async_add_executor_job(_read_certs)

        import ssl

        _orig = ssl.create_default_context

        def _patched(*args, **kwargs):
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ctx.verify_mode = ssl.CERT_REQUIRED
            ctx.check_hostname = True
            ctx.load_verify_locations(cadata=certs_data.decode("utf-8"))
            ctx.set_default_verify_paths = lambda: None
            ctx.load_default_certs = lambda purpose=None: None
            return ctx

        ssl.create_default_context = _patched
        try:
            await self._client.ws.connect()
        finally:
            ssl.create_default_context = _orig

    async def _ws_listener(self) -> None:
        """Keep WebSocket alive; reconnection is handled by the lib itself."""
        while True:
            try:
                await self._ws_connect()
                _LOGGER.debug("Tonies WebSocket connected")

                tng_count = 0
                for box in self.data.boxes:
                    subscribed = await self._client.ws.subscribe_to_toniebox(box)
                    if subscribed:
                        tng_count += 1
                        _LOGGER.debug("WS subscribed: %s", box.name)

                if tng_count == 0:
                    _LOGGER.debug("No TNG boxes — WebSocket listener idle")

                # The lib handles reconnection internally; we just keep the task alive
                while True:
                    await asyncio.sleep(60)

            except asyncio.CancelledError:
                _LOGGER.debug("Tonies WS listener cancelled")
                return
            except Exception as err:
                _LOGGER.warning("Tonies WS error, retrying in 30s: %s", err)
                await asyncio.sleep(30)

    # ------------------------------------------------------------------
    # WebSocket event handler
    # ------------------------------------------------------------------

    @callback
    def _on_ws_event(self, topic: str, payload: Any) -> None:
        """Dispatch MQTT events to the correct box state dict."""
        # Topic: external/toniebox/{mac_address}/{event_suffix}
        parts = topic.split("/")
        if len(parts) < 4:
            return

        mac = parts[2]
        event = "/".join(parts[3:])

        box = next((b for b in self.data.boxes if b.mac_address == mac), None)
        if box is None:
            return

        box_id = box.id
        state = self.data.ws_state.setdefault(box_id, {})

        _LOGGER.debug("WS [%s] %s → %s", box.name, event, payload)

        if "online-state" in event:
            # payload: {'onlineState': 'online'|'connected'} or {'onlineState': 'offline'}
            _ONLINE_VALUES = {"online", "connected"}
            if isinstance(payload, dict):
                state["online"] = (
                    str(payload.get("onlineState", "")).lower() in _ONLINE_VALUES
                )
            elif isinstance(payload, str):
                state["online"] = payload.lower() in _ONLINE_VALUES
            else:
                state["online"] = bool(payload)

        elif "metrics/battery" in event:
            # payload: {'percent': 80, 'charging': False}
            if isinstance(payload, dict):
                pct = payload.get("percent")
                state["battery"] = int(pct) if pct is not None else None
                state["charging"] = bool(payload.get("charging", False))
            elif payload is not None:
                state["battery"] = int(payload)

        elif "playback/state" in event:
            # payload: {'tonie': {'id': '...', 'name': '...', 'imageUrl': '...'}}
            # or payload: {'tonie': '<id_string>'} (TNG compact format)
            # or payload: {'tonie': None} when removed
            _LOGGER.debug("Playback raw payload: %s", payload)
            if isinstance(payload, dict):
                tonie = payload.get("tonie")
                if isinstance(tonie, dict):
                    state["tonie_id"] = tonie.get("id")
                    state["tonie_name"] = tonie.get("name") or tonie.get("tonieName")
                    state["tonie_image"] = tonie.get("imageUrl") or tonie.get("image")
                elif isinstance(tonie, str):
                    # Compact format: tonie is just the ID string — look up name/image
                    state["tonie_id"] = tonie
                    found = self._find_tonie_by_id(tonie)
                    state["tonie_name"] = found.get("name") if found else tonie
                    state["tonie_image"] = found.get("image_url") if found else None
                elif tonie is None:
                    state["tonie_id"] = None
                    state["tonie_name"] = None
                    state["tonie_image"] = None

        elif "metrics/headphones" in event:
            # payload: {'connected': True}
            if isinstance(payload, dict):
                state["headphones"] = bool(payload.get("connected", False))
            else:
                state["headphones"] = bool(payload)

        self.async_set_updated_data(self.data)

    # ------------------------------------------------------------------
    # Helpers for entities
    # ------------------------------------------------------------------

    def _find_tonie_by_id(self, tonie_id: str) -> dict | None:
        """Look up a tonie by ID across all households. Returns the tonie dict or None."""
        for t in self.get_all_tonies():
            if t.get("id") == tonie_id:
                return t
        return None

    def get_box(self, box_id: str) -> Any | None:
        return next((b for b in self.data.boxes if b.id == box_id), None)

    def get_ws_state(self, box_id: str) -> dict:
        return self.data.ws_state.get(box_id, {})

    def get_all_tonies(self) -> list[dict]:
        """Return a flat list of all Tonies across all households.

        HouseholdWithTonies(Household) has:
          .id               — household id
          .content_tonies   — List[ContentTonie]
          .creative_tonies  — List[CreativeTonie]
        """
        result = []
        for hwt in self.data.households_with_tonies.values():
            household_id = hwt.id
            for tonie in hwt.content_tonies or []:
                # ContentTonie uses .title (not .name)
                result.append(
                    {
                        "id": tonie.id,
                        "name": tonie.title,
                        "image_url": tonie.image_url,
                        "cover_url": tonie.cover_url,
                        "household_id": household_id,
                        "type": "content",
                    }
                )
            for tonie in hwt.creative_tonies or []:
                # CreativeTonie uses .name
                result.append(
                    {
                        "id": tonie.id,
                        "name": tonie.name,
                        "image_url": tonie.image_url,
                        "household_id": household_id,
                        "type": "creative",
                        "live": tonie.live,
                    }
                )
        return result

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    async def sleep_box(self, mac_address: str) -> None:
        """Send sleep command (TNG only)."""
        if self._client is None:
            raise RuntimeError("API client not initialised")
        await self._client.ws.sleep_now(mac_address)

    async def set_volume(self, household_id: str, box_id: str, volume: int) -> None:
        """Set max speaker volume. Classic: snapped to 25/50/75/100."""
        if self._client is None:
            raise RuntimeError("API client not initialised")
        await self._client.tonies.set_max_volume(household_id, box_id, volume)

    async def set_headphone_volume(
        self, household_id: str, box_id: str, volume: int
    ) -> None:
        """Set max headphone volume. Classic: snapped to 25/50/75/100."""
        if self._client is None:
            raise RuntimeError("API client not initialised")
        await self._client.tonies.set_max_headphone_volume(household_id, box_id, volume)

    async def set_led(self, household_id: str, box_id: str, level: str) -> None:
        """Set LED brightness: on | dimmed | off."""
        if self._client is None:
            raise RuntimeError("API client not initialised")
        await self._client.tonies.set_led_brightness(household_id, box_id, level)

    # TNG-only commands
    async def set_lightring_brightness(
        self, household_id: str, box_id: str, brightness: int
    ) -> None:
        if self._client is None:
            raise RuntimeError("API client not initialised")
        await self._client.tonies.set_lightring_brightness(
            household_id, box_id, brightness
        )

    async def set_bedtime_volume(
        self, household_id: str, box_id: str, volume: int
    ) -> None:
        if self._client is None:
            raise RuntimeError("API client not initialised")
        await self._client.tonies.set_bedtime_max_volume(household_id, box_id, volume)

    async def set_bedtime_headphone_volume(
        self, household_id: str, box_id: str, volume: int
    ) -> None:
        if self._client is None:
            raise RuntimeError("API client not initialised")
        await self._client.tonies.set_bedtime_headphone_max_volume(
            household_id, box_id, volume
        )

    async def set_bedtime_lightring_brightness(
        self, household_id: str, box_id: str, brightness: int
    ) -> None:
        if self._client is None:
            raise RuntimeError("API client not initialised")
        await self._client.tonies.set_bedtime_lightring_brightness(
            household_id, box_id, brightness
        )
