"""The Tonies integration."""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DATA_COORDINATOR, DOMAIN, PLATFORMS
from .coordinator import ToniesCoordinator

_LOGGER = logging.getLogger(__name__)

SERVICE_GET_TONIES_LIST = "get_tonies_list"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tonies from a config entry."""
    coordinator = ToniesCoordinator(hass, entry)

    try:
        await coordinator.async_setup()
    except Exception as err:
        raise ConfigEntryNotReady(f"Failed to set up Tonies integration: {err}") from err

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {DATA_COORDINATOR: coordinator}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # ── Service : tonies.get_tonies_list ─────────────────────────────────────
    # Retourne la liste complète via un event de réponse plutôt que des attributs
    # (les attributs HA sont limités à 16KB — la liste peut dépasser cette limite).

    async def handle_get_tonies_list(call: ServiceCall) -> None:
        """Fire a tonies_list event with the full catalogue."""
        all_tonies: list[dict] = []
        for entry_data in hass.data.get(DOMAIN, {}).values():
            coord: ToniesCoordinator = entry_data.get(DATA_COORDINATOR)
            if coord:
                all_tonies.extend(coord.get_all_tonies())

        hass.bus.async_fire(
            f"{DOMAIN}_list_result",
            {
                "total":          len(all_tonies),
                "content_count":  sum(1 for t in all_tonies if t.get("type") == "content"),
                "creative_count": sum(1 for t in all_tonies if t.get("type") == "creative"),
                "tonies":         all_tonies,
            },
        )
        _LOGGER.debug("Fired %s_list_result with %d tonies", DOMAIN, len(all_tonies))

    if not hass.services.has_service(DOMAIN, SERVICE_GET_TONIES_LIST):
        hass.services.async_register(
            DOMAIN,
            SERVICE_GET_TONIES_LIST,
            handle_get_tonies_list,
            schema=vol.Schema({}),
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        coordinator: ToniesCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
        await coordinator.async_teardown()
        hass.data[DOMAIN].pop(entry.entry_id)

        # Déregistre le service si plus aucune entrée active
        if not hass.data.get(DOMAIN):
            hass.services.async_remove(DOMAIN, SERVICE_GET_TONIES_LIST)

    return unload_ok