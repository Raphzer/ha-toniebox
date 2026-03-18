"""Media player platform for Tonies."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ATTR_HEADPHONES,
    ATTR_HOUSEHOLD_ID,
    ATTR_MAC_ADDRESS,
    ATTR_TONIE_ID,
    ATTR_TONIE_IMAGE,
    ATTR_TONIE_NAME,
    CLASSIC_VOLUME_STEPS,
    DATA_COORDINATOR,
    DOMAIN,
    UNIQUE_ID_MEDIA_PLAYER,
)
from .coordinator import ToniesCoordinator
from .entity import ToniesBaseEntity

_LOGGER = logging.getLogger(__name__)

# TNG: volume libre + turn_off via WebSocket sleep
_FEATURES_TNG = (
    MediaPlayerEntityFeature.VOLUME_SET
    | MediaPlayerEntityFeature.VOLUME_STEP
    | MediaPlayerEntityFeature.TURN_OFF
)
# Classic: volume par paliers uniquement, pas de sleep
_FEATURES_CLASSIC = (
    MediaPlayerEntityFeature.VOLUME_SET | MediaPlayerEntityFeature.VOLUME_STEP
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ToniesCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities(
        [ToniesMediaPlayer(coordinator, b.id) for b in coordinator.data.boxes]
    )


class ToniesMediaPlayer(ToniesBaseEntity, MediaPlayerEntity):
    """Toniebox as a HA media player.

    TNG  → real-time state, free volume (25-100), sleep command, tonie art
    Classic → always IDLE, volume snapped to 25/50/75/100, no sleep
    """

    def __init__(self, coordinator: ToniesCoordinator, box_id: str) -> None:
        super().__init__(coordinator, box_id)
        self._attr_unique_id = f"{UNIQUE_ID_MEDIA_PLAYER}_{box_id}"
        self._attr_name = None  # device name is used directly

    @property
    def supported_features(self) -> MediaPlayerEntityFeature:
        return _FEATURES_TNG if self.is_tng else _FEATURES_CLASSIC

    @property
    def entity_picture(self) -> str | None:
        """Show tonie art when playing (TNG), otherwise box image."""
        if self.is_tng:
            tonie_img = self._ws.get("tonie_image")
            if tonie_img:
                return tonie_img
        box = self._box
        return box.image_url if box else None

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    @property
    def state(self) -> MediaPlayerState:
        if not self.is_tng:
            return MediaPlayerState.IDLE
        ws = self._ws
        if not ws.get("online", True):
            return MediaPlayerState.OFF
        if ws.get("tonie_id"):
            return MediaPlayerState.PLAYING
        return MediaPlayerState.IDLE

    @property
    def volume_level(self) -> float | None:
        box = self._box
        if box is None:
            return None
        return box.max_volume / 100.0

    @property
    def media_title(self) -> str | None:
        return self._ws.get("tonie_name") if self.is_tng else None

    @property
    def media_image_url(self) -> str | None:
        return self._ws.get("tonie_image") if self.is_tng else None

    @property
    def media_content_id(self) -> str | None:
        return self._ws.get("tonie_id") if self.is_tng else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        box = self._box
        attrs: dict[str, Any] = {"tng": self.is_tng}
        if box:
            attrs[ATTR_HOUSEHOLD_ID] = box.household_id
            attrs[ATTR_MAC_ADDRESS] = box.mac_address
        if self.is_tng:
            ws = self._ws
            attrs[ATTR_TONIE_ID] = ws.get("tonie_id")
            attrs[ATTR_TONIE_NAME] = ws.get("tonie_name")
            attrs[ATTR_TONIE_IMAGE] = ws.get("tonie_image")
            attrs[ATTR_HEADPHONES] = ws.get("headphones", False)
        return attrs

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    async def async_set_volume_level(self, volume: float) -> None:
        box = self._box
        if box is None:
            return
        vol_int = round(volume * 100)
        if not self.is_tng:
            # Snap to nearest Classic step: 25, 50, 75, 100
            vol_int = min(CLASSIC_VOLUME_STEPS, key=lambda s: abs(s - vol_int))
        await self.coordinator.set_volume(box.household_id, box.id, vol_int)
        await self.coordinator.async_request_refresh()

    async def async_volume_up(self) -> None:
        box = self._box
        if box is None:
            return
        current = box.max_volume
        if not self.is_tng:
            higher = [s for s in CLASSIC_VOLUME_STEPS if s > current]
            new_vol = higher[0] if higher else CLASSIC_VOLUME_STEPS[-1]
        else:
            new_vol = min(100, current + 5)
        await self.coordinator.set_volume(box.household_id, box.id, new_vol)
        await self.coordinator.async_request_refresh()

    async def async_volume_down(self) -> None:
        box = self._box
        if box is None:
            return
        current = box.max_volume
        if not self.is_tng:
            lower = [s for s in CLASSIC_VOLUME_STEPS if s < current]
            new_vol = lower[-1] if lower else CLASSIC_VOLUME_STEPS[0]
        else:
            new_vol = max(25, current - 5)
        await self.coordinator.set_volume(box.household_id, box.id, new_vol)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self) -> None:
        """Sleep command — TNG only."""
        if not self.is_tng:
            return
        box = self._box
        if box:
            await self.coordinator.sleep_box(box.mac_address)
