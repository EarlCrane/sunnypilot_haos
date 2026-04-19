"""Number platform for sunnypilot — Int/Float params."""
from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, PARAM_REGISTRY
from .coordinator import SunnypilotCoordinator
from .entity import SunnypilotEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SunnypilotCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        SunnypilotNumber(coordinator, key, meta)
        for key, meta in PARAM_REGISTRY.items()
        if meta["platform"] == "number"
    ]
    async_add_entities(entities)


class SunnypilotNumber(SunnypilotEntity, NumberEntity):
    """A number entity for an Int/Float sunnypilot param."""

    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: SunnypilotCoordinator, param_key: str, param_meta: dict) -> None:
        super().__init__(coordinator, param_key, param_meta)
        self._attr_native_min_value = float(param_meta.get("min", 0))
        self._attr_native_max_value = float(param_meta.get("max", 100))
        self._attr_native_step = float(param_meta.get("step", 1))
        # Use Float type if step has decimals, otherwise Int
        self._param_type = "Float" if self._attr_native_step < 1 else "Int"

    @property
    def native_value(self) -> float | None:
        val = self.current_value
        if val is None:
            return None
        try:
            return float(val)
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        api_value = value if self._param_type == "Float" else int(value)
        try:
            await self.hass.async_add_executor_job(
                self.coordinator.client.set_value,
                self.coordinator.device_id,
                self._param_key,
                api_value,
                self._param_type,
            )
        except Exception as err:
            _LOGGER.error("Failed to set %s to %s: %s", self._param_key, value, err)
            return
        await self.coordinator.async_request_refresh()
