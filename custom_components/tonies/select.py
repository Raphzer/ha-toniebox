"""Select platform for Tonies — LED control (all boxes)."""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATOR, DOMAIN, LED_OPTIONS, UNIQUE_ID_SELECT_LED
from .coordinator import ToniesCoordinator
from .entity import ToniesBaseEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ToniesCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities([ToniesLedSelect(coordinator, b.id) for b in coordinator.data.boxes])


class ToniesLedSelect(ToniesBaseEntity, SelectEntity):
    """LED brightness selector — available on all boxes (Classic & TNG)."""

    _attr_name = "LED"
    _attr_icon = "mdi:led-on"
    _attr_options = LED_OPTIONS  # ["on", "dimmed", "off"]

    def __init__(self, coordinator: ToniesCoordinator, box_id: str) -> None:
        super().__init__(coordinator, box_id)
        self._attr_unique_id = f"{UNIQUE_ID_SELECT_LED}_{box_id}"

    @property
    def current_option(self) -> str | None:
        """led_level is a str field on the Toniebox model."""
        box = self._box
        if box is None:
            return None
        val = getattr(box, "led_level", None)
        return str(val).lower() if val is not None else None

    async def async_select_option(self, option: str) -> None:
        box = self._box
        if box is None:
            return
        await self.coordinator.set_led(box.household_id, box.id, option)
        await self.coordinator.async_request_refresh()
