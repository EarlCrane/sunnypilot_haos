"""Switch platform for sunnypilot — Bool params."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
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
        SunnypilotSwitch(coordinator, key, meta)
        for key, meta in PARAM_REGISTRY.items()
        if meta["platform"] == "switch"
    ]
    async_add_entities(entities)


class SunnypilotSwitch(SunnypilotEntity, SwitchEntity):
    """A switch entity for a Bool sunnypilot param."""

    _attr_assumed_state = False

    @property
    def is_on(self) -> bool:
        val = self.current_value
        if val is None:
            return False
        return bool(val)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set(False)

    async def _set(self, value: bool) -> None:
        try:
            await self.hass.async_add_executor_job(
                self.coordinator.client.set_value,
                self.coordinator.device_id,
                self._param_key,
                value,
                "Bool",
            )
        except Exception as err:
            _LOGGER.error("Failed to set %s: %s", self._param_key, err)
            return
        await self.coordinator.async_request_refresh()
