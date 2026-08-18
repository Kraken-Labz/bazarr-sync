"""Binary sensor platform for Bazarr integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import BazarrDataUpdateCoordinator
from .entity import BazarrEntity
from .types import BazarrConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BazarrConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Bazarr binary sensors based on a config entry."""
    coordinator = entry.runtime_data

    async_add_entities([BazarrHealthIssuesBinarySensor(coordinator, entry)])


class BazarrHealthIssuesBinarySensor(BazarrEntity, BinarySensorEntity):
    """Binary sensor for Bazarr health issues."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_translation_key = "health"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: BazarrDataUpdateCoordinator,
        entry: BazarrConfigEntry,
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_health_issues"

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data:
            health_issues = self.coordinator.data.get("health_issues", [])
            return bool(health_issues)
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.coordinator.data:
            health_issues = self.coordinator.data.get("health_issues", [])
            return {"issues": health_issues}
        return None
