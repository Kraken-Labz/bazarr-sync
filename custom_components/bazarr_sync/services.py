"""Services for Bazarr Sync integration."""

from __future__ import annotations

import logging
from functools import partial
from typing import Any, cast

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
    ACTION_DOWNLOAD_BEST_SUBTITLE,
    ACTION_DOWNLOAD_SUBTITLE,
    ACTION_FIND_SUBTITLES,
    ACTION_SEARCH_SUBTITLES,
    ACTION_SYNC_SUBTITLE,
    ACTION_SYNC_SUBTITLE_AUTO,
    DOMAIN,
)
from .media_resolver import (
    MediaResolutionError,
    MediaResolver,
)
from .models import ResolvedMedia, SubtitleCandidate

_LOGGER = logging.getLogger(__name__)


def _get_coordinator(hass: HomeAssistant, entry_id: str) -> BazarrClient:
    """Get the coordinator's client for an entry."""
    entry = hass.config_entries.async_get_entry(entry_id)
    if not entry or not entry.runtime_data:
        raise HomeAssistantError(f"Config entry {entry_id} not found")
    return entry.runtime_data._client


def _get_resolver(hass: HomeAssistant, entry_id: str) -> MediaResolver:
    """Get a MediaResolver for an entry."""
    client = _get_coordinator(hass, entry_id)
    return MediaResolver(client)


def _normalize_language(value: str) -> str:
    """Normalize language code for comparison."""
    if not value:
        return ""
    return value.strip().lower().replace("_", "-")


async def _resolve_media(
    hass: HomeAssistant, entry_id: str, call: ServiceCall
) -> ResolvedMedia:
    """Resolve human-friendly media parameters to a ResolvedMedia object."""
    media_type = call.data["media_type"]

    try:
        if media_type == "movie":
            title = call.data["title"]
            year = call.data.get("year")
            return await _get_resolver(hass, entry_id).resolve_movie(title, year)
        else:
            title = call.data["title"]
            season = call.data["season"]
            episode = call.data["episode"]
            year = call.data.get("year")
            return await _get_resolver(hass, entry_id).resolve_episode(
                title, season, episode, year
            )
    except MediaResolutionError as err:
        # Re-raise with more context
        raise HomeAssistantError(str(err)) from err


def _select_best_candidate(
    candidates: list[SubtitleCandidate],
    language: str,
    hearing_impaired: bool = False,
    forced: bool = False,
) -> SubtitleCandidate | None:
    """Select the best candidate based on score and filters."""
    norm_lang = _normalize_language(language)

    # Filter by language
    lang_candidates = [
        c for c in candidates if _normalize_language(c.language) == norm_lang
    ]

    if not lang_candidates:
        return None

    # Filter by forced/hearing_impaired if requested
    if forced:
        lang_candidates = [c for c in lang_candidates if c.forced]
    if hearing_impaired:
        lang_candidates = [c for c in lang_candidates if c.hearing_impaired]

    if not lang_candidates:
        return None

    # Sort by score descending, preserve Bazarr order for ties
    lang_candidates.sort(key=lambda c: c.score, reverse=True)
    return lang_candidates[0]


async def _find_installed_subtitle(
    resolver: MediaResolver,
    resolved: ResolvedMedia,
    language: str,
    hearing_impaired: bool = False,
    forced: bool = False,
) -> dict[str, Any] | None:
    """Find an installed subtitle matching the criteria."""
    installed = await resolver.get_installed_subtitles_for_media(resolved)

    norm_lang = _normalize_language(language)
    matches = []

    for sub in installed:
        sub_lang = _normalize_language(sub.get("language", ""))
        if sub_lang != norm_lang:
            continue
        if forced and not sub.get("forced", False):
            continue
        if hearing_impaired and not sub.get("hearing_impaired", False):
            continue
        matches.append(sub)

    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise HomeAssistantError(
            f"Multiple installed subtitles match language '{language}' with the requested flags. "
            f"Use the advanced sync_subtitle action or refine language/flags."
        )
    return None


async def async_find_subtitles(
    hass: HomeAssistant, call: ServiceCall
) -> ServiceResponse:
    """Find subtitles for a movie or episode using human-readable identifiers."""
    entry_id = call.data["config_entry_id"]

    # Resolve media first
    resolved = await _resolve_media(hass, entry_id, call)

    # Search for subtitles
    client = _get_coordinator(hass, entry_id)

    try:
        if resolved.media_type == "movie":
            results = await client.async_search_movie_subtitles(resolved.media_id)
        else:
            results = await client.async_search_episode_subtitles(resolved.media_id)

        candidates = [SubtitleCandidate.from_bazarr(r).as_dict() for r in results]
        return cast(
            ServiceResponse,
            {"resolved_media": resolved.as_dict(), "candidates": candidates},
        )
    except BazarrError as err:
        raise HomeAssistantError(f"Bazarr error: {err}") from err


async def async_download_best_subtitle(
    hass: HomeAssistant, call: ServiceCall
) -> ServiceResponse:
    """Download the best matching subtitle for a movie or episode."""
    entry_id = call.data["config_entry_id"]
    language = call.data["language"]
    hearing_impaired = call.data.get("hearing_impaired", False)
    forced = call.data.get("forced", False)
    original_format = call.data.get("original_format", False)

    # Resolve media first
    resolved = await _resolve_media(hass, entry_id, call)

    # Search for subtitles
    client = _get_coordinator(hass, entry_id)

    try:
        if resolved.media_type == "movie":
            results = await client.async_search_movie_subtitles(resolved.media_id)
        else:
            results = await client.async_search_episode_subtitles(resolved.media_id)

        candidates = [SubtitleCandidate.from_bazarr(r) for r in results]

        # Select best candidate
        best = _select_best_candidate(candidates, language, hearing_impaired, forced)

        if best is None:
            raise HomeAssistantError(
                f"No subtitle candidate matches language '{language}' with the requested flags."
            )

        # Download the subtitle
        if resolved.media_type == "movie":
            await client.async_download_movie_subtitle(
                radarr_id=resolved.media_id,
                provider=best.provider,
                subtitle_id=best.subtitle_id,
                hearing_impaired=hearing_impaired,
                forced=forced,
                original_format=original_format,
            )
        else:
            await client.async_download_episode_subtitle(
                series_id=resolved.series_id or 0,
                episode_id=resolved.media_id,
                provider=best.provider,
                subtitle_id=best.subtitle_id,
                hearing_impaired=hearing_impaired,
                forced=forced,
                original_format=original_format,
            )

        return cast(
            ServiceResponse,
            {
                "success": True,
                "resolved_media": resolved.as_dict(),
                "selected_candidate": {
                    "provider": best.provider,
                    "subtitle_id": best.subtitle_id,
                    "language": best.language,
                    "score": best.score,
                    "forced": best.forced,
                    "hearing_impaired": best.hearing_impaired,
                },
            },
        )
    except BazarrError as err:
        raise HomeAssistantError(f"Bazarr error: {err}") from err


async def async_sync_subtitle_auto(
    hass: HomeAssistant, call: ServiceCall
) -> ServiceResponse:
    """Automatically sync a subtitle for a movie or episode."""
    entry_id = call.data["config_entry_id"]
    language = call.data["subtitle_language"]
    hearing_impaired = call.data.get("hearing_impaired", False)
    forced = call.data.get("forced", False)
    original_format = call.data.get("original_format", False)
    max_offset_seconds = call.data.get("max_offset_seconds")
    no_fix_framerate = call.data.get("no_fix_framerate", False)
    gss = call.data.get("gss", False)

    # Resolve media first
    resolved = await _resolve_media(hass, entry_id, call)

    # Find installed subtitle
    resolver = _get_resolver(hass, entry_id)
    installed_sub = await _find_installed_subtitle(
        resolver, resolved, language, hearing_impaired, forced
    )

    if installed_sub is None:
        installed = await resolver.get_installed_subtitles_for_media(resolved)
        available: dict[str, int] = {}
        for sub in installed:
            lang = str(sub.get("language", "unknown"))
            flags: list[str] = []
            if sub.get("forced"):
                flags.append("forced")
            if sub.get("hearing_impaired"):
                flags.append("hi")
            key = f"{lang} ({', '.join(flags)})" if flags else lang
            available[key] = available.get(key, 0) + 1

        raise HomeAssistantError(
            f"No installed subtitle matches language '{language}' with the requested flags. "
            f"Available: {available}"
        )

    # Sync the subtitle
    client = _get_coordinator(hass, entry_id)

    try:
        # Resolve subtitle path server-side
        path = await client.async_get_installed_subtitle_path(
            media_type=resolved.media_type,
            media_id=resolved.media_id,
            subtitle_id=installed_sub["subtitle_id"],
            series_id=resolved.series_id,
        )
        if path is None:
            raise HomeAssistantError(
                f"Installed subtitle '{installed_sub['subtitle_id']}' not found for media {resolved.media_id}"
            )

        await client.async_sync_subtitle(
            action="sync",
            language="",  # Language not needed for sync when path is provided
            path=path,
            media_type=resolved.media_type,
            media_id=resolved.media_id,
            forced=forced,
            hearing_impaired=hearing_impaired,
            original_format=original_format,
            reference=None,  # Allow default behavior
            max_offset_seconds=(
                str(max_offset_seconds) if max_offset_seconds is not None else None
            ),
            no_fix_framerate=no_fix_framerate,
            gss=gss,
        )

        return cast(
            ServiceResponse,
            {
                "success": True,
                "resolved_media": resolved.as_dict(),
                "subtitle": {
                    "subtitle_id": installed_sub["subtitle_id"],
                    "language": installed_sub.get("language"),
                    "forced": installed_sub.get("forced", False),
                    "hearing_impaired": installed_sub.get("hearing_impaired", False),
                },
            },
        )
    except BazarrError as err:
        raise HomeAssistantError(f"Bazarr error: {err}") from err


# --- Existing actions (unchanged) ---


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
        return cast(ServiceResponse, {"candidates": candidates})
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

        # Resolve reference_id to the value Bazarr expects (real path for external)
        resolved_reference = reference_id
        if reference_id is not None:
            resolved_reference = await client.async_get_sync_reference_identifier(
                media_type=media_type,
                media_id=media_id,
                reference_id=reference_id,
                series_id=series_id,
            )
            if resolved_reference is None:
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
            reference=resolved_reference,
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
    # --- Human-friendly actions (listed first) ---

    find_schema = vol.Schema(
        {
            vol.Required("config_entry_id"): str,
            vol.Required("media_type"): vol.In(["movie", "episode"]),
            vol.Required("title"): str,
            vol.Optional("year"): vol.Coerce(int),
            vol.Optional("season"): vol.Coerce(int),
            vol.Optional("episode"): vol.Coerce(int),
        }
    )

    download_best_schema = vol.Schema(
        {
            vol.Required("config_entry_id"): str,
            vol.Required("media_type"): vol.In(["movie", "episode"]),
            vol.Required("title"): str,
            vol.Optional("year"): vol.Coerce(int),
            vol.Optional("season"): vol.Coerce(int),
            vol.Optional("episode"): vol.Coerce(int),
            vol.Required("language"): str,
            vol.Optional("hearing_impaired", default=False): bool,
            vol.Optional("forced", default=False): bool,
            vol.Optional("original_format", default=False): bool,
        }
    )

    sync_auto_schema = vol.Schema(
        {
            vol.Required("config_entry_id"): str,
            vol.Required("media_type"): vol.In(["movie", "episode"]),
            vol.Required("title"): str,
            vol.Optional("year"): vol.Coerce(int),
            vol.Optional("season"): vol.Coerce(int),
            vol.Optional("episode"): vol.Coerce(int),
            vol.Required("subtitle_language"): str,
            vol.Optional("hearing_impaired", default=False): bool,
            vol.Optional("forced", default=False): bool,
            vol.Optional("original_format", default=False): bool,
            vol.Optional("max_offset_seconds"): vol.Coerce(int),
            vol.Optional("no_fix_framerate", default=False): bool,
            vol.Optional("gss", default=False): bool,
        }
    )

    # --- Existing schemas (unchanged) ---

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

    # --- Register handlers ---

    # New human-friendly actions
    find_handler = partial(async_find_subtitles, hass)
    download_best_handler = partial(async_download_best_subtitle, hass)
    sync_auto_handler = partial(async_sync_subtitle_auto, hass)

    # Existing handlers
    search_handler = partial(async_search_subtitles, hass)
    download_handler = partial(async_download_subtitle, hass)
    sync_handler = partial(async_sync_subtitle, hass)

    # Register human-friendly actions FIRST (as per spec)
    hass.services.async_register(
        DOMAIN,
        ACTION_FIND_SUBTITLES,
        find_handler,
        schema=find_schema,
        supports_response=SupportsResponse.ONLY,
    )

    hass.services.async_register(
        DOMAIN,
        ACTION_DOWNLOAD_BEST_SUBTITLE,
        download_best_handler,
        schema=download_best_schema,
        supports_response=SupportsResponse.ONLY,
    )

    hass.services.async_register(
        DOMAIN,
        ACTION_SYNC_SUBTITLE_AUTO,
        sync_auto_handler,
        schema=sync_auto_schema,
        supports_response=SupportsResponse.ONLY,
    )

    # Register existing actions (with "Advanced / API" in description)
    hass.services.async_register(
        DOMAIN,
        ACTION_SEARCH_SUBTITLES,
        search_handler,
        schema=search_schema,
        supports_response=SupportsResponse.ONLY,
    )

    hass.services.async_register(
        DOMAIN,
        ACTION_DOWNLOAD_SUBTITLE,
        download_handler,
        schema=download_schema,
    )

    hass.services.async_register(
        DOMAIN,
        ACTION_SYNC_SUBTITLE,
        sync_handler,
        schema=sync_schema,
    )
