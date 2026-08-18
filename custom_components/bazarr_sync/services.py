"""Services for Bazarr Sync integration."""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import HomeAssistantError

from .client import BazarrClient, BazarrError
from .const import (
    ACTION_DOWNLOAD_SUBTITLE,
    ACTION_SEARCH_SUBTITLES,
    ACTION_SYNC_SUBTITLE,
    DOMAIN,
)
from .models import SubtitleCandidate

_LOGGER = logging.getLogger(__name__)


def _get_coordinator(hass: HomeAssistant, entry_id: str) -> BazarrClient:
    """Get the coordinator's client for an entry."""
    entry = hass.config_entries.async_get_entry(entry_id)
    if not entry or not entry.runtime_data:
        raise HomeAssistantError(f"Config entry {entry_id} not found")
    return entry.runtime_data._client


async def async_search_subtitles(
    hass: HomeAssistant, call: ServiceCall
) -> ServiceResponse:
    """Search for subtitles for a movie or episode."""
    entry_id = call.data["config_entry_id"]
    media_type = call.data["media_type"]
    media_id = call.data["media_id"]
    series_id = call.data.get("series_id")

    client = _get_coordinator(hass, entry_id)

    try:
        if media_type == "movie":
            results = await client.async_search_movie_subtitles(media_id)
        else:
            if series_id is None:
                raise HomeAssistantError("series_id is required for episodes")
            results = await client.async_search_episode_subtitles(media_id)

        candidates = [SubtitleCandidate.from_bazarr(r).as_dict() for r in results]
        return {"candidates": candidates}  # type: ignore[dict-item,return-value]
    except BazarrError as err:
        raise HomeAssistantError(f"Bazarr error: {err}") from err


async def async_download_subtitle(hass: HomeAssistant, call: ServiceCall) -> None:
    """Download a specific subtitle."""
    entry_id = call.data["config_entry_id"]
    media_type = call.data["media_type"]
    media_id = call.data["media_id"]
    series_id = call.data.get("series_id")
    provider = call.data["provider"]
    subtitle_id = call.data["subtitle"]
    hearing_impaired = call.data.get("hearing_impaired", False)
    forced = call.data.get("forced", False)
    original_format = call.data.get("original_format", False)

    client = _get_coordinator(hass, entry_id)

    try:
        if media_type == "movie":
            await client.async_download_movie_subtitle(
                radarr_id=media_id,
                provider=provider,
                subtitle_id=subtitle_id,
                hearing_impaired=hearing_impaired,
                forced=forced,
                original_format=original_format,
            )
        else:
            if series_id is None:
                raise HomeAssistantError("series_id is required for episodes")
            await client.async_download_episode_subtitle(
                series_id=series_id,
                episode_id=media_id,
                provider=provider,
                subtitle_id=subtitle_id,
                hearing_impaired=hearing_impaired,
                forced=forced,
                original_format=original_format,
            )
    except BazarrError as err:
        raise HomeAssistantError(f"Bazarr error: {err}") from err


async def async_sync_subtitle(hass: HomeAssistant, call: ServiceCall) -> None:
    """Sync a subtitle."""
    entry_id = call.data["config_entry_id"]
    media_type = call.data["media_type"]
    media_id = call.data["media_id"]
    subtitle_id = call.data["subtitle_id"]
    reference_id = call.data.get("reference_id")
    hearing_impaired = call.data.get("hearing_impaired", False)
    forced = call.data.get("forced", False)
    original_format = call.data.get("original_format", False)
    max_offset_seconds = call.data.get("max_offset_seconds")
    no_fix_framerate = call.data.get("no_fix_framerate", False)
    gss = call.data.get("gss", False)
    series_id = call.data.get("series_id")

    client = _get_coordinator(hass, entry_id)

    try:
        # Resolve subtitle path server-side from installed subtitles using subtitle_id
        path = await client.async_get_installed_subtitle_path(
            media_type=media_type,
            media_id=media_id,
            subtitle_id=subtitle_id,
            series_id=series_id,
        )
        if path is None:
            raise HomeAssistantError(
                f"Installed subtitle '{subtitle_id}' not found for media {media_id}"
            )

        # Validate reference_id if provided
        if reference_id is not None:
            ref_valid = await client.async_get_sync_reference_identifier(
                media_type=media_type,
                media_id=media_id,
                reference_id=reference_id,
                series_id=series_id,
            )
            if ref_valid is None:
                raise HomeAssistantError(
                    f"Sync reference '{reference_id}' not found for media {media_id}"
                )

        await client.async_sync_subtitle(
            action="sync",
            language="",  # Language not needed for sync when path is provided
            path=path,
            media_type=media_type,
            media_id=media_id,
            forced=forced,
            hearing_impaired=hearing_impaired,
            original_format=original_format,
            reference=reference_id,
            max_offset_seconds=(
                str(max_offset_seconds) if max_offset_seconds is not None else None
            ),
            no_fix_framerate=no_fix_framerate,
            gss=gss,
        )
    except BazarrError as err:
        raise HomeAssistantError(f"Bazarr error: {err}") from err


def _register_services(hass: HomeAssistant) -> None:
    """Register services."""
    search_schema = vol.Schema(
        {
            vol.Required("config_entry_id"): str,
            vol.Required("media_type"): vol.In(["movie", "episode"]),
            vol.Required("media_id"): vol.Coerce(int),
            vol.Optional("series_id"): vol.Coerce(int),
        }
    )

    download_schema = vol.Schema(
        {
            vol.Required("config_entry_id"): str,
            vol.Required("media_type"): vol.In(["movie", "episode"]),
            vol.Required("media_id"): vol.Coerce(int),
            vol.Optional("series_id"): vol.Coerce(int),
            vol.Required("provider"): str,
            vol.Required("subtitle"): str,
            vol.Required("language"): str,
            vol.Optional("hearing_impaired", default=False): bool,
            vol.Optional("forced", default=False): bool,
            vol.Optional("original_format", default=False): bool,
        }
    )

    sync_schema = vol.Schema(
        {
            vol.Required("config_entry_id"): str,
            vol.Required("media_type"): vol.In(["movie", "episode"]),
            vol.Required("media_id"): vol.Coerce(int),
            vol.Required("subtitle_id"): str,
            vol.Optional("reference_id"): str,
            vol.Optional("hearing_impaired", default=False): bool,
            vol.Optional("forced", default=False): bool,
            vol.Optional("original_format", default=False): bool,
            vol.Optional("max_offset_seconds"): vol.Coerce(int),
            vol.Optional("no_fix_framerate", default=False): bool,
            vol.Optional("gss", default=False): bool,
            vol.Optional("series_id"): vol.Coerce(int),
        }
    )

    hass.services.async_register(
        DOMAIN,
        ACTION_SEARCH_SUBTITLES,
        async_search_subtitles,  # type: ignore[arg-type]
        schema=search_schema,
        supports_response=SupportsResponse.ONLY,
    )

    hass.services.async_register(
        DOMAIN,
        ACTION_DOWNLOAD_SUBTITLE,
        async_download_subtitle,  # type: ignore[arg-type]
        schema=download_schema,
    )

    hass.services.async_register(
        DOMAIN,
        ACTION_SYNC_SUBTITLE,
        async_sync_subtitle,  # type: ignore[arg-type]
        schema=sync_schema,
    )
