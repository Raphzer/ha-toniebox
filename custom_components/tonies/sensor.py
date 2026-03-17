"""Sensor platform for Tonies."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass, SensorEntity, SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import EntityCategory

from .const import (
    DATA_COORDINATOR, DOMAIN,
    UNIQUE_ID_SENSOR_BATTERY, UNIQUE_ID_SENSOR_ONLINE, UNIQUE_ID_SENSOR_TONIE,
)
from .coordinator import ToniesCoordinator
from .entity import ToniesBaseEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ToniesCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    entities: list[SensorEntity] = []

    for box in coordinator.data.boxes:
        if getattr(box, "is_tng", False):
            # TNG only: real-time sensors
            entities += [
                TonieBatterySensor(coordinator, box.id),
                ToniesTonieSensor(coordinator, box.id),
                ToniesOnlineSensor(coordinator, box.id),
            ]
        else:
            _LOGGER.debug("Classic box %s: skipping real-time sensors", box.name)

    # Tonies catalogue sensor — one global sensor per integration entry
    entities.append(ToniesLibrarySensor(coordinator, entry.entry_id))

    async_add_entities(entities)


# ---------------------------------------------------------------------------
# TNG-only sensors
# ---------------------------------------------------------------------------

class TonieBatterySensor(ToniesBaseEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_name = "Battery"

    def __init__(self, coordinator: ToniesCoordinator, box_id: str) -> None:
        super().__init__(coordinator, box_id)
        self._attr_unique_id = f"{UNIQUE_ID_SENSOR_BATTERY}_{box_id}"

    @property
    def native_value(self) -> int | None:
        return self._ws.get("battery")

    @property
    def extra_state_attributes(self) -> dict:
        return {"charging": self._ws.get("charging", False)}


class ToniesTonieSensor(ToniesBaseEntity, SensorEntity):
    _attr_name = "Active Tonie"
    _attr_icon = "mdi:toy-brick"

    def __init__(self, coordinator: ToniesCoordinator, box_id: str) -> None:
        super().__init__(coordinator, box_id)
        self._attr_unique_id = f"{UNIQUE_ID_SENSOR_TONIE}_{box_id}"

    @property
    def native_value(self) -> str | None:
        return self._ws.get("tonie_name")

    @property
    def extra_state_attributes(self) -> dict:
        ws = self._ws
        return {
            "tonie_id":        ws.get("tonie_id"),
            "tonie_image_url": ws.get("tonie_image"),
        }


class ToniesOnlineSensor(ToniesBaseEntity, SensorEntity):
    _attr_name = "Connection"
    _attr_icon = "mdi:wifi"

    def __init__(self, coordinator: ToniesCoordinator, box_id: str) -> None:
        super().__init__(coordinator, box_id)
        self._attr_unique_id = f"{UNIQUE_ID_SENSOR_ONLINE}_{box_id}"

    @property
    def native_value(self) -> str:
        online = self._ws.get("online")
        if online is None:
            return "unknown"
        return "online" if online else "offline"


# ---------------------------------------------------------------------------
# Tonies library sensor — all boxes, attached to first box device (or standalone)
# ---------------------------------------------------------------------------

class ToniesLibrarySensor(SensorEntity):
    """Global sensor showing Tonies counts.

    State = total count.
    Attributes = counts only (no full list — too large for HA DB).
    Use the service tonies.get_tonies_list to retrieve the full catalogue.
    """
    _attr_has_entity_name = True
    _attr_name = "Tonies Library"
    _attr_icon = "mdi:bookshelf"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: ToniesCoordinator, entry_id: str) -> None:
        self._coordinator = coordinator
        self._entry_id = entry_id
        self._attr_unique_id = f"tonies_library_{entry_id}"

    @property
    def should_poll(self) -> bool:
        return False

    @property
    def native_value(self) -> int:
        return len(self._coordinator.get_all_tonies())

    @property
    def extra_state_attributes(self) -> dict:
        tonies = self._coordinator.get_all_tonies()
        return {
            "content_count":  sum(1 for t in tonies if t.get("type") == "content"),
            "creative_count": sum(1 for t in tonies if t.get("type") == "creative"),
        }

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self._coordinator.async_add_listener(self.async_write_ha_state)
        )