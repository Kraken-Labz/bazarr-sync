"""Tests for services."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.bazarr_sync.client import BazarrClient, BazarrError
from custom_components.bazarr_sync.services import (
    async_search_subtitles,
    async_download_subtitle,
    async_sync_subtitle,
)


@pytest.fixture
def hass():
    """Mock Home Assistant."""
    hass = MagicMock(spec=HomeAssistant)
    return hass


@pytest.fixture
def mock_entry():
    """Mock config entry with client."""
    entry = MagicMock()
    entry.entry_id = "test-entry"
    return entry


@pytest.fixture
def mock_client():
    """Mock BazarrClient."""
    return AsyncMock(spec=BazarrClient)


def make_service_call(data: dict) -> MagicMock:
    """Create a mock service call."""
    call = MagicMock()
    call.data = data
    return call


class TestServices:
    """Test HA services."""

    async def test_search_subtitles_movie(self, hass, mock_entry, mock_client):
        """Test search subtitles for movie."""
        with patch(
            "custom_components.bazarr_sync.services._get_coordinator",
            return_value=mock_client,
        ):
            mock_client.async_search_movie_subtitles.return_value = [
                {"provider": "opensubtitles", "subtitle": "sub1", "language": "en"}
            ]

            call = make_service_call(
                {
                    "config_entry_id": "test-entry",
                    "media_type": "movie",
                    "media_id": 1,
                }
            )

            result = await async_search_subtitles(hass, call)

            assert "candidates" in result
            assert len(result["candidates"]) == 1
            mock_client.async_search_movie_subtitles.assert_called_once_with(1)

    async def test_search_subtitles_episode(self, hass, mock_entry, mock_client):
        """Test search subtitles for episode."""
        with patch(
            "custom_components.bazarr_sync.services._get_coordinator",
            return_value=mock_client,
        ):
            mock_client.async_search_episode_subtitles.return_value = [
                {"provider": "opensubtitles", "subtitle": "sub1", "language": "en"}
            ]

            call = make_service_call(
                {
                    "config_entry_id": "test-entry",
                    "media_type": "episode",
                    "media_id": 1,
                    "series_id": 2,
                }
            )

            result = await async_search_subtitles(hass, call)

            assert "candidates" in result
            mock_client.async_search_episode_subtitles.assert_called_once_with(1)

    async def test_search_subtitles_episode_missing_series_id(
        self, hass, mock_entry, mock_client
    ):
        """Test search subtitles for episode without series_id raises error."""
        with patch(
            "custom_components.bazarr_sync.services._get_coordinator",
            return_value=mock_client,
        ):
            call = make_service_call(
                {
                    "config_entry_id": "test-entry",
                    "media_type": "episode",
                    "media_id": 1,
                }
            )

            with pytest.raises(
                HomeAssistantError, match="series_id is required for episodes"
            ):
                await async_search_subtitles(hass, call)

    async def test_search_subtitles_bazarr_error(self, hass, mock_entry, mock_client):
        """Test search subtitles handles BazarrError."""
        with patch(
            "custom_components.bazarr_sync.services._get_coordinator",
            return_value=mock_client,
        ):
            mock_client.async_search_movie_subtitles.side_effect = BazarrError(
                "API error"
            )

            call = make_service_call(
                {
                    "config_entry_id": "test-entry",
                    "media_type": "movie",
                    "media_id": 1,
                }
            )

            with pytest.raises(HomeAssistantError, match="Bazarr error: API error"):
                await async_search_subtitles(hass, call)

    async def test_download_subtitle_movie(self, hass, mock_entry, mock_client):
        """Test download subtitle for movie."""
        with patch(
            "custom_components.bazarr_sync.services._get_coordinator",
            return_value=mock_client,
        ):
            call = make_service_call(
                {
                    "config_entry_id": "test-entry",
                    "media_type": "movie",
                    "media_id": 1,
                    "provider": "opensubtitles",
                    "subtitle": "sub1",
                    "language": "en",
                    "hearing_impaired": True,
                    "forced": False,
                    "original_format": True,
                }
            )

            await async_download_subtitle(hass, call)

            mock_client.async_download_movie_subtitle.assert_called_once_with(
                radarr_id=1,
                provider="opensubtitles",
                subtitle_id="sub1",
                hearing_impaired=True,
                forced=False,
                original_format=True,
            )

    async def test_download_subtitle_episode(self, hass, mock_entry, mock_client):
        """Test download subtitle for episode."""
        with patch(
            "custom_components.bazarr_sync.services._get_coordinator",
            return_value=mock_client,
        ):
            call = make_service_call(
                {
                    "config_entry_id": "test-entry",
                    "media_type": "episode",
                    "media_id": 1,
                    "series_id": 2,
                    "provider": "opensubtitles",
                    "subtitle": "sub1",
                    "language": "en",
                }
            )

            await async_download_subtitle(hass, call)

            mock_client.async_download_episode_subtitle.assert_called_once_with(
                series_id=2,
                episode_id=1,
                provider="opensubtitles",
                subtitle_id="sub1",
                hearing_impaired=False,
                forced=False,
                original_format=False,
            )

    async def test_download_subtitle_episode_missing_series_id(
        self, hass, mock_entry, mock_client
    ):
        """Test download subtitle for episode without series_id raises error."""
        with patch(
            "custom_components.bazarr_sync.services._get_coordinator",
            return_value=mock_client,
        ):
            call = make_service_call(
                {
                    "config_entry_id": "test-entry",
                    "media_type": "episode",
                    "media_id": 1,
                    "provider": "opensubtitles",
                    "subtitle": "sub1",
                    "language": "en",
                }
            )

            with pytest.raises(
                HomeAssistantError, match="series_id is required for episodes"
            ):
                await async_download_subtitle(hass, call)

    async def test_sync_subtitle(self, hass, mock_entry, mock_client):
        """Test sync subtitle."""
        with patch(
            "custom_components.bazarr_sync.services._get_coordinator",
            return_value=mock_client,
        ):
            # Mock the path resolution
            mock_client.async_get_installed_subtitle_path.return_value = (
                "/subs/movie.en.srt"
            )
            mock_client.async_get_sync_reference_identifier.return_value = "a:0"
            call = make_service_call(
                {
                    "config_entry_id": "test-entry",
                    "media_type": "movie",
                    "media_id": 1,
                    "subtitle_id": "/subs/movie.en.srt",
                    "reference_id": "a:0",
                    "hearing_impaired": False,
                    "forced": True,
                    "original_format": False,
                    "max_offset_seconds": 30,
                    "no_fix_framerate": True,
                    "gss": False,
                }
            )

            await async_sync_subtitle(hass, call)

            mock_client.async_get_installed_subtitle_path.assert_called_once_with(
                media_type="movie",
                media_id=1,
                subtitle_id="/subs/movie.en.srt",
                series_id=None,
            )
            mock_client.async_get_sync_reference_identifier.assert_called_once_with(
                media_type="movie", media_id=1, reference_id="a:0", series_id=None
            )
            mock_client.async_sync_subtitle.assert_called_once_with(
                action="sync",
                language="",
                path="/subs/movie.en.srt",
                media_type="movie",
                media_id=1,
                forced=True,
                hearing_impaired=False,
                original_format=False,
                reference="a:0",
                max_offset_seconds="30",
                no_fix_framerate=True,
                gss=False,
            )

    async def test_sync_subtitle_without_optional_params(
        self, hass, mock_entry, mock_client
    ):
        """Test sync subtitle without optional params."""
        with patch(
            "custom_components.bazarr_sync.services._get_coordinator",
            return_value=mock_client,
        ):
            # Mock the path resolution
            mock_client.async_get_installed_subtitle_path.return_value = (
                "/subs/movie.en.srt"
            )
            call = make_service_call(
                {
                    "config_entry_id": "test-entry",
                    "media_type": "movie",
                    "media_id": 1,
                    "subtitle_id": "/subs/movie.en.srt",
                }
            )

            await async_sync_subtitle(hass, call)

            mock_client.async_get_installed_subtitle_path.assert_called_once_with(
                media_type="movie",
                media_id=1,
                subtitle_id="/subs/movie.en.srt",
                series_id=None,
            )
            mock_client.async_sync_subtitle.assert_called_once()
            kwargs = mock_client.async_sync_subtitle.call_args[1]
            assert kwargs["reference"] is None
            assert kwargs["max_offset_seconds"] is None

    # Negative tests for path security
    async def test_sync_subtitle_forged_subtitle_id_rejected(
        self, hass, mock_entry, mock_client
    ):
        """Test that forged subtitle_id is rejected."""
        with patch(
            "custom_components.bazarr_sync.services._get_coordinator",
            return_value=mock_client,
        ):
            mock_client.async_get_installed_subtitle_path.return_value = None
            call = make_service_call(
                {
                    "config_entry_id": "test-entry",
                    "media_type": "movie",
                    "media_id": 1,
                    "subtitle_id": "/etc/passwd",  # Arbitrary path
                }
            )

            with pytest.raises(HomeAssistantError, match="not found"):
                await async_sync_subtitle(hass, call)

            mock_client.async_get_installed_subtitle_path.assert_called_once_with(
                media_type="movie",
                media_id=1,
                subtitle_id="/etc/passwd",
                series_id=None,
            )
            mock_client.async_sync_subtitle.assert_not_called()

    async def test_sync_subtitle_forged_reference_id_rejected(
        self, hass, mock_entry, mock_client
    ):
        """Test that forged reference_id is rejected."""
        with patch(
            "custom_components.bazarr_sync.services._get_coordinator",
            return_value=mock_client,
        ):
            mock_client.async_get_installed_subtitle_path.return_value = (
                "/subs/movie.en.srt"
            )
            mock_client.async_get_sync_reference_identifier.return_value = None
            call = make_service_call(
                {
                    "config_entry_id": "test-entry",
                    "media_type": "movie",
                    "media_id": 1,
                    "subtitle_id": "/subs/movie.en.srt",
                    "reference_id": "s:999",  # Non-existent reference
                }
            )

            with pytest.raises(HomeAssistantError, match="not found"):
                await async_sync_subtitle(hass, call)

            mock_client.async_get_sync_reference_identifier.assert_called_once_with(
                media_type="movie", media_id=1, reference_id="s:999", series_id=None
            )
            mock_client.async_sync_subtitle.assert_not_called()

    async def test_sync_subtitle_subtitle_id_from_other_media_rejected(
        self, hass, mock_entry, mock_client
    ):
        """Test that subtitle_id from another media is rejected."""
        with patch(
            "custom_components.bazarr_sync.services._get_coordinator",
            return_value=mock_client,
        ):
            # Subtitle exists but for different media_id
            mock_client.async_get_installed_subtitle_path.return_value = None
            call = make_service_call(
                {
                    "config_entry_id": "test-entry",
                    "media_type": "movie",
                    "media_id": 999,  # Different media
                    "subtitle_id": "/subs/movie.en.srt",  # Valid subtitle but for media_id=1
                }
            )

            with pytest.raises(HomeAssistantError, match="not found"):
                await async_sync_subtitle(hass, call)
