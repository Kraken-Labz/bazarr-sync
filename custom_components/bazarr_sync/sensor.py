"""Sensor platform for Bazarr integration."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
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
    """Set up Bazarr sensors based on a config entry."""
    coordinator = entry.runtime_data

    async_add_entities(
        [
            BazarrWantedMoviesSensor(coordinator, entry),
            BazarrWantedEpisodesSensor(coordinator, entry),
        ]
    )


class BazarrWantedMoviesSensor(BazarrEntity, SensorEntity):
    """Sensor for wanted movies count."""

    _attr_icon = "mdi:movie-search"
    _attr_translation_key = "wanted_movies"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self, coordinator: BazarrDataUpdateCoordinator, entry: BazarrConfigEntry
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_wanted_movies"

    @property
    def native_value(self) -> int | None:
        if self.coordinator.data:
            return self.coordinator.data.get("wanted_movies")
        return None


class BazarrWantedEpisodesSensor(BazarrEntity, SensorEntity):
    """Sensor for wanted episodes count."""

    _attr_icon = "mdi:television-classic"
    _attr_translation_key = "wanted_episodes"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self, coordinator: BazarrDataUpdateCoordinator, entry: BazarrConfigEntry
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_wanted_episodes"

    @property
    def native_value(self) -> int | None:
        if self.coordinator.data:
            return self.coordinator.data.get("wanted_episodes")
        return None
