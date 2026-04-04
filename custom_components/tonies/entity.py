"""Base entity for Tonies integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ToniesCoordinator


class ToniesBaseEntity(CoordinatorEntity[ToniesCoordinator]):
    """Shared base for all Tonies entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ToniesCoordinator, box_id: str) -> None:
        super().__init__(coordinator)
        self._box_id = box_id

    @property
    def _box(self):
        return self.coordinator.get_box(self._box_id)

    @property
    def _ws(self) -> dict:
        return self.coordinator.get_ws_state(self._box_id)

    @property
    def is_tng(self) -> bool:
        """True if this box supports TNG (WebSocket, lightring, bedtime settings)."""
        box = self._box
        return getattr(box, "is_tng", False) if box else False

    @property
    def device_info(self) -> DeviceInfo:
        box = self._box
        return DeviceInfo(
            identifiers={(DOMAIN, self._box_id)},
            name=box.name if box else self._box_id,
            manufacturer="Boxine",
            model="Gen 2" if self.is_tng else "Gen 1",
        )
