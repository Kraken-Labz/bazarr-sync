"""The Bazarr Sync integration."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import BazarrDataUpdateCoordinator
from .services import _register_services
from .types import BazarrSyncConfigEntry
from .websocket import async_register_websocket_commands

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Bazarr Sync integration."""
    # Register services globally
    _register_services(hass)
    # Register WebSocket commands globally
    async_register_websocket_commands(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: BazarrSyncConfigEntry) -> bool:
    """Set up Bazarr Sync from a config entry."""
    coordinator = BazarrDataUpdateCoordinator(hass, entry)

    await coordinator.ensure_tokens()
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: BazarrSyncConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
