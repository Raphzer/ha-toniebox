"""Switch platform for Tonies — sleep command (TNG only)."""
from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATOR, DOMAIN, UNIQUE_ID_SWITCH_SLEEP
from .coordinator import ToniesCoordinator
from .entity import ToniesBaseEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ToniesCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    entities = [
        TonieSleepSwitch(coordinator, b.id)
        for b in coordinator.data.boxes
        if getattr(b, "is_tng", False)
    ]
    async_add_entities(entities)


class TonieSleepSwitch(ToniesBaseEntity, SwitchEntity):
    """One-shot switch that sends a sleep command (TNG only)."""

    _attr_name = "Sleep"
    _attr_icon = "mdi:sleep"

    def __init__(self, coordinator: ToniesCoordinator, box_id: str) -> None:
        super().__init__(coordinator, box_id)
        self._attr_unique_id = f"{UNIQUE_ID_SWITCH_SLEEP}_{box_id}"
        self._is_on = False

    @property
    def is_on(self) -> bool:
        return self._is_on

    async def async_turn_on(self, **kwargs) -> None:
        box = self._box
        if box is None:
            return
        _LOGGER.info("Sleep → %s", box.name)
        await self.coordinator.sleep_box(box.mac_address)
        self._is_on = True
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
        self._is_on = False
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        self._is_on = False
        self.async_write_ha_state()
