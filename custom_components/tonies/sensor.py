"""Sensor platform for Tonies."""

from __future__ import annotations

import logging
import time

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DATA_COORDINATOR,
    DOMAIN,
    UNIQUE_ID_SENSOR_BATTERY,
    UNIQUE_ID_SENSOR_CHAPTER,
    UNIQUE_ID_SENSOR_ONLINE,
    UNIQUE_ID_SENSOR_TONIE,
)
from .coordinator import ToniesCoordinator
from .entity import ToniesBaseEntity

_LOGGER = logging.getLogger(__name__)


def _library_device_info(entry_id: str) -> DeviceInfo:
    """DeviceInfo for the virtual Tonies Library device."""
    return DeviceInfo(
        identifiers={(DOMAIN, f"tonies_library_{entry_id}")},
        name="Tonies Library",
        manufacturer="Boxine",
        entry_type=DeviceEntryType.SERVICE,
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ToniesCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    entities: list[SensorEntity] = []

    for box in coordinator.data.boxes:
        if getattr(box, "is_tng", False):
            entities += [
                TonieBatterySensor(coordinator, box.id),
                ToniesTonieSensor(coordinator, box.id),
                ToniesOnlineSensor(coordinator, box.id),
                ToniesChapterSensor(coordinator, box.id),
            ]
        else:
            _LOGGER.debug("Classic box %s: skipping real-time sensors", box.name)

    # Library device — count sensor + one entity per tonie
    entities.append(ToniesLibrarySensor(coordinator, entry.entry_id))

    for hwt in coordinator.data.households_with_tonies.values():
        for tonie in hwt.content_tonies or []:
            entities.append(ContentTonieSensor(coordinator, entry.entry_id, tonie))
        for tonie in hwt.creative_tonies or []:
            entities.append(CreativeTonieSensor(coordinator, entry.entry_id, tonie))

    async_add_entities(entities)


# ---------------------------------------------------------------------------
# TNG-only sensors (per box)
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
    def entity_picture(self) -> str | None:
        return self._ws.get("tonie_image") or None

    @property
    def extra_state_attributes(self) -> dict:
        ws = self._ws
        attrs: dict = {
            "tonie_id": ws.get("tonie_id"),
            "tonie_image_url": ws.get("tonie_image"),
            "chapter": ws.get("chapter"),
        }
        chapter_until_ms = ws.get("chapter_until_ms")
        chapter_duration = ws.get("chapter_duration")
        if chapter_until_ms is not None:
            remaining_s = max(0, chapter_until_ms / 1000 - time.time())
            attrs["chapter_remaining_s"] = round(remaining_s)
        if chapter_duration is not None:
            attrs["chapter_duration_s"] = round(chapter_duration)
        return attrs


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


class ToniesChapterSensor(ToniesBaseEntity, SensorEntity):
    """Current chapter number and duration — TNG only."""

    _attr_name = "Chapter"
    _attr_icon = "mdi:book-open-page-variant"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: ToniesCoordinator, box_id: str) -> None:
        super().__init__(coordinator, box_id)
        self._attr_unique_id = f"{UNIQUE_ID_SENSOR_CHAPTER}_{box_id}"

    @property
    def native_value(self) -> int | None:
        return self._ws.get("chapter")

    @property
    def extra_state_attributes(self) -> dict:
        ws = self._ws
        attrs: dict = {}
        chapter_duration = ws.get("chapter_duration")
        if chapter_duration is not None:
            attrs["chapter_duration_s"] = round(chapter_duration)
        chapter_until_ms = ws.get("chapter_until_ms")
        if chapter_until_ms is not None:
            remaining_s = max(0, chapter_until_ms / 1000 - time.time())
            attrs["chapter_remaining_s"] = round(remaining_s)
        return attrs


# ---------------------------------------------------------------------------
# Tonies Library device — virtual device grouping all tonies
# ---------------------------------------------------------------------------


class ToniesLibrarySensor(SensorEntity):
    """Count sensor for the library device (total tonies owned)."""

    _attr_has_entity_name = True
    _attr_name = "Count"
    _attr_icon = "mdi:bookshelf"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: ToniesCoordinator, entry_id: str) -> None:
        super().__init__()
        self._coordinator = coordinator
        self._entry_id = entry_id
        self._attr_unique_id = f"tonies_library_{entry_id}"

    @property
    def device_info(self) -> DeviceInfo:
        return _library_device_info(self._entry_id)

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
            "content_count": sum(1 for t in tonies if t.get("type") == "content"),
            "creative_count": sum(1 for t in tonies if t.get("type") == "creative"),
        }

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self._coordinator.async_add_listener(self.async_write_ha_state)
        )


class ContentTonieSensor(CoordinatorEntity[ToniesCoordinator], SensorEntity):
    """One sensor per content tonie (physical figurine from the catalogue)."""

    _attr_has_entity_name = False
    _attr_icon = "mdi:music-box"

    def __init__(self, coordinator: ToniesCoordinator, entry_id: str, tonie) -> None:
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._tonie_id = tonie.id
        self._attr_unique_id = f"tonies_content_{tonie.id}"
        self._attr_name = tonie.title

    @property
    def device_info(self) -> DeviceInfo:
        return _library_device_info(self._entry_id)

    @property
    def _tonie(self):
        for hwt in self.coordinator.data.households_with_tonies.values():
            for t in hwt.content_tonies or []:
                if t.id == self._tonie_id:
                    return t
        return None

    @property
    def native_value(self) -> str | None:
        t = self._tonie
        return t.title if t else None

    @property
    def entity_picture(self) -> str | None:
        t = self._tonie
        return t.image_url if t else None

    @property
    def extra_state_attributes(self) -> dict:
        t = self._tonie
        if t is None:
            return {}
        return {
            "tonie_id": t.id,
            "cover_url": t.cover_url,
            "series": t.series.name if t.series else None,
        }


class CreativeTonieSensor(CoordinatorEntity[ToniesCoordinator], SensorEntity):
    """One sensor per creative tonie (recordable figurine)."""

    _attr_has_entity_name = False
    _attr_icon = "mdi:microphone"

    def __init__(self, coordinator: ToniesCoordinator, entry_id: str, tonie) -> None:
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._tonie_id = tonie.id
        self._attr_unique_id = f"tonies_creative_{tonie.id}"
        self._attr_name = tonie.name

    @property
    def device_info(self) -> DeviceInfo:
        return _library_device_info(self._entry_id)

    @property
    def _tonie(self):
        for hwt in self.coordinator.data.households_with_tonies.values():
            for t in hwt.creative_tonies or []:
                if t.id == self._tonie_id:
                    return t
        return None

    @property
    def native_value(self) -> str | None:
        t = self._tonie
        return t.name if t else None

    @property
    def entity_picture(self) -> str | None:
        t = self._tonie
        return t.image_url if t else None

    @property
    def extra_state_attributes(self) -> dict:
        t = self._tonie
        if t is None:
            return {}
        return {
            "tonie_id": t.id,
            "live": t.live,
            "chapters": len(t.chapters or []),
        }
