"""Number platform for Tonies — volume and LED brightness controls."""
from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CLASSIC_VOLUME_STEPS, DATA_COORDINATOR, DOMAIN,
    UNIQUE_ID_NUMBER_HP_VOL, UNIQUE_ID_NUMBER_LED_BRIGHTNESS, UNIQUE_ID_NUMBER_VOLUME,
)
from .coordinator import ToniesCoordinator
from .entity import ToniesBaseEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ToniesCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    entities: list[NumberEntity] = []
    for box in coordinator.data.boxes:
        entities.append(HeadphoneVolumeNumber(coordinator, box.id))
        if getattr(box, "is_tng", False):
            entities.append(TngSpeakerVolumeNumber(coordinator, box.id))
            entities.append(TngLedBrightnessNumber(coordinator, box.id))
    async_add_entities(entities)


class HeadphoneVolumeNumber(ToniesBaseEntity, NumberEntity):
    """Max headphone volume.

    TNG  → free range 25-100
    Classic → snapped to 25, 50, 75, 100
    """

    _attr_name = "Max Headphone Volume"
    _attr_icon = "mdi:headphones"
    _attr_mode = NumberMode.SLIDER
    _attr_native_unit_of_measurement = "%"

    def __init__(self, coordinator: ToniesCoordinator, box_id: str) -> None:
        super().__init__(coordinator, box_id)
        self._attr_unique_id = f"{UNIQUE_ID_NUMBER_HP_VOL}_{box_id}"

    @property
    def native_min_value(self) -> float:
        return 25.0

    @property
    def native_max_value(self) -> float:
        return 100.0

    @property
    def native_step(self) -> float:
        return 1.0 if self.is_tng else 25.0

    @property
    def native_value(self) -> float | None:
        box = self._box
        return float(box.max_headphone_volume) if box else None

    async def async_set_native_value(self, value: float) -> None:
        box = self._box
        if box is None:
            return
        vol_int = round(value)
        if not self.is_tng:
            vol_int = min(CLASSIC_VOLUME_STEPS, key=lambda s: abs(s - vol_int))
        await self.coordinator.set_headphone_volume(box.household_id, box.id, vol_int)
        await self.coordinator.async_request_refresh()


class TngSpeakerVolumeNumber(ToniesBaseEntity, NumberEntity):
    """Max speaker volume — TNG only, 25-100% in 1% steps."""

    _attr_name = "Max Volume"
    _attr_icon = "mdi:volume-high"
    _attr_mode = NumberMode.SLIDER
    _attr_native_unit_of_measurement = "%"
    _attr_native_min_value = 25.0
    _attr_native_max_value = 100.0
    _attr_native_step = 1.0

    def __init__(self, coordinator: ToniesCoordinator, box_id: str) -> None:
        super().__init__(coordinator, box_id)
        self._attr_unique_id = f"{UNIQUE_ID_NUMBER_VOLUME}_{box_id}"

    @property
    def native_value(self) -> float | None:
        box = self._box
        return float(box.max_volume) if box else None

    async def async_set_native_value(self, value: float) -> None:
        box = self._box
        if box is None:
            return
        await self.coordinator.set_volume(box.household_id, box.id, round(value))
        await self.coordinator.async_request_refresh()


class TngLedBrightnessNumber(ToniesBaseEntity, NumberEntity):
    """Light ring brightness — TNG only, 0-100% in 1% steps."""

    _attr_name = "LED Brightness"
    _attr_icon = "mdi:led-on"
    _attr_mode = NumberMode.SLIDER
    _attr_native_unit_of_measurement = "%"
    _attr_native_min_value = 0.0
    _attr_native_max_value = 100.0
    _attr_native_step = 1.0

    def __init__(self, coordinator: ToniesCoordinator, box_id: str) -> None:
        super().__init__(coordinator, box_id)
        self._attr_unique_id = f"{UNIQUE_ID_NUMBER_LED_BRIGHTNESS}_{box_id}"

    @property
    def native_value(self) -> float | None:
        box = self._box
        if box is None or box.lightring_brightness is None:
            return None
        return float(box.lightring_brightness)

    async def async_set_native_value(self, value: float) -> None:
        box = self._box
        if box is None:
            return
        await self.coordinator.set_lightring_brightness(box.household_id, box.id, round(value))
        await self.coordinator.async_request_refresh()
