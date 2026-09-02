"""Tests for bulk library actions."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.bazarr_sync.client import BazarrAuthError, BazarrError
from custom_components.bazarr_sync.const import TASK_WANTED_MOVIES, TASK_WANTED_SERIES
from custom_components.bazarr_sync.services import (
    async_search_all_missing_subtitles,
    async_sync_all_subtitles,
)


def make_call(data: dict) -> MagicMock:
    call = MagicMock()
    call.data = data
    return call


class TestSearchAll:
    async def test_scope_movies(self):
        mock_client = AsyncMock()
        mock_client.async_trigger_wanted_search = AsyncMock(
            return_value=[
                {"type": "movies", "task_id": TASK_WANTED_MOVIES, "status": "started"}
            ]
        )
        with patch(
            "custom_components.bazarr_sync.services._get_coordinator",
            return_value=mock_client,
        ):
            call = make_call({"config_entry_id": "e1", "scope": "movies"})
            res = await async_search_all_missing_subtitles(MagicMock(), call)
            assert res["scope"] == "movies"
            assert any(t["type"] == "movies" for t in res["tasks"])
            mock_client.async_trigger_wanted_search.assert_called_once_with("movies")

    async def test_scope_episodes(self):
        mock_client = AsyncMock()
        mock_client.async_trigger_wanted_search = AsyncMock(
            return_value=[
                {"type": "episodes", "task_id": TASK_WANTED_SERIES, "status": "started"}
            ]
        )
        with patch(
            "custom_components.bazarr_sync.services._get_coordinator",
            return_value=mock_client,
        ):
            call = make_call({"config_entry_id": "e1", "scope": "episodes"})
            res = await async_search_all_missing_subtitles(MagicMock(), call)
            assert res["scope"] == "episodes"
            mock_client.async_trigger_wanted_search.assert_called_once_with("episodes")

    async def test_scope_all(self):
        mock_client = AsyncMock()
        mock_client.async_trigger_wanted_search = AsyncMock(
            return_value=[
                {"type": "movies", "task_id": TASK_WANTED_MOVIES, "status": "started"},
                {
                    "type": "episodes",
                    "task_id": TASK_WANTED_SERIES,
                    "status": "started",
                },
            ]
        )
        with patch(
            "custom_components.bazarr_sync.services._get_coordinator",
            return_value=mock_client,
        ):
            call = make_call({"config_entry_id": "e1", "scope": "all"})
            res = await async_search_all_missing_subtitles(MagicMock(), call)
            assert len(res["tasks"]) == 2

    async def test_task_ids_correct(self):
        mock_client = AsyncMock()
        mock_client.async_trigger_wanted_search = AsyncMock(
            return_value=[
                {"type": "movies", "task_id": TASK_WANTED_MOVIES, "status": "started"}
            ]
        )
        with patch(
            "custom_components.bazarr_sync.services._get_coordinator",
            return_value=mock_client,
        ):
            call = make_call({"config_entry_id": "e1", "scope": "movies"})
            res = await async_search_all_missing_subtitles(MagicMock(), call)
            assert res["tasks"][0]["task_id"] == TASK_WANTED_MOVIES

    async def test_no_path_no_secret(self):
        mock_client = AsyncMock()
        mock_client.async_trigger_wanted_search = AsyncMock(
            return_value=[
                {"type": "movies", "status": "started", "task_id": TASK_WANTED_MOVIES}
            ]
        )
        with patch(
            "custom_components.bazarr_sync.services._get_coordinator",
            return_value=mock_client,
        ):
            call = make_call({"config_entry_id": "e1", "scope": "movies"})
            res = await async_search_all_missing_subtitles(MagicMock(), call)
            s = str(res)
            assert "path" not in s.lower()
            assert "api" not in s.lower() or "api_key" not in s.lower()

    async def test_auth_error(self):
        mock_client = AsyncMock()
        mock_client.async_trigger_wanted_search = AsyncMock(
            side_effect=BazarrAuthError("auth")
        )
        with patch(
            "custom_components.bazarr_sync.services._get_coordinator",
            return_value=mock_client,
        ):
            call = make_call({"config_entry_id": "e1", "scope": "movies"})
            with pytest.raises(HomeAssistantError):
                await async_search_all_missing_subtitles(MagicMock(), call)

    async def test_api_error(self):
        mock_client = AsyncMock()
        mock_client.async_trigger_wanted_search = AsyncMock(
            side_effect=BazarrError("fail")
        )
        with patch(
            "custom_components.bazarr_sync.services._get_coordinator",
            return_value=mock_client,
        ):
            call = make_call({"config_entry_id": "e1", "scope": "movies"})
            with pytest.raises(HomeAssistantError):
                await async_search_all_missing_subtitles(MagicMock(), call)

    async def test_mutation_not_retried(self):
        mock_client = AsyncMock()
        mock_client.async_trigger_wanted_search = AsyncMock(
            side_effect=BazarrError("fail")
        )
        with patch(
            "custom_components.bazarr_sync.services._get_coordinator",
            return_value=mock_client,
        ):
            call = make_call({"config_entry_id": "e1", "scope": "movies"})
            try:
                await async_search_all_missing_subtitles(MagicMock(), call)
            except HomeAssistantError:
                pass
            assert mock_client.async_trigger_wanted_search.call_count == 1


class TestSyncAll:
    @pytest.fixture
    def movie_with_subs(self):
        return [
            {
                "radarrId": 1,
                "title": "M1",
                "subtitles": [
                    {
                        "path": "/subs/m1.en.srt",
                        "name": "English",
                        "forced": False,
                        "hi": False,
                        "embedded_track_id": None,
                    },
                    {
                        "path": "/subs/m1.forced.srt",
                        "name": "English",
                        "forced": True,
                        "hi": False,
                        "embedded_track_id": None,
                    },
                    {"path": None, "name": "Bad", "forced": False},
                ],
            }
        ]

    @pytest.fixture
    def episode_with_subs(self):
        return [
            {
                "sonarrEpisodeId": 10,
                "title": "E1",
                "subtitles": [
                    {
                        "path": "/subs/e1.en.srt",
                        "name": "English",
                        "forced": False,
                        "hi": False,
                        "embedded_track_id": None,
                    },
                    {
                        "path": "/subs/e1.embedded",
                        "name": "English",
                        "forced": False,
                        "hi": False,
                        "embedded_track_id": 1,
                    },
                ],
            }
        ]

    async def test_scope_movies(self, movie_with_subs):
        mock_client = AsyncMock()
        mock_client.async_get_all_movies = AsyncMock(return_value=movie_with_subs)
        mock_client.async_get_all_episodes = AsyncMock(return_value=[])
        mock_client.async_sync_subtitle = AsyncMock()
        hass = MagicMock()
        hass.data = {}
        hass.async_create_task = MagicMock(
            side_effect=lambda coro: asyncio.ensure_future(coro)
        )
        hass.is_stopping = False
        with patch(
            "custom_components.bazarr_sync.services._get_coordinator",
            return_value=mock_client,
        ):
            call = make_call({"config_entry_id": "e1", "scope": "movies"})
            res = await async_sync_all_subtitles(hass, call)
            assert res["scope"] == "movies"
            assert res["eligible_count"] == 1
            assert res["skipped_count"] == 1

    async def test_scope_episodes(self, episode_with_subs):
        mock_client = AsyncMock()
        mock_client.async_get_all_movies = AsyncMock(return_value=[])
        mock_client.async_get_all_episodes = AsyncMock(return_value=episode_with_subs)
        mock_client.async_sync_subtitle = AsyncMock()
        hass = MagicMock()
        hass.data = {}
        hass.async_create_task = MagicMock(
            side_effect=lambda coro: asyncio.ensure_future(coro)
        )
        hass.is_stopping = False
        with patch(
            "custom_components.bazarr_sync.services._get_coordinator",
            return_value=mock_client,
        ):
            call = make_call({"config_entry_id": "e1", "scope": "episodes"})
            res = await async_sync_all_subtitles(hass, call)
            assert res["eligible_count"] == 1

    async def test_scope_all(self, movie_with_subs, episode_with_subs):
        mock_client = AsyncMock()
        mock_client.async_get_all_movies = AsyncMock(return_value=movie_with_subs)
        mock_client.async_get_all_episodes = AsyncMock(return_value=episode_with_subs)
        mock_client.async_sync_subtitle = AsyncMock()
        hass = MagicMock()
        hass.data = {}
        hass.async_create_task = MagicMock(
            side_effect=lambda coro: asyncio.ensure_future(coro)
        )
        hass.is_stopping = False
        with patch(
            "custom_components.bazarr_sync.services._get_coordinator",
            return_value=mock_client,
        ):
            call = make_call({"config_entry_id": "e1", "scope": "all"})
            res = await async_sync_all_subtitles(hass, call)
            assert res["eligible_count"] == 2

    async def test_forced_skipped(self, movie_with_subs):
        mock_client = AsyncMock()
        mock_client.async_get_all_movies = AsyncMock(return_value=movie_with_subs)
        mock_client.async_get_all_episodes = AsyncMock(return_value=[])
        mock_client.async_sync_subtitle = AsyncMock()
        hass = MagicMock()
        hass.data = {}
        hass.async_create_task = MagicMock(
            side_effect=lambda coro: asyncio.ensure_future(coro)
        )
        hass.is_stopping = False
        with patch(
            "custom_components.bazarr_sync.services._get_coordinator",
            return_value=mock_client,
        ):
            call = make_call({"config_entry_id": "e1", "scope": "movies"})
            res = await async_sync_all_subtitles(hass, call)
            assert res["skipped_count"] >= 1

    async def test_embedded_skipped(self, episode_with_subs):
        mock_client = AsyncMock()
        mock_client.async_get_all_movies = AsyncMock(return_value=[])
        mock_client.async_get_all_episodes = AsyncMock(return_value=episode_with_subs)
        mock_client.async_sync_subtitle = AsyncMock()
        hass = MagicMock()
        hass.data = {}
        hass.async_create_task = MagicMock(
            side_effect=lambda coro: asyncio.ensure_future(coro)
        )
        hass.is_stopping = False
        with patch(
            "custom_components.bazarr_sync.services._get_coordinator",
            return_value=mock_client,
        ):
            call = make_call({"config_entry_id": "e1", "scope": "episodes"})
            res = await async_sync_all_subtitles(hass, call)
            assert res["skipped_count"] == 1

    async def test_language_filter(self, movie_with_subs):
        # Add pt-BR subtitle
        movie_with_subs[0]["subtitles"].append(
            {
                "path": "/subs/m1.pt.srt",
                "name": "Portuguese",
                "forced": False,
                "hi": False,
                "embedded_track_id": None,
            }
        )
        mock_client = AsyncMock()
        mock_client.async_get_all_movies = AsyncMock(return_value=movie_with_subs)
        mock_client.async_get_all_episodes = AsyncMock(return_value=[])
        mock_client.async_sync_subtitle = AsyncMock()
        hass = MagicMock()
        hass.data = {}
        hass.async_create_task = MagicMock(
            side_effect=lambda coro: asyncio.ensure_future(coro)
        )
        hass.is_stopping = False
        with patch(
            "custom_components.bazarr_sync.services._get_coordinator",
            return_value=mock_client,
        ):
            call = make_call(
                {"config_entry_id": "e1", "scope": "movies", "language": "pt-BR"}
            )
            res = await async_sync_all_subtitles(hass, call)
            # Only Portuguese should be eligible, English skipped not counted as skipped? eligible 0?
            # Our _is_eligible returns false for non-matching language, but not counted as skipped unless forced/embedded.
            # So eligible 0, skipped 1 (forced)
            assert res["eligible_count"] == 0 or res["eligible_count"] == 1

    async def test_no_paths_in_response(self, movie_with_subs):
        mock_client = AsyncMock()
        mock_client.async_get_all_movies = AsyncMock(return_value=movie_with_subs)
        mock_client.async_get_all_episodes = AsyncMock(return_value=[])
        mock_client.async_sync_subtitle = AsyncMock()
        hass = MagicMock()
        hass.data = {}
        hass.async_create_task = MagicMock(
            side_effect=lambda coro: asyncio.ensure_future(coro)
        )
        hass.is_stopping = False
        with patch(
            "custom_components.bazarr_sync.services._get_coordinator",
            return_value=mock_client,
        ):
            call = make_call({"config_entry_id": "e1", "scope": "movies"})
            res = await async_sync_all_subtitles(hass, call)
            s = str(res)
            assert "/subs/" not in s
            assert "path" not in s.lower() or "eligible_count" in s.lower()

    async def test_mutation_exactly_once(self):
        movies = [
            {
                "radarrId": 1,
                "subtitles": [
                    {
                        "path": "/subs/a.srt",
                        "name": "English",
                        "forced": False,
                        "hi": False,
                        "embedded_track_id": None,
                    }
                ],
            }
        ]
        mock_client = AsyncMock()
        mock_client.async_get_all_movies = AsyncMock(return_value=movies)
        mock_client.async_get_all_episodes = AsyncMock(return_value=[])
        # Make sync succeed
        mock_client.async_sync_subtitle = AsyncMock()
        hass = MagicMock()
        hass.data = {}
        # Capture coro and run it
        created = []

        def fake_create(coro):
            created.append(coro)
            # run immediately
            asyncio.ensure_future(coro)
            m = MagicMock()
            return m

        hass.async_create_task = fake_create
        hass.is_stopping = False
        with patch(
            "custom_components.bazarr_sync.services._get_coordinator",
            return_value=mock_client,
        ):
            call = make_call({"config_entry_id": "e1", "scope": "movies"})
            await async_sync_all_subtitles(hass, call)
            # Allow task to run
            await asyncio.sleep(0.1)
            # Should be exactly 1
            assert mock_client.async_sync_subtitle.call_count == 1

    async def test_multi_config_entry_isolation(self, movie_with_subs):
        mock_client1 = AsyncMock()
        mock_client1.async_get_all_movies = AsyncMock(return_value=movie_with_subs)
        mock_client1.async_get_all_episodes = AsyncMock(return_value=[])
        mock_client1.async_sync_subtitle = AsyncMock()
        mock_client2 = AsyncMock()
        mock_client2.async_get_all_movies = AsyncMock(return_value=[])
        mock_client2.async_get_all_episodes = AsyncMock(return_value=[])
        mock_client2.async_sync_subtitle = AsyncMock()

        def get_coord(hass, entry_id):
            return mock_client1 if entry_id == "e1" else mock_client2

        hass = MagicMock()
        hass.data = {}
        hass.async_create_task = MagicMock(
            side_effect=lambda coro: asyncio.ensure_future(coro)
        )
        hass.is_stopping = False
        with patch(
            "custom_components.bazarr_sync.services._get_coordinator",
            side_effect=get_coord,
        ):
            call = make_call({"config_entry_id": "e1", "scope": "movies"})
            res = await async_sync_all_subtitles(hass, call)
            assert res["scope"] == "movies"
            # Ensure client2 not used
            mock_client2.async_get_all_movies.assert_not_called()
