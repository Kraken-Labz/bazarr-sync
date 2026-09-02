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

    async def test_canonical_endpoint(self):
        from custom_components.bazarr_sync.const import API_SYSTEM_TASKS

        mock_client = AsyncMock()
        mock_client.async_get_task_status = AsyncMock(
            return_value={"job_running": False}
        )
        mock_client.async_trigger_task = AsyncMock(return_value={"status": "started"})
        mock_client.async_trigger_wanted_search = AsyncMock(
            wraps=mock_client.async_trigger_wanted_search
        )
        # Directly test client canonical endpoint via _request mock
        from custom_components.bazarr_sync.client import BazarrClient

        client = BazarrClient(MagicMock(), "http://x", "k")
        client._request = AsyncMock(return_value={"status": "started"})
        await client.async_trigger_task("wanted_search_missing_subtitles_movies")
        client._request.assert_called_with(
            "POST",
            API_SYSTEM_TASKS,
            data={"taskid": "wanted_search_missing_subtitles_movies"},
        )

    async def test_already_running(self):
        mock_client = AsyncMock()
        mock_client.async_get_task_status = AsyncMock(
            return_value={"job_running": True}
        )
        mock_client.async_trigger_task = AsyncMock()
        mock_client.async_trigger_wanted_search = AsyncMock(
            side_effect=lambda scope: [
                {
                    "type": "movies",
                    "task_id": TASK_WANTED_MOVIES,
                    "status": "already_running",
                }
            ]
        )
        # Simulate service-level already_running
        with patch(
            "custom_components.bazarr_sync.services._get_coordinator",
            return_value=mock_client,
        ):
            # Mock to return already_running directly
            mock_client.async_trigger_wanted_search = AsyncMock(
                return_value=[
                    {
                        "type": "movies",
                        "task_id": TASK_WANTED_MOVIES,
                        "status": "already_running",
                    }
                ]
            )
            call = make_call({"config_entry_id": "e1", "scope": "movies"})
            res = await async_search_all_missing_subtitles(MagicMock(), call)
            assert res["tasks"][0]["status"] == "already_running"
            assert res["accepted"] is True

    async def test_accepted_false_when_all_error(self):
        mock_client = AsyncMock()
        mock_client.async_trigger_wanted_search = AsyncMock(
            return_value=[
                {"type": "movies", "task_id": TASK_WANTED_MOVIES, "status": "error"},
                {"type": "episodes", "task_id": TASK_WANTED_SERIES, "status": "error"},
            ]
        )
        with patch(
            "custom_components.bazarr_sync.services._get_coordinator",
            return_value=mock_client,
        ):
            call = make_call({"config_entry_id": "e1", "scope": "all"})
            res = await async_search_all_missing_subtitles(MagicMock(), call)
            assert res["accepted"] is False


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
                        "code2": "en",
                        "forced": False,
                        "hi": False,
                        "embedded_track_id": None,
                    },
                    {
                        "path": "/subs/m1.forced.srt",
                        "name": "English",
                        "code2": "en",
                        "forced": True,
                        "hi": False,
                        "embedded_track_id": None,
                    },
                    {"path": None, "name": "Bad", "code2": "en", "forced": False},
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
                        "code2": "en",
                        "forced": False,
                        "hi": False,
                        "embedded_track_id": None,
                    },
                    {
                        "path": "/subs/e1.embedded",
                        "name": "English",
                        "code2": "en",
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
            assert res["status"] == "preparing"
            await asyncio.sleep(0.1)
            from custom_components.bazarr_sync.services import (
                async_get_bulk_sync_status,
            )

            status = await async_get_bulk_sync_status(
                hass, make_call({"config_entry_id": "e1", "job_id": res["job_id"]})
            )
            assert status["total"] == 1
            assert status["skipped"] == 2

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
            assert res["status"] == "preparing"
            await asyncio.sleep(0.1)
            from custom_components.bazarr_sync.services import (
                async_get_bulk_sync_status,
            )

            status = await async_get_bulk_sync_status(
                hass, make_call({"config_entry_id": "e1", "job_id": res["job_id"]})
            )
            assert status["total"] == 1

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
            assert res["status"] == "preparing"
            await asyncio.sleep(0.1)
            from custom_components.bazarr_sync.services import (
                async_get_bulk_sync_status,
            )

            status = await async_get_bulk_sync_status(
                hass, make_call({"config_entry_id": "e1", "job_id": res["job_id"]})
            )
            assert status["total"] == 2

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
            await asyncio.sleep(0.1)
            from custom_components.bazarr_sync.services import (
                async_get_bulk_sync_status,
            )

            status = await async_get_bulk_sync_status(
                hass, make_call({"config_entry_id": "e1", "job_id": res["job_id"]})
            )
            assert status["skipped"] >= 1

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
            await asyncio.sleep(0.1)
            from custom_components.bazarr_sync.services import (
                async_get_bulk_sync_status,
            )

            status = await async_get_bulk_sync_status(
                hass, make_call({"config_entry_id": "e1", "job_id": res["job_id"]})
            )
            assert status["skipped"] == 1

    async def test_language_filter(self, movie_with_subs):
        movie_with_subs[0]["subtitles"].append(
            {
                "path": "/subs/m1.pt.srt",
                "name": "Portuguese",
                "code2": "pt",
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
                {"config_entry_id": "e1", "scope": "movies", "language": "pt"}
            )
            res = await async_sync_all_subtitles(hass, call)
            assert res["status"] == "preparing"
            await asyncio.sleep(0.1)
            from custom_components.bazarr_sync.services import (
                async_get_bulk_sync_status,
            )

            status = await async_get_bulk_sync_status(
                hass, make_call({"config_entry_id": "e1", "job_id": res["job_id"]})
            )
            assert status["total"] == 1
            assert status["skipped"] == 3

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
            # Immediate response is preparing without counts/paths
            assert res["status"] == "preparing"
            assert "eligible_count" not in res

    async def test_mutation_exactly_once(self):
        movies = [
            {
                "radarrId": 1,
                "subtitles": [
                    {
                        "path": "/subs/a.srt",
                        "name": "English",
                        "code2": "en",
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

    async def test_missing_code2_skipped(self):
        movies = [
            {
                "radarrId": 1,
                "subtitles": [
                    {
                        "path": "/subs/a.srt",
                        "name": "English",
                        "code2": "",
                        "forced": False,
                        "hi": False,
                        "embedded_track_id": None,
                    },
                    {
                        "path": "/subs/b.srt",
                        "name": "English",
                        "code2": None,
                        "forced": False,
                        "hi": False,
                        "embedded_track_id": None,
                    },
                    {
                        "path": "/subs/c.srt",
                        "name": "English",
                        "code2": "en",
                        "forced": False,
                        "hi": False,
                        "embedded_track_id": None,
                    },
                ],
            }
        ]
        mock_client = AsyncMock()
        mock_client.async_get_all_movies = AsyncMock(return_value=movies)
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
            await asyncio.sleep(0.1)
            from custom_components.bazarr_sync.services import (
                async_get_bulk_sync_status,
            )

            status = await async_get_bulk_sync_status(
                hass, make_call({"config_entry_id": "e1", "job_id": res["job_id"]})
            )
            assert status["total"] == 1
            assert status["skipped"] == 2

    async def test_duplicate_active_bulk_prevented(self, movie_with_subs):
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
            await async_sync_all_subtitles(hass, call)
            # Second call should fail due to active job
            with pytest.raises(HomeAssistantError, match="already running"):
                await async_sync_all_subtitles(hass, call)

    async def test_bulk_status(self, movie_with_subs):
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
        from custom_components.bazarr_sync.services import async_get_bulk_sync_status

        with patch(
            "custom_components.bazarr_sync.services._get_coordinator",
            return_value=mock_client,
        ):
            call = make_call({"config_entry_id": "e1", "scope": "movies"})
            res = await async_sync_all_subtitles(hass, call)
            job_id = res["job_id"]
            status_call = make_call({"config_entry_id": "e1", "job_id": job_id})
            status = await async_get_bulk_sync_status(hass, status_call)
            assert status["job_id"] == job_id
            assert "total" in status

    async def test_shutdown_cancels(self):
        movies = [
            {
                "radarrId": 1,
                "subtitles": [
                    {
                        "path": "/subs/a.srt",
                        "name": "English",
                        "code2": "en",
                        "forced": False,
                        "hi": False,
                        "embedded_track_id": None,
                    },
                    {
                        "path": "/subs/b.srt",
                        "name": "English",
                        "code2": "en",
                        "forced": False,
                        "hi": False,
                        "embedded_track_id": None,
                    },
                ],
            }
        ]
        mock_client = AsyncMock()
        mock_client.async_get_all_movies = AsyncMock(return_value=movies)
        mock_client.async_get_all_episodes = AsyncMock(return_value=[])

        async def slow_sync(*args, **kwargs):
            await asyncio.sleep(0.05)

        mock_client.async_sync_subtitle = slow_sync
        hass = MagicMock()
        hass.data = {}
        hass.async_create_task = MagicMock(
            side_effect=lambda coro: asyncio.ensure_future(coro)
        )
        hass.is_stopping = True
        with patch(
            "custom_components.bazarr_sync.services._get_coordinator",
            return_value=mock_client,
        ):
            call = make_call({"config_entry_id": "e1", "scope": "movies"})
            res = await async_sync_all_subtitles(hass, call)
            await asyncio.sleep(0.2)
            from custom_components.bazarr_sync.services import (
                async_get_bulk_sync_status,
            )

            status = await async_get_bulk_sync_status(
                hass, make_call({"config_entry_id": "e1", "job_id": res["job_id"]})
            )
            assert status["status"] == "cancelled"
