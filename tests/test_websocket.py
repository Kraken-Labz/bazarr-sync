"""Tests for WebSocket API."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.bazarr_sync.client import BazarrClient, BazarrError
from custom_components.bazarr_sync.websocket import async_register_websocket_commands
from custom_components.bazarr_sync.const import (
    WS_TYPE_DOWNLOAD_SUBTITLE,
    WS_TYPE_GET_MEDIA,
    WS_TYPE_GET_SUBTITLES,
    WS_TYPE_GET_SYNC_REFERENCES,
    WS_TYPE_SEARCH_SUBTITLES,
    WS_TYPE_SYNC_SUBTITLE,
)


@pytest.fixture
def hass():
    """Mock Home Assistant."""
    return MagicMock(spec=HomeAssistant)


@pytest.fixture
def mock_client():
    """Mock BazarrClient."""
    return AsyncMock(spec=BazarrClient)


@pytest.fixture
def mock_connection():
    """Mock WebSocket connection."""
    conn = AsyncMock(spec=websocket_api.ActiveConnection)
    conn.send_result = MagicMock()
    conn.send_error = MagicMock()
    return conn


class TestWebSocket:
    """Test WebSocket commands."""

    async def test_ws_get_media_movies(self, hass, mock_client, mock_connection):
        """Test get media movies."""
        with patch(
            "custom_components.bazarr_sync.websocket._get_client",
            return_value=mock_client,
        ):
            mock_client.async_get_movies.return_value = {
                "data": [
                    {
                        "radarrId": 1,
                        "title": "Movie 1",
                        "path": "/movies/1",
                        "year": "2023",
                        "poster": "/poster.jpg",
                    }
                ],
                "total": 1,
            }

            msg = {
                "id": 1,
                "type": WS_TYPE_GET_MEDIA,
                "config_entry_id": "test-entry",
                "media_type": "movies",
            }

            # Import and call the internal handler directly
            from custom_components.bazarr_sync.websocket import _ws_get_media

            await _ws_get_media(hass, mock_connection, msg)

            mock_connection.send_result.assert_called_once()
            args = mock_connection.send_result.call_args[0]
            assert args[0] == 1  # msg id
            result = args[1]
            assert "media" in result
            assert len(result["media"]) == 1
            assert result["media"][0]["radarrId"] == 1

    async def test_ws_get_media_episodes(self, hass, mock_client, mock_connection):
        """Test get media episodes."""
        with patch(
            "custom_components.bazarr_sync.websocket._get_client",
            return_value=mock_client,
        ):
            mock_client.async_get_episodes.return_value = [
                {
                    "sonarrEpisodeId": 1,
                    "sonarrSeriesId": 2,
                    "title": "Ep 1",
                    "path": "/episodes/1",
                    "season": 1,
                    "episode": 1,
                }
            ]

            msg = {
                "id": 2,
                "type": WS_TYPE_GET_MEDIA,
                "config_entry_id": "test-entry",
                "media_type": "episodes",
                "series_id": 2,
            }

            from custom_components.bazarr_sync.websocket import _ws_get_media

            await _ws_get_media(hass, mock_connection, msg)

            mock_connection.send_result.assert_called_once()
            args = mock_connection.send_result.call_args[0]
            result = args[1]
            assert result["media"][0]["sonarrEpisodeId"] == 1

    async def test_ws_get_media_episodes_missing_series_id(
        self, hass, mock_client, mock_connection
    ):
        """Test get media episodes without series_id."""
        with patch(
            "custom_components.bazarr_sync.websocket._get_client",
            return_value=mock_client,
        ):
            msg = {
                "id": 3,
                "type": WS_TYPE_GET_MEDIA,
                "config_entry_id": "test-entry",
                "media_type": "episodes",
            }

            from custom_components.bazarr_sync.websocket import _ws_get_media

            with pytest.raises(
                HomeAssistantError, match="series_id is required for episodes"
            ):
                await _ws_get_media(hass, mock_connection, msg)

    async def test_ws_get_media_series(self, hass, mock_client, mock_connection):
        """Test get media series."""
        with patch(
            "custom_components.bazarr_sync.websocket._get_client",
            return_value=mock_client,
        ):
            mock_client.async_get_series.return_value = {
                "data": [
                    {
                        "sonarrSeriesId": 1,
                        "title": "Series 1",
                        "path": "/series/1",
                        "year": "2023",
                        "poster": "/poster.jpg",
                        "episodeFileCount": 10,
                        "episodeMissingCount": 2,
                    }
                ],
                "total": 1,
            }

            msg = {
                "id": 4,
                "type": WS_TYPE_GET_MEDIA,
                "config_entry_id": "test-entry",
                "media_type": "series",
            }

            from custom_components.bazarr_sync.websocket import _ws_get_media

            await _ws_get_media(hass, mock_connection, msg)

            mock_connection.send_result.assert_called_once()
            args = mock_connection.send_result.call_args[0]
            result = args[1]
            assert result["media"][0]["sonarrSeriesId"] == 1

    async def test_ws_get_subtitles(self, hass, mock_client, mock_connection):
        """Test get subtitles."""
        with patch(
            "custom_components.bazarr_sync.websocket._get_client",
            return_value=mock_client,
        ):
            mock_client.async_get_movies.return_value = {
                "data": [
                    {
                        "subtitles": [
                            {
                                "path": "/subs/movie.en.srt",
                                "name": "English",
                                "code2": "en",
                                "code3": "eng",
                                "forced": True,
                                "hi": False,
                                "file_size": 1024,
                                "embedded_track_id": 0,
                            }
                        ]
                    }
                ]
            }
            mock_client._generate_subtitle_id.return_value = "abc123def456"

            msg = {
                "id": 5,
                "type": WS_TYPE_GET_SUBTITLES,
                "config_entry_id": "test-entry",
                "media_type": "movie",
                "media_id": 1,
            }

            from custom_components.bazarr_sync.websocket import _ws_get_subtitles

            await _ws_get_subtitles(hass, mock_connection, msg)

            mock_connection.send_result.assert_called_once()
            args = mock_connection.send_result.call_args[0]
            result = args[1]
            assert "subtitles" in result
            assert len(result["subtitles"]) == 1
            assert result["subtitles"][0]["subtitle_id"] is not None
            assert isinstance(result["subtitles"][0]["subtitle_id"], str)

    async def test_ws_search_subtitles(self, hass, mock_client, mock_connection):
        """Test search subtitles."""
        with patch(
            "custom_components.bazarr_sync.websocket._get_client",
            return_value=mock_client,
        ):
            mock_client.async_search_movie_subtitles.return_value = [
                {
                    "provider": "opensubtitles",
                    "subtitle": "sub1",
                    "language": "en",
                    "score": 95,
                }
            ]

            msg = {
                "id": 6,
                "type": WS_TYPE_SEARCH_SUBTITLES,
                "config_entry_id": "test-entry",
                "media_type": "movie",
                "media_id": 1,
            }

            from custom_components.bazarr_sync.websocket import _ws_search_subtitles

            await _ws_search_subtitles(hass, mock_connection, msg)

            mock_connection.send_result.assert_called_once()
            args = mock_connection.send_result.call_args[0]
            result = args[1]
            assert "candidates" in result
            assert len(result["candidates"]) == 1

    async def test_ws_download_subtitle(self, hass, mock_client, mock_connection):
        """Test download subtitle."""
        with patch(
            "custom_components.bazarr_sync.websocket._get_client",
            return_value=mock_client,
        ):
            msg = {
                "id": 7,
                "type": WS_TYPE_DOWNLOAD_SUBTITLE,
                "config_entry_id": "test-entry",
                "media_type": "movie",
                "media_id": 1,
                "provider": "opensubtitles",
                "subtitle": "sub1",
                "language": "en",
            }

            from custom_components.bazarr_sync.websocket import _ws_download_subtitle

            await _ws_download_subtitle(hass, mock_connection, msg)

            mock_connection.send_result.assert_called_once()
            args = mock_connection.send_result.call_args[0]
            result = args[1]
            assert result["success"] is True
            mock_client.async_download_movie_subtitle.assert_called_once()

    async def test_ws_get_sync_references(self, hass, mock_client, mock_connection):
        """Test get sync references."""
        with patch(
            "custom_components.bazarr_sync.websocket._get_client",
            return_value=mock_client,
        ):
            mock_client.async_get_installed_subtitle_path.return_value = (
                "/subs/movie.en.srt"
            )
            mock_client.async_get_sync_references.return_value = {
                "audio_tracks": [
                    {"stream": "a:0", "name": "English", "language": "en"}
                ],
                "embedded_subtitles_tracks": [],
                "external_subtitles_tracks": [],
            }

            msg = {
                "id": 8,
                "type": WS_TYPE_GET_SYNC_REFERENCES,
                "config_entry_id": "test-entry",
                "media_type": "movie",
                "media_id": 1,
                "subtitle_id": "/subs/movie.en.srt",
            }

            from custom_components.bazarr_sync.websocket import _ws_get_sync_references

            await _ws_get_sync_references(hass, mock_connection, msg)

            mock_client.async_get_installed_subtitle_path.assert_called_once_with(
                media_type="movie",
                media_id=1,
                subtitle_id="/subs/movie.en.srt",
                series_id=None,
            )
            mock_connection.send_result.assert_called_once()
            args = mock_connection.send_result.call_args[0]
            result = args[1]
            assert "audio_tracks" in result
            assert len(result["audio_tracks"]) == 1

    async def test_ws_sync_subtitle(self, hass, mock_client, mock_connection):
        """Test sync subtitle."""
        with patch(
            "custom_components.bazarr_sync.websocket._get_client",
            return_value=mock_client,
        ):
            mock_client.async_get_installed_subtitle_path.return_value = (
                "/subs/movie.en.srt"
            )
            mock_client.async_get_sync_reference_identifier.return_value = "a:0"
            msg = {
                "id": 9,
                "type": WS_TYPE_SYNC_SUBTITLE,
                "config_entry_id": "test-entry",
                "media_type": "movie",
                "media_id": 1,
                "subtitle_id": "/subs/movie.en.srt",
                "reference_id": "a:0",
            }

            from custom_components.bazarr_sync.websocket import _ws_sync_subtitle

            await _ws_sync_subtitle(hass, mock_connection, msg)

            mock_client.async_get_installed_subtitle_path.assert_called_once_with(
                media_type="movie",
                media_id=1,
                subtitle_id="/subs/movie.en.srt",
                series_id=None,
            )
            mock_client.async_get_sync_reference_identifier.assert_called_once_with(
                media_type="movie", media_id=1, reference_id="a:0", series_id=None
            )
            mock_connection.send_result.assert_called_once()
            args = mock_connection.send_result.call_args[0]
            result = args[1]
            assert result["success"] is True
            mock_client.async_sync_subtitle.assert_called_once()
            sync_kwargs = mock_client.async_sync_subtitle.call_args[1]
            assert sync_kwargs["reference"] == "a:0"

    async def test_ws_sync_subtitle_external_reference_resolves_to_path(
        self, hass, mock_client, mock_connection
    ):
        """External opaque reference_id resolves to the real path sent to Bazarr."""
        with patch(
            "custom_components.bazarr_sync.websocket._get_client",
            return_value=mock_client,
        ):
            mock_client.async_get_installed_subtitle_path.return_value = (
                "/subs/movie.en.srt"
            )
            mock_client.async_get_sync_reference_identifier.return_value = (
                "/internal/example.en.srt"
            )
            msg = {
                "id": 14,
                "type": WS_TYPE_SYNC_SUBTITLE,
                "config_entry_id": "test-entry",
                "media_type": "movie",
                "media_id": 1,
                "subtitle_id": "/subs/movie.en.srt",
                "reference_id": "abc123def4567890",
            }

            from custom_components.bazarr_sync.websocket import _ws_sync_subtitle

            await _ws_sync_subtitle(hass, mock_connection, msg)

            mock_client.async_get_sync_reference_identifier.assert_called_once_with(
                media_type="movie",
                media_id=1,
                reference_id="abc123def4567890",
                series_id=None,
            )
            mock_connection.send_result.assert_called_once()
            mock_client.async_sync_subtitle.assert_called_once()
            sync_kwargs = mock_client.async_sync_subtitle.call_args[1]
            assert sync_kwargs["reference"] == "/internal/example.en.srt"

    async def test_ws_bazarr_error_handling(self, hass, mock_client, mock_connection):
        """Test WebSocket handles BazarrError."""
        with patch(
            "custom_components.bazarr_sync.websocket._get_client",
            return_value=mock_client,
        ):
            mock_client.async_get_movies.side_effect = BazarrError("API error")

            msg = {
                "id": 10,
                "type": WS_TYPE_GET_MEDIA,
                "config_entry_id": "test-entry",
                "media_type": "movies",
            }

            from custom_components.bazarr_sync.websocket import _ws_get_media

            await _ws_get_media(hass, mock_connection, msg)

            mock_connection.send_error.assert_called_once()
            args = mock_connection.send_error.call_args[0]
            assert args[0] == 10
            assert args[1] == "bazarr_error"

    # Negative tests for path security
    async def test_ws_get_sync_references_forged_subtitle_id_rejected(
        self, hass, mock_client, mock_connection
    ):
        """Test that forged subtitle_id is rejected in get_sync_references."""
        with patch(
            "custom_components.bazarr_sync.websocket._get_client",
            return_value=mock_client,
        ):
            mock_client.async_get_installed_subtitle_path.return_value = None

            msg = {
                "id": 11,
                "type": WS_TYPE_GET_SYNC_REFERENCES,
                "config_entry_id": "test-entry",
                "media_type": "movie",
                "media_id": 1,
                "subtitle_id": "/etc/passwd",  # Arbitrary path
            }

            from custom_components.bazarr_sync.websocket import _ws_get_sync_references

            await _ws_get_sync_references(hass, mock_connection, msg)

            mock_connection.send_error.assert_called_once()
            args = mock_connection.send_error.call_args[0]
            assert args[0] == 11
            assert args[1] == "subtitle_not_found"

    async def test_ws_sync_subtitle_forged_subtitle_id_rejected(
        self, hass, mock_client, mock_connection
    ):
        """Test that forged subtitle_id is rejected in sync_subtitle."""
        with patch(
            "custom_components.bazarr_sync.websocket._get_client",
            return_value=mock_client,
        ):
            mock_client.async_get_installed_subtitle_path.return_value = None

            msg = {
                "id": 12,
                "type": WS_TYPE_SYNC_SUBTITLE,
                "config_entry_id": "test-entry",
                "media_type": "movie",
                "media_id": 1,
                "subtitle_id": "/etc/passwd",  # Arbitrary path
            }

            from custom_components.bazarr_sync.websocket import _ws_sync_subtitle

            await _ws_sync_subtitle(hass, mock_connection, msg)

            mock_connection.send_error.assert_called_once()
            args = mock_connection.send_error.call_args[0]
            assert args[0] == 12
            assert args[1] == "subtitle_not_found"

    async def test_ws_sync_subtitle_forged_reference_id_rejected(
        self, hass, mock_client, mock_connection
    ):
        """Test that forged reference_id is rejected in sync_subtitle."""
        with patch(
            "custom_components.bazarr_sync.websocket._get_client",
            return_value=mock_client,
        ):
            mock_client.async_get_installed_subtitle_path.return_value = (
                "/subs/movie.en.srt"
            )
            mock_client.async_get_sync_reference_identifier.return_value = None

            msg = {
                "id": 13,
                "type": WS_TYPE_SYNC_SUBTITLE,
                "config_entry_id": "test-entry",
                "media_type": "movie",
                "media_id": 1,
                "subtitle_id": "/subs/movie.en.srt",
                "reference_id": "s:999",  # Non-existent reference
            }

            from custom_components.bazarr_sync.websocket import _ws_sync_subtitle

            await _ws_sync_subtitle(hass, mock_connection, msg)

            mock_connection.send_error.assert_called_once()
            args = mock_connection.send_error.call_args[0]
            assert args[0] == 13
            assert args[1] == "reference_not_found"
