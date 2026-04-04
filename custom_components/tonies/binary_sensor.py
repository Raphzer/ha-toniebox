"""Binary sensor platform for Tonies — connectivity (TNG only)."""

from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATOR, DOMAIN, UNIQUE_ID_SENSOR_ONLINE
from .coordinator import ToniesCoordinator
from .entity import ToniesBaseEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ToniesCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities(
        [
            ToniesOnlineBinarySensor(coordinator, b.id)
            for b in coordinator.data.boxes
            if getattr(b, "is_tng", False)
        ]
    )


class ToniesOnlineBinarySensor(ToniesBaseEntity, BinarySensorEntity):
    _attr_name = "Connection"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator: ToniesCoordinator, box_id: str) -> None:
        super().__init__(coordinator, box_id)
        self._attr_unique_id = f"{UNIQUE_ID_SENSOR_ONLINE}_{box_id}"

    @property
    def is_on(self) -> bool | None:
        online = self._ws.get("online")
        if online is None:
            return None
        return online
