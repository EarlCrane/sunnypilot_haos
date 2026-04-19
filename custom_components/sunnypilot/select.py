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
        self._param_type: str = param_meta.get("param_type", "Int")

    @property
    def current_option(self) -> str | None:
        val = self.current_value
        if val is None:
            return None
        if self._param_type == "Int":
            # Generic: API stores the index into options list
            if isinstance(val, int) and 0 <= val < len(self._attr_options):
                return self._attr_options[val]
            if isinstance(val, float):
                idx = int(val)
                if 0 <= idx < len(self._attr_options):
                    return self._attr_options[idx]
        # String-backed: match directly
        label = str(val)
        return label if label in self._attr_options else None

    async def async_select_option(self, option: str) -> None:
        if self._param_type == "Int":
            try:
                api_value: object = self._attr_options.index(option)
            except ValueError:
                _LOGGER.error("Option %r not in %s options", option, self._param_key)
                return
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
