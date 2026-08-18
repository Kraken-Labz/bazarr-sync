"""Bazarr HTTP client."""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

import aiohttp
from aiohttp import ClientResponseError, ClientTimeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    API_BADGES,
    API_EPISODES,
    API_MOVIES,
    API_PROVIDERS_EPISODES,
    API_PROVIDERS_MOVIES,
    API_SERIES,
    API_SUBTITLES,
    API_SYSTEM_HEALTH,
    API_SYSTEM_STATUS,
)

_LOGGER = logging.getLogger(__name__)


def _generate_correlation_id() -> str:
    """Generate a short correlation ID for request tracing."""
    return uuid.uuid4().hex[:8]


class BazarrError(Exception):
    """Base Bazarr error."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class BazarrAuthError(BazarrError):
    """Authentication failed (401/403)."""

    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message, status=401)


class BazarrNotFoundError(BazarrError):
    """Resource not found (404)."""

    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message, status=404)


class BazarrTimeoutError(BazarrError):
    """Request timeout."""

    def __init__(self, message: str = "Request timeout") -> None:
        super().__init__(message, status=None)


class BazarrClient:
    """Client for Bazarr API."""

    def __init__(
        self,
        hass: HomeAssistant,
        url: str,
        api_key: str,
        max_concurrent: int = 5,
        max_retries: int = 3,
        retry_base_delay: float = 0.5,
    ) -> None:
        """Initialize the client."""
        self.hass = hass
        self.url = url.rstrip("/")
        self.api_key = api_key
        self._session: aiohttp.ClientSession | None = None
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._max_retries = max_retries
        self._retry_base_delay = retry_base_delay

    def _get_headers(self) -> dict[str, str]:
        """Get headers with API key."""
        return {"X-API-KEY": self.api_key}

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = async_get_clientsession(self.hass)
        return self._session

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        timeout: int = 10,
        correlation_id: str | None = None,
    ) -> Any:
        """Make HTTP request with concurrency control and retry logic."""
        cid = correlation_id or _generate_correlation_id()
        async with self._semaphore:
            session = await self._get_session()
            url = f"{self.url}{endpoint}"
            headers = self._get_headers()

            # Determine if request is idempotent (safe to retry)
            is_idempotent = method.upper() in ("GET", "HEAD", "OPTIONS")

            last_exception: Exception | None = None

            _LOGGER.debug(
                "Request started: %s %s [correlation_id=%s]",
                method,
                endpoint,
                cid,
            )

            for attempt in range(self._max_retries + 1):
                try:
                    async with session.request(
                        method,
                        url,
                        headers=headers,
                        params=params,
                        data=data,
                        timeout=ClientTimeout(total=timeout),
                    ) as response:
                        response.raise_for_status()

                        if response.status == 204 or response.content_length == 0:
                            _LOGGER.debug(
                                "Request completed: %s %s [correlation_id=%s] status=%d",
                                method,
                                endpoint,
                                cid,
                                response.status,
                            )
                            return None

                        content_type = response.headers.get("Content-Type", "")
                        if "application/json" in content_type:
                            result = await response.json()
                            _LOGGER.debug(
                                "Request completed: %s %s [correlation_id=%s] status=%d",
                                method,
                                endpoint,
                                cid,
                                response.status,
                            )
                            return result
                        result = await response.text()
                        _LOGGER.debug(
                            "Request completed: %s %s [correlation_id=%s] status=%d",
                            method,
                            endpoint,
                            cid,
                            response.status,
                        )
                        return result

                except ClientResponseError as err:
                    last_exception = err
                    # Don't retry auth errors or 404
                    if err.status in (401, 403):
                        _LOGGER.error(
                            "Request auth error: %s %s [correlation_id=%s] status=%d",
                            method,
                            endpoint,
                            cid,
                            err.status,
                        )
                        raise BazarrAuthError(f"Authentication failed: {err}") from err
                    if err.status == 404:
                        _LOGGER.warning(
                            "Request not found: %s %s [correlation_id=%s]",
                            method,
                            endpoint,
                            cid,
                        )
                        raise BazarrNotFoundError(f"Resource not found: {err}") from err
                    # Retry on 5xx server errors for idempotent requests
                    if (
                        is_idempotent
                        and 500 <= err.status < 600
                        and attempt < self._max_retries
                    ):
                        delay = self._retry_base_delay * (2**attempt)
                        _LOGGER.warning(
                            "Request failed with %s, retrying in %.1fs (attempt %d/%d) [correlation_id=%s]",
                            err.status,
                            delay,
                            attempt + 1,
                            self._max_retries,
                            cid,
                        )
                        await asyncio.sleep(delay)
                        continue
                    # If we've exhausted retries or it's non-retryable, raise error
                    if attempt >= self._max_retries:
                        _LOGGER.error(
                            "Request failed after %d attempts: %s %s [correlation_id=%s]",
                            self._max_retries + 1,
                            method,
                            endpoint,
                            cid,
                        )
                        raise BazarrError(
                            f"Request failed after {self._max_retries + 1} attempts: {err}"
                        ) from err
                    _LOGGER.error(
                        "Request error: %s %s [correlation_id=%s] status=%d",
                        method,
                        endpoint,
                        cid,
                        err.status,
                    )
                    raise BazarrError(f"HTTP error {err.status}: {err}") from err

                except asyncio.TimeoutError as err:
                    last_exception = err
                    if is_idempotent and attempt < self._max_retries:
                        delay = self._retry_base_delay * (2**attempt)
                        _LOGGER.warning(
                            "Request timeout, retrying in %.1fs (attempt %d/%d) [correlation_id=%s]",
                            delay,
                            attempt + 1,
                            self._max_retries,
                            cid,
                        )
                        await asyncio.sleep(delay)
                        continue
                    _LOGGER.error(
                        "Request timeout after %d attempts: %s %s [correlation_id=%s]",
                        self._max_retries + 1,
                        method,
                        endpoint,
                        cid,
                    )
                    raise BazarrTimeoutError(f"Timeout connecting to {url}") from err

                except aiohttp.ClientError as err:
                    last_exception = err
                    if is_idempotent and attempt < self._max_retries:
                        delay = self._retry_base_delay * (2**attempt)
                        _LOGGER.warning(
                            "Client error: %s, retrying in %.1fs (attempt %d/%d) [correlation_id=%s]",
                            err,
                            delay,
                            attempt + 1,
                            self._max_retries,
                            cid,
                        )
                        await asyncio.sleep(delay)
                        continue
                    _LOGGER.error(
                        "Client error after %d attempts: %s %s [correlation_id=%s]",
                        self._max_retries + 1,
                        method,
                        endpoint,
                        cid,
                    )
                    raise BazarrError(f"Client error: {err}") from err

            # Should not reach here, but just in case
            _LOGGER.error(
                "Request failed after %d attempts: %s %s [correlation_id=%s]",
                self._max_retries + 1,
                method,
                endpoint,
                cid,
            )
            raise BazarrError(
                f"Request failed after {self._max_retries + 1} attempts: {last_exception}"
            ) from last_exception

    # Status / health / badges
    async def async_get_status(self) -> dict[str, Any]:
        """Get system status."""
        result = await self._request("GET", API_SYSTEM_STATUS)
        return result.get("data", {}) if result else {}

    async def async_get_badges(self) -> dict[str, Any]:
        """Get badges (wanted counts)."""
        return await self._request("GET", API_BADGES) or {}

    async def async_get_health(self) -> list[dict[str, Any]]:
        """Get health issues."""
        result = await self._request("GET", API_SYSTEM_HEALTH)
        return result.get("data", []) if result else []

    # Media listing
    async def async_get_movies(
        self, start: int = 0, length: int = -1, radarr_ids: list[int] | None = None
    ) -> dict[str, Any]:
        """Get movies list."""
        params: dict[str, Any] = {"start": start}
        if length > 0:
            params["length"] = length
        if radarr_ids:
            params["radarrid[]"] = radarr_ids
        return await self._request("GET", API_MOVIES, params=params) or {
            "data": [],
            "total": 0,
        }

    async def async_get_episodes(
        self, series_ids: list[int] | None = None, episode_ids: list[int] | None = None
    ) -> list[dict[str, Any]]:
        """Get episodes list."""
        params: dict[str, Any] = {}
        if episode_ids:
            params["episodeid[]"] = episode_ids
        elif series_ids:
            params["seriesid[]"] = series_ids
        else:
            raise ValueError("Either series_ids or episode_ids must be provided")
        result = await self._request("GET", API_EPISODES, params=params)
        return result.get("data", []) if result else []

    async def async_get_series(
        self, start: int = 0, length: int = -1, series_ids: list[int] | None = None
    ) -> dict[str, Any]:
        """Get series list."""
        params: dict[str, Any] = {"start": start}
        if length > 0:
            params["length"] = length
        if series_ids:
            params["seriesid[]"] = series_ids
        return await self._request("GET", API_SERIES, params=params) or {
            "data": [],
            "total": 0,
        }

    # Subtitle search
    async def async_search_movie_subtitles(
        self, radarr_id: int
    ) -> list[dict[str, Any]]:
        """Search subtitles for a movie."""
        params = {"radarrid": radarr_id}
        result = await self._request("GET", API_PROVIDERS_MOVIES, params=params)
        return result.get("data", []) if result else []

    async def async_search_episode_subtitles(
        self, episode_id: int
    ) -> list[dict[str, Any]]:
        """Search subtitles for an episode."""
        params = {"episodeid": episode_id}
        result = await self._request("GET", API_PROVIDERS_EPISODES, params=params)
        return result.get("data", []) if result else []

    # Subtitle download
    async def async_download_movie_subtitle(
        self,
        radarr_id: int,
        provider: str,
        subtitle_id: str,
        hearing_impaired: bool = False,
        forced: bool = False,
        original_format: bool = False,
    ) -> None:
        """Download a specific subtitle for a movie."""
        data = {
            "radarrid": radarr_id,
            "provider": provider,
            "subtitle": subtitle_id,
            "hi": "True" if hearing_impaired else "False",
            "forced": "True" if forced else "False",
            "original_format": "True" if original_format else "False",
        }
        await self._request("POST", API_PROVIDERS_MOVIES, data=data)

    async def async_download_episode_subtitle(
        self,
        series_id: int,
        episode_id: int,
        provider: str,
        subtitle_id: str,
        hearing_impaired: bool = False,
        forced: bool = False,
        original_format: bool = False,
    ) -> None:
        """Download a specific subtitle for an episode."""
        data = {
            "seriesid": series_id,
            "episodeid": episode_id,
            "provider": provider,
            "subtitle": subtitle_id,
            "hi": "True" if hearing_impaired else "False",
            "forced": "True" if forced else "False",
            "original_format": "True" if original_format else "False",
        }
        await self._request("POST", API_PROVIDERS_EPISODES, data=data)

    # Sync references
    async def async_get_sync_references(
        self,
        subtitles_path: str,
        sonarr_episode_id: int | None = None,
        radarr_movie_id: int | None = None,
    ) -> dict[str, Any]:
        """Get sync references for a subtitle file."""
        params: dict[str, Any] = {"subtitlesPath": subtitles_path}
        if sonarr_episode_id is not None:
            params["sonarrEpisodeId"] = sonarr_episode_id
        if radarr_movie_id is not None:
            params["radarrMovieId"] = radarr_movie_id
        result = await self._request("GET", API_SUBTITLES, params=params)
        return result.get("data", {}) if result else {}

    async def async_get_installed_subtitle_path(
        self,
        media_type: str,
        media_id: int,
        subtitle_id: str,
        series_id: int | None = None,
    ) -> str | None:
        """Get the installed subtitle file path for a media item by subtitle_id.

        Resolves the path server-side by querying Bazarr for the media item
        and validating the subtitle_id against installed subtitles.
        The subtitle_id is the filesystem path of the installed subtitle.
        """
        if media_type == "movie":
            result = await self.async_get_movies(radarr_ids=[media_id])
            data = result.get("data", [])
        else:
            if series_id is None:
                raise ValueError("series_id is required for episodes")
            data = await self.async_get_episodes(episode_ids=[media_id])

        if not data:
            return None

        item = data[0]
        subtitles = item.get("subtitles", [])

        for sub in subtitles:
            if sub.get("path") == subtitle_id:
                return sub.get("path")

        return None

    async def async_get_sync_reference_identifier(
        self,
        media_type: str,
        media_id: int,
        reference_id: str,
        series_id: int | None = None,
    ) -> str | None:
        """Get the sync reference identifier for a media item by reference_id.

        Validates that the reference_id exists in the sync references for the media.
        The reference_id is the stream identifier (e.g., 'a:0', 's:0').
        """
        if media_type == "movie":
            result = await self.async_get_movies(radarr_ids=[media_id])
            data = result.get("data", [])
        else:
            if series_id is None:
                raise ValueError("series_id is required for episodes")
            data = await self.async_get_episodes(episode_ids=[media_id])

        if not data:
            return None

        item = data[0]
        # Get sync references for the media item to validate reference_id
        subtitles = item.get("subtitles", [])
        if not subtitles:
            return None

        # Use the first subtitle's path to get sync references
        first_sub_path = subtitles[0].get("path")
        if not first_sub_path:
            return None

        sync_result = await self.async_get_sync_references(
            subtitles_path=first_sub_path,
            sonarr_episode_id=media_id if media_type == "episode" else None,
            radarr_movie_id=media_id if media_type == "movie" else None,
        )

        # Check if reference_id exists in audio tracks, embedded subtitles, or external subtitles
        for track in sync_result.get("audio_tracks", []):
            if track.get("stream") == reference_id:
                return reference_id
        for track in sync_result.get("embedded_subtitles_tracks", []):
            if track.get("stream") == reference_id:
                return reference_id
        for track in sync_result.get("external_subtitles_tracks", []):
            if track.get("path") == reference_id:
                return reference_id

        return None

    # Sync subtitle
    async def async_sync_subtitle(
        self,
        action: str,
        language: str,
        path: str,
        media_type: str,  # "movie" or "episode"
        media_id: int,
        forced: bool = False,
        hearing_impaired: bool = False,
        original_format: bool = False,
        reference: str | None = None,
        max_offset_seconds: str | None = None,
        no_fix_framerate: bool = False,
        gss: bool = False,
    ) -> None:
        """Sync a subtitle."""
        data = {
            "action": action,
            "language": language,
            "path": path,
            "type": media_type,
            "id": media_id,
            "forced": "True" if forced else "False",
            "hi": "True" if hearing_impaired else "False",
            "original_format": "True" if original_format else "False",
        }
        if reference is not None:
            data["reference"] = reference
        if max_offset_seconds is not None:
            data["max_offset_seconds"] = max_offset_seconds
        if no_fix_framerate:
            data["no_fix_framerate"] = "True"
        if gss:
            data["gss"] = "True"

        await self._request("PATCH", API_SUBTITLES, data=data)
