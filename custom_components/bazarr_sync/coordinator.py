"""DataUpdateCoordinator for Bazarr."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import BazarrAuthError, BazarrClient, BazarrError, BazarrTimeoutError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class BazarrDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching Bazarr data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=5),
        )
        self.url = entry.data[CONF_URL]
        self.api_token = entry.data[CONF_API_KEY]
        self._client = BazarrClient(hass, self.url, self.api_token, max_concurrent=5)

    async def ensure_tokens(self) -> None:
        """Ensure that the API tokens are valid."""
        try:
            await self._client.async_get_status()
        except BazarrAuthError as err:
            raise ConfigEntryAuthFailed(err) from err
        except BazarrTimeoutError as err:
            raise ConfigEntryNotReady(
                f"Timed out while connecting to {self.url}"
            ) from err

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Bazarr API."""
        try:
            badges_data = await self._client.async_get_badges()
            health_data = await self._client.async_get_health()
            status_data = await self._client.async_get_status()

            data = {
                "wanted_movies": badges_data.get("movies", 0),
                "wanted_episodes": badges_data.get("episodes", 0),
                "health_issues": health_data,
                "version": status_data.get("bazarr_version", "Unknown"),
            }

            _LOGGER.debug(f"Coordinator data: {data}")

            return data
        except (TimeoutError, BazarrError) as err:
            raise UpdateFailed(f"Error communicating with Bazarr API: {err}") from err
