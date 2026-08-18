"""Base entity for Bazarr Sync integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import BazarrSyncConfigEntry
from .const import DOMAIN
from .coordinator import BazarrDataUpdateCoordinator


class BazarrEntity(CoordinatorEntity[BazarrDataUpdateCoordinator]):
    """Base entity for Bazarr Sync integration."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BazarrDataUpdateCoordinator,
        entry: BazarrSyncConfigEntry,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._entry = entry

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this Bazarr Sync instance."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name="Bazarr Sync",
            manufacturer="Bazarr",
            configuration_url=self._entry.data["url"],
            sw_version=self.coordinator.data.get("version", "Unknown"),
        )
