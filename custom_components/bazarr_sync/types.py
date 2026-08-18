"""Type aliases for Bazarr integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry

from .coordinator import BazarrDataUpdateCoordinator

type BazarrConfigEntry = ConfigEntry[BazarrDataUpdateCoordinator]
type BazarrSyncConfigEntry = ConfigEntry[BazarrDataUpdateCoordinator]
