"""WebSocket API for Bazarr Sync integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .client import BazarrClient, BazarrError
from .const import (
    WS_TYPE_DOWNLOAD_SUBTITLE,
    WS_TYPE_GET_MEDIA,
    WS_TYPE_GET_SUBTITLES,
    WS_TYPE_GET_SYNC_REFERENCES,
    WS_TYPE_SEARCH_SUBTITLES,
    WS_TYPE_SYNC_SUBTITLE,
)
from .models import SubtitleCandidate, SyncReferences

_LOGGER = logging.getLogger(__name__)


def _get_client(hass: HomeAssistant, entry_id: str) -> BazarrClient:
    """Get the BazarrClient for an entry."""
    entry = hass.config_entries.async_get_entry(entry_id)
    if not entry or not entry.runtime_data:
        raise HomeAssistantError(f"Config entry {entry_id} not found")
    return entry.runtime_data._client


# --- Internal handler logic (testable) ---


async def _ws_get_media(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Get media list (movies, episodes, or series)."""
    entry_id = msg["config_entry_id"]
    media_type = msg.get("media_type", "movies")
    series_id = msg.get("series_id")

    client = _get_client(hass, entry_id)

    try:
        if media_type == "movies":
            result = await client.async_get_movies()
            data = result.get("data", [])
        elif media_type == "episodes":
            if series_id is None:
                raise HomeAssistantError("series_id is required for episodes")
            data = await client.async_get_episodes(series_ids=[series_id])
        else:
            result = await client.async_get_series()
            data = result.get("data", [])

        # Filter to only essential fields
        filtered = []
        for item in data:
            if media_type == "movies":
                filtered.append(
                    {
                        "radarrId": item.get("radarrId"),
                        "title": item.get("title"),
                        "year": item.get("year"),
                        "poster": item.get("poster"),
                    }
                )
            elif media_type == "episodes":
                filtered.append(
                    {
                        "sonarrEpisodeId": item.get("sonarrEpisodeId"),
                        "sonarrSeriesId": item.get("sonarrSeriesId"),
                        "title": item.get("title"),
                        "season": item.get("season"),
                        "episode": item.get("episode"),
                    }
                )
            else:
                filtered.append(
                    {
                        "sonarrSeriesId": item.get("sonarrSeriesId"),
                        "title": item.get("title"),
                        "year": item.get("year"),
                        "poster": item.get("poster"),
                        "episodeFileCount": item.get("episodeFileCount"),
                        "episodeMissingCount": item.get("episodeMissingCount"),
                    }
                )

        connection.send_result(msg["id"], {"media": filtered})
    except BazarrError as err:
        connection.send_error(msg["id"], "bazarr_error", str(err))


@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_TYPE_GET_MEDIA,
        vol.Required("config_entry_id"): str,
        vol.Optional("media_type"): vol.In(["movies", "episodes", "series"]),
        vol.Optional("series_id"): vol.Coerce(int),
    }
)
@websocket_api.async_response
async def ws_get_media(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Get media list (movies, episodes, or series)."""
    await _ws_get_media(hass, connection, msg)


async def _ws_get_subtitles(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Get installed subtitles for a media item."""
    entry_id = msg["config_entry_id"]
    media_type = msg["media_type"]
    media_id = msg["media_id"]
    series_id = msg.get("series_id")

    client = _get_client(hass, entry_id)

    try:
        if media_type == "movie":
            result = await client.async_get_movies(radarr_ids=[media_id])
            data = result.get("data", [])
        else:
            if series_id is None:
                raise HomeAssistantError("series_id is required for episodes")
            data = await client.async_get_episodes(episode_ids=[media_id])

        if not data:
            connection.send_result(msg["id"], {"subtitles": []})
            return

        item = data[0]
        subtitles = item.get("subtitles", [])

        filtered = []
        for sub in subtitles:
            path = sub.get("path")
            subtitle_id = (
                client._generate_subtitle_id(media_type, media_id, path)
                if path
                else None
            )
            filtered.append(
                {
                    "subtitle_id": subtitle_id,
                    "language": sub.get("name"),
                    "code2": sub.get("code2"),
                    "code3": sub.get("code3"),
                    "forced": sub.get("forced"),
                    "hearing_impaired": sub.get("hi"),
                    "file_size": sub.get("file_size"),
                    "embedded_track_id": sub.get("embedded_track_id"),
                }
            )

        connection.send_result(msg["id"], {"subtitles": filtered})
    except BazarrError as err:
        connection.send_error(msg["id"], "bazarr_error", str(err))


@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_TYPE_GET_SUBTITLES,
        vol.Required("config_entry_id"): str,
        vol.Required("media_type"): vol.In(["movie", "episode"]),
        vol.Required("media_id"): vol.Coerce(int),
        vol.Optional("series_id"): vol.Coerce(int),
    }
)
@websocket_api.async_response
async def ws_get_subtitles(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Get installed subtitles for a media item."""
    await _ws_get_subtitles(hass, connection, msg)


async def _ws_search_subtitles(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Search for subtitle candidates."""
    entry_id = msg["config_entry_id"]
    media_type = msg["media_type"]
    media_id = msg["media_id"]
    series_id = msg.get("series_id")

    client = _get_client(hass, entry_id)

    try:
        if media_type == "movie":
            results = await client.async_search_movie_subtitles(media_id)
        else:
            if series_id is None:
                raise HomeAssistantError("series_id is required for episodes")
            results = await client.async_search_episode_subtitles(media_id)

        candidates = [SubtitleCandidate.from_bazarr(r).as_dict() for r in results]
        connection.send_result(msg["id"], {"candidates": candidates})
    except BazarrError as err:
        connection.send_error(msg["id"], "bazarr_error", str(err))


@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_TYPE_SEARCH_SUBTITLES,
        vol.Required("config_entry_id"): str,
        vol.Required("media_type"): vol.In(["movie", "episode"]),
        vol.Required("media_id"): vol.Coerce(int),
        vol.Optional("series_id"): vol.Coerce(int),
    }
)
@websocket_api.async_response
async def ws_search_subtitles(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Search for subtitle candidates."""
    await _ws_search_subtitles(hass, connection, msg)


async def _ws_download_subtitle(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Download a specific subtitle."""
    entry_id = msg["config_entry_id"]
    media_type = msg["media_type"]
    media_id = msg["media_id"]
    series_id = msg.get("series_id")
    provider = msg["provider"]
    subtitle_id = msg["subtitle"]
    hearing_impaired = msg.get("hearing_impaired", False)
    forced = msg.get("forced", False)
    original_format = msg.get("original_format", False)

    client = _get_client(hass, entry_id)

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

        connection.send_result(msg["id"], {"success": True})
    except BazarrError as err:
        connection.send_error(msg["id"], "bazarr_error", str(err))


@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_TYPE_DOWNLOAD_SUBTITLE,
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
@websocket_api.async_response
async def ws_download_subtitle(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Download a specific subtitle."""
    await _ws_download_subtitle(hass, connection, msg)


async def _ws_get_sync_references(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Get sync references for a subtitle file."""
    entry_id = msg["config_entry_id"]
    media_type = msg["media_type"]
    media_id = msg["media_id"]
    subtitle_id = msg["subtitle_id"]
    series_id = msg.get("series_id")

    client = _get_client(hass, entry_id)

    try:
        # Resolve subtitle path server-side from installed subtitles using subtitle_id
        subtitles_path = await client.async_get_installed_subtitle_path(
            media_type=media_type,
            media_id=media_id,
            subtitle_id=subtitle_id,
            series_id=series_id,
        )
        if subtitles_path is None:
            connection.send_error(
                msg["id"],
                "subtitle_not_found",
                f"Installed subtitle '{subtitle_id}' not found for media {media_id}",
            )
            return

        sonarr_episode_id = media_id if media_type == "episode" else None
        radarr_movie_id = media_id if media_type == "movie" else None

        result = await client.async_get_sync_references(
            subtitles_path=subtitles_path,
            sonarr_episode_id=sonarr_episode_id,
            radarr_movie_id=radarr_movie_id,
        )

        refs = SyncReferences.from_bazarr(result)
        connection.send_result(
            msg["id"],
            {
                "audio_tracks": [
                    {
                        "kind": "audio",
                        "identifier": r.identifier,
                        "label": r.label,
                        "language": r.language,
                    }
                    for r in refs.audio_tracks
                ],
                "embedded_subtitles": [
                    {
                        "kind": "embedded_subtitle",
                        "identifier": r.identifier,
                        "label": r.label,
                        "language": r.language,
                        "forced": r.forced,
                        "hearing_impaired": r.hearing_impaired,
                    }
                    for r in refs.embedded_subtitles
                ],
                "external_subtitles": [
                    {
                        "kind": "external_subtitle",
                        "identifier": r.identifier,
                        "label": r.label,
                        "language": r.language,
                        "forced": r.forced,
                        "hearing_impaired": r.hearing_impaired,
                    }
                    for r in refs.external_subtitles
                ],
            },
        )
    except BazarrError as err:
        connection.send_error(msg["id"], "bazarr_error", str(err))
    except ValueError as err:
        connection.send_error(msg["id"], "invalid_request", str(err))


@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_TYPE_GET_SYNC_REFERENCES,
        vol.Required("config_entry_id"): str,
        vol.Required("media_type"): vol.In(["movie", "episode"]),
        vol.Required("media_id"): vol.Coerce(int),
        vol.Required("subtitle_id"): str,
        vol.Optional("series_id"): vol.Coerce(int),
    }
)
@websocket_api.async_response
async def ws_get_sync_references(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Get sync references for a subtitle file."""
    await _ws_get_sync_references(hass, connection, msg)


async def _ws_sync_subtitle(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Sync a subtitle."""
    entry_id = msg["config_entry_id"]
    media_type = msg["media_type"]
    media_id = msg["media_id"]
    subtitle_id = msg["subtitle_id"]
    reference_id = msg.get("reference_id")
    hearing_impaired = msg.get("hearing_impaired", False)
    forced = msg.get("forced", False)
    original_format = msg.get("original_format", False)
    max_offset_seconds = msg.get("max_offset_seconds")
    no_fix_framerate = msg.get("no_fix_framerate", False)
    gss = msg.get("gss", False)
    series_id = msg.get("series_id")

    client = _get_client(hass, entry_id)

    try:
        # Resolve subtitle path server-side from installed subtitles using subtitle_id
        path = await client.async_get_installed_subtitle_path(
            media_type=media_type,
            media_id=media_id,
            subtitle_id=subtitle_id,
            series_id=series_id,
        )
        if path is None:
            connection.send_error(
                msg["id"],
                "subtitle_not_found",
                f"Installed subtitle '{subtitle_id}' not found for media {media_id}",
            )
            return

        # Validate reference_id if provided
        if reference_id is not None:
            ref_valid = await client.async_get_sync_reference_identifier(
                media_type=media_type,
                media_id=media_id,
                reference_id=reference_id,
                series_id=series_id,
            )
            if ref_valid is None:
                connection.send_error(
                    msg["id"],
                    "reference_not_found",
                    f"Sync reference '{reference_id}' not found for media {media_id}",
                )
                return

        await client.async_sync_subtitle(
            action="sync",
            language="",
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

        connection.send_result(msg["id"], {"success": True})
    except BazarrError as err:
        connection.send_error(msg["id"], "bazarr_error", str(err))
    except ValueError as err:
        connection.send_error(msg["id"], "invalid_request", str(err))


@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_TYPE_SYNC_SUBTITLE,
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
@websocket_api.async_response
async def ws_sync_subtitle(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Sync a subtitle."""
    await _ws_sync_subtitle(hass, connection, msg)


def async_register_websocket_commands(hass: HomeAssistant) -> None:
    """Register WebSocket commands."""
    websocket_api.async_register_command(hass, ws_get_media)
    websocket_api.async_register_command(hass, ws_get_subtitles)
    websocket_api.async_register_command(hass, ws_search_subtitles)
    websocket_api.async_register_command(hass, ws_download_subtitle)
    websocket_api.async_register_command(hass, ws_get_sync_references)
    websocket_api.async_register_command(hass, ws_sync_subtitle)
