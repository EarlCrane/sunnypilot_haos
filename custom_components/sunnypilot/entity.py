"""Base entity for sunnypilot."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SunnypilotCoordinator


class SunnypilotEntity(CoordinatorEntity[SunnypilotCoordinator]):
    """Base class for all sunnypilot entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SunnypilotCoordinator,
        param_key: str,
        param_meta: dict,
    ) -> None:
        super().__init__(coordinator)
        self._param_key = param_key
        self._attr_name = param_meta["name"]
        self._attr_icon = param_meta.get("icon", "mdi:car-connected")
        self._attr_unique_id = f"{coordinator.device_id}_{param_key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.device_id)},
            name="sunnypilot",
            manufacturer="sunnypilot",
            model="comma device",
        )

    @property
    def current_value(self) -> object:
        return (self.coordinator.data or {}).get(self._param_key)
