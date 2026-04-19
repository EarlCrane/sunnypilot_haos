"""Select platform for sunnypilot — enum params."""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, PARAM_REGISTRY
from .coordinator import SunnypilotCoordinator
from .entity import SunnypilotEntity

_LOGGER = logging.getLogger(__name__)

# LongitudinalPersonality API values are integers 0/1/2.
# Map label → int for writes, int → label for reads.
_PERSONALITY_BY_LABEL: dict[str, int] = {"Relaxed": 0, "Standard": 1, "Aggressive": 2}
_PERSONALITY_BY_VALUE: dict[int, str] = {v: k for k, v in _PERSONALITY_BY_LABEL.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SunnypilotCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        SunnypilotSelect(coordinator, key, meta)
        for key, meta in PARAM_REGISTRY.items()
        if meta["platform"] == "select" and meta.get("options")
    ]
    async_add_entities(entities)


class SunnypilotSelect(SunnypilotEntity, SelectEntity):
    """A select entity for an enum sunnypilot param."""

    def __init__(self, coordinator: SunnypilotCoordinator, param_key: str, param_meta: dict) -> None:
        super().__init__(coordinator, param_key, param_meta)
        self._attr_options = list(param_meta.get("options", []))
        self._param_type: str = param_meta.get("param_type", "String")

    @property
    def current_option(self) -> str | None:
        val = self.current_value
        if val is None:
            return None
        # Int-backed selects: map value → label
        if self._param_type == "Int" and isinstance(val, int):
            if self._param_key == "LongitudinalPersonality":
                return _PERSONALITY_BY_VALUE.get(val)
        return str(val) if str(val) in self._attr_options else None

    async def async_select_option(self, option: str) -> None:
        # Resolve label → API value
        if self._param_type == "Int":
            if self._param_key == "LongitudinalPersonality":
                api_value = _PERSONALITY_BY_LABEL.get(option, 1)
            else:
                try:
                    api_value = int(option)
                except ValueError:
                    api_value = option
        else:
            api_value = option

        try:
            await self.hass.async_add_executor_job(
                self.coordinator.client.set_value,
                self.coordinator.device_id,
                self._param_key,
                api_value,
                self._param_type,
            )
        except Exception as err:
            _LOGGER.error("Failed to set %s to %s: %s", self._param_key, option, err)
            return
        await self.coordinator.async_request_refresh()
