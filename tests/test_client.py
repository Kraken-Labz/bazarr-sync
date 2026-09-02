"""Tests for BazarrClient."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from aiohttp import ClientResponseError

from custom_components.bazarr_sync.client import (
    BazarrAuthError,
    BazarrClient,
    BazarrError,
    BazarrNotFoundError,
    BazarrTimeoutError,
)
from custom_components.bazarr_sync.util import generate_external_reference_id
from tests.conftest import MockRequestContextManager, MockResponse, make_mock_request


@pytest.fixture
def client(hass):
    """Create a BazarrClient with mocked session."""
    with patch(
        "custom_components.bazarr_sync.client.async_get_clientsession"
    ) as mock_get_session:
        session = AsyncMock()
        mock_get_session.return_value = session
        client = BazarrClient(hass, "http://localhost:6767", "test-api-key")
        client._session = session
        yield client


class TestBazarrClient:
    """Test BazarrClient."""

    @pytest.fixture
    def hass(self):
        """Mock Home Assistant."""
        return MagicMock()

    async def test_init(self, hass):
        """Test client initialization."""
        with patch("custom_components.bazarr_sync.client.async_get_clientsession"):
            client = BazarrClient(hass, "http://localhost:6767", "test-key")
            assert client.url == "http://localhost:6767"
            assert client.api_key == "test-key"

    async def test_get_headers(self, hass):
        """Test headers include API key."""
        with patch("custom_components.bazarr_sync.client.async_get_clientsession"):
            client = BazarrClient(hass, "http://localhost:6767", "test-key")
            headers = client._get_headers()
            assert headers["X-API-KEY"] == "test-key"

    async def test_request_success(self, hass, client):
        """Test successful request."""
        mock_response = MockResponse(200, {"data": {"bazarr_version": "1.0.0"}})
        tracker = make_mock_request(mock_response)
        client._session.request = tracker

        result = await client._request("GET", "/api/test")
        assert result == {"data": {"bazarr_version": "1.0.0"}}
        assert tracker.call_count == 1

    async def test_request_204(self, hass, client):
        """Test 204 No Content response."""
        mock_response = MockResponse(204, text_data="")
        mock_response.content_length = 0
        tracker = make_mock_request(mock_response)
        client._session.request = tracker

        result = await client._request("POST", "/api/test")
        assert result is None

    async def test_request_401(self, hass, client):
        """Test 401 raises BazarrAuthError."""
        mock_response = MockResponse(401)
        tracker = make_mock_request(mock_response)
        client._session.request = tracker

        with pytest.raises(BazarrAuthError):
            await client._request("GET", "/api/test")

    async def test_request_404(self, hass, client):
        """Test 404 raises BazarrNotFoundError."""
        mock_response = MockResponse(404)
        tracker = make_mock_request(mock_response)
        client._session.request = tracker

        with pytest.raises(BazarrNotFoundError):
            await client._request("GET", "/api/test")

    async def test_request_timeout(self, hass, client):
        """Test timeout raises BazarrTimeoutError."""

        def mock_request(*args, **kwargs):
            raise TimeoutError()

        client._session.request = mock_request

        with pytest.raises(BazarrTimeoutError):
            await client._request("GET", "/api/test")

    async def test_request_client_error(self, hass, client):
        """Test client error raises BazarrError."""

        def mock_request(*args, **kwargs):
            raise ClientResponseError(
                request_info=MagicMock(),
                history=(),
                status=500,
                message="Connection failed",
            )

        client._session.request = mock_request

        with pytest.raises(BazarrError):
            await client._request("GET", "/api/test")

    async def test_get_status(self, hass, client):
        """Test get system status."""
        mock_response = MockResponse(200, {"data": {"bazarr_version": "1.2.3"}})
        tracker = make_mock_request(mock_response)
        client._session.request = tracker

        result = await client.async_get_status()
        assert result["bazarr_version"] == "1.2.3"

    async def test_get_badges(self, hass, client):
        """Test get badges."""
        mock_response = MockResponse(200, {"movies": 5, "episodes": 10})
        tracker = make_mock_request(mock_response)
        client._session.request = tracker

        result = await client.async_get_badges()
        assert result["movies"] == 5
        assert result["episodes"] == 10

    async def test_get_health(self, hass, client):
        """Test get health."""
        mock_response = MockResponse(
            200, {"data": [{"type": "warning", "message": "test"}]}
        )
        tracker = make_mock_request(mock_response)
        client._session.request = tracker

        result = await client.async_get_health()
        assert len(result) == 1
        assert result[0]["type"] == "warning"

    async def test_get_movies(self, hass, client):
        """Test get movies list."""
        mock_response = MockResponse(
            200, {"data": [{"radarrId": 1, "title": "Test"}], "total": 1}
        )
        tracker = make_mock_request(mock_response)
        client._session.request = tracker

        result = await client.async_get_movies()
        assert result["total"] == 1
        assert result["data"][0]["radarrId"] == 1

    async def test_get_movies_with_filters(self, hass, client):
        """Test get movies with filters."""
        mock_response = MockResponse(200, {"data": [], "total": 0})
        tracker = make_mock_request(mock_response)
        client._session.request = tracker

        await client.async_get_movies(start=10, length=20, radarr_ids=[1, 2])
        _, kwargs = tracker.call_args
        assert kwargs["params"]["start"] == 10
        assert kwargs["params"]["length"] == 20
        assert kwargs["params"]["radarrid[]"] == [1, 2]

    async def test_get_episodes(self, hass, client):
        """Test get episodes list."""
        mock_response = MockResponse(
            200, {"data": [{"sonarrEpisodeId": 1, "title": "Ep1"}]}
        )
        tracker = make_mock_request(mock_response)
        client._session.request = tracker

        result = await client.async_get_episodes(series_ids=[1])
        assert len(result) == 1
        assert result[0]["sonarrEpisodeId"] == 1

    async def test_get_episodes_requires_ids(self, hass, client):
        """Test get episodes requires series_id or episode_id."""
        with pytest.raises(
            ValueError, match="Either series_ids or episode_ids must be provided"
        ):
            await client.async_get_episodes()

    async def test_get_series(self, hass, client):
        """Test get series list."""
        mock_response = MockResponse(
            200, {"data": [{"sonarrSeriesId": 1, "title": "Series1"}], "total": 1}
        )
        tracker = make_mock_request(mock_response)
        client._session.request = tracker

        result = await client.async_get_series()
        assert result["total"] == 1
        assert result["data"][0]["sonarrSeriesId"] == 1

    async def test_search_movie_subtitles(self, hass, client):
        """Test search movie subtitles."""
        mock_response = MockResponse(
            200, {"data": [{"provider": "opensubtitles", "subtitle": "sub1"}]}
        )
        tracker = make_mock_request(mock_response)
        client._session.request = tracker

        result = await client.async_search_movie_subtitles(1)
        assert len(result) == 1
        assert result[0]["provider"] == "opensubtitles"

    async def test_search_episode_subtitles(self, hass, client):
        """Test search episode subtitles."""
        mock_response = MockResponse(
            200, {"data": [{"provider": "opensubtitles", "subtitle": "sub1"}]}
        )
        tracker = make_mock_request(mock_response)
        client._session.request = tracker

        result = await client.async_search_episode_subtitles(1)
        assert len(result) == 1

    async def test_download_movie_subtitle(self, hass, client):
        """Test download movie subtitle."""
        mock_response = MockResponse(204)
        mock_response.content_length = 0
        tracker = make_mock_request(mock_response)
        client._session.request = tracker

        await client.async_download_movie_subtitle(
            radarr_id=1,
            provider="opensubtitles",
            subtitle_id="sub1",
            hearing_impaired=True,
            forced=False,
            original_format=True,
        )

        args, kwargs = tracker.call_args
        assert args[0] == "POST"
        assert args[1] == "http://localhost:6767/api/providers/movies"
        data = kwargs["data"]
        assert data["radarrid"] == 1
        assert data["hi"] == "True"
        assert data["forced"] == "False"
        assert data["original_format"] == "True"

    async def test_download_episode_subtitle(self, hass, client):
        """Test download episode subtitle."""
        mock_response = MockResponse(204)
        mock_response.content_length = 0
        tracker = make_mock_request(mock_response)
        client._session.request = tracker

        await client.async_download_episode_subtitle(
            series_id=1,
            episode_id=2,
            provider="opensubtitles",
            subtitle_id="sub1",
            hearing_impaired=False,
            forced=True,
            original_format=False,
        )

        args, kwargs = tracker.call_args
        assert args[1] == "http://localhost:6767/api/providers/episodes"
        data = kwargs["data"]
        assert data["seriesid"] == 1
        assert data["episodeid"] == 2
        assert data["forced"] == "True"
        assert data["hi"] == "False"

    async def test_get_sync_references(self, hass, client):
        """Test get sync references."""
        mock_response = MockResponse(
            200,
            {
                "data": {
                    "audio_tracks": [
                        {"stream": "a:0", "name": "English", "language": "en"}
                    ],
                    "embedded_subtitles_tracks": [],
                    "external_subtitles_tracks": [],
                }
            },
        )
        tracker = make_mock_request(mock_response)
        client._session.request = tracker

        await client.async_get_sync_references(
            subtitles_path="/path/sub.srt",
            radarr_movie_id=1,
        )

        _, kwargs = tracker.call_args
        params = kwargs["params"]
        assert params["subtitlesPath"] == "/path/sub.srt"
        assert params["radarrMovieId"] == 1

    async def test_sync_reference_identifier_external_roundtrip(self, hass, client):
        """External opaque reference_id resolves to the real filesystem path.

        Roundtrip: /internal/example.en.srt -> opaque_hash -> resolver ->
        /internal/example.en.srt (the value sent to Bazarr).
        """
        real_path = "/internal/example.en.srt"
        opaque_id = generate_external_reference_id(real_path)

        client.async_get_movies = AsyncMock(
            return_value={"data": [{"subtitles": [{"path": real_path}]}]}
        )
        client.async_get_sync_references = AsyncMock(
            return_value={
                "audio_tracks": [],
                "embedded_subtitles_tracks": [],
                "external_subtitles_tracks": [{"path": real_path, "language": "en"}],
            }
        )

        resolved = await client.async_get_sync_reference_identifier(
            media_type="movie",
            media_id=1,
            reference_id=opaque_id,
        )

        assert resolved == real_path

    async def test_sync_reference_identifier_audio_passthrough(self, hass, client):
        """Audio reference resolves to its stream identifier."""
        client.async_get_movies = AsyncMock(
            return_value={"data": [{"subtitles": [{"path": "/path/sub.srt"}]}]}
        )
        client.async_get_sync_references = AsyncMock(
            return_value={
                "audio_tracks": [{"stream": "a:0", "language": "en"}],
                "embedded_subtitles_tracks": [],
                "external_subtitles_tracks": [],
            }
        )

        resolved = await client.async_get_sync_reference_identifier(
            media_type="movie",
            media_id=1,
            reference_id="a:0",
        )

        assert resolved == "a:0"

    async def test_sync_reference_identifier_embedded_passthrough(self, hass, client):
        """Embedded subtitle reference resolves to its stream identifier."""
        client.async_get_movies = AsyncMock(
            return_value={"data": [{"subtitles": [{"path": "/path/sub.srt"}]}]}
        )
        client.async_get_sync_references = AsyncMock(
            return_value={
                "audio_tracks": [],
                "embedded_subtitles_tracks": [{"stream": "s:0", "language": "en"}],
                "external_subtitles_tracks": [],
            }
        )

        resolved = await client.async_get_sync_reference_identifier(
            media_type="movie",
            media_id=1,
            reference_id="s:0",
        )

        assert resolved == "s:0"

    async def test_sync_reference_identifier_forged_reference_rejected(
        self, hass, client
    ):
        """Forged external reference_id is rejected."""
        real_path = "/internal/example.en.srt"
        forged_id = generate_external_reference_id("/internal/other.en.srt")

        client.async_get_movies = AsyncMock(
            return_value={"data": [{"subtitles": [{"path": real_path}]}]}
        )
        client.async_get_sync_references = AsyncMock(
            return_value={
                "audio_tracks": [],
                "embedded_subtitles_tracks": [],
                "external_subtitles_tracks": [{"path": real_path, "language": "en"}],
            }
        )

        resolved = await client.async_get_sync_reference_identifier(
            media_type="movie",
            media_id=1,
            reference_id=forged_id,
        )

        assert resolved is None

    async def test_sync_subtitle(self, hass, client):
        """Test sync subtitle."""
        mock_response = MockResponse(204)
        mock_response.content_length = 0
        tracker = make_mock_request(mock_response)
        client._session.request = tracker

        await client.async_sync_subtitle(
            action="sync",
            language="en",
            path="/path/sub.srt",
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

        args, kwargs = tracker.call_args
        assert args[0] == "PATCH"
        assert args[1] == "http://localhost:6767/api/subtitles"
        data = kwargs["data"]
        assert data["action"] == "sync"
        assert data["type"] == "movie"
        assert data["id"] == 1
        assert data["forced"] == "True"
        assert data["reference"] == "a:0"
        assert data["no_fix_framerate"] == "True"

    # Retry tests
    async def test_request_retry_on_500_get(self, hass):
        """Test retry on 500 error for GET request."""
        with patch(
            "custom_components.bazarr_sync.client.async_get_clientsession"
        ) as mock_get_session:
            session = AsyncMock()
            mock_get_session.return_value = session
            client = BazarrClient(
                hass,
                "http://localhost:6767",
                "test-key",
                max_retries=2,
                retry_base_delay=0.01,
            )
            client._session = session

            call_count = 0

            def make_response(attempt: int):
                if attempt <= 2:
                    raise ClientResponseError(
                        request_info=MagicMock(),
                        history=(),
                        status=500,
                        message="Internal Server Error",
                    )
                return MockResponse(200, {"data": "success"})

            def mock_request(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                return MockRequestContextManager(make_response(call_count))

            client._session.request = mock_request

            result = await client._request("GET", "/api/test")
            assert result == {"data": "success"}
            assert call_count == 3

    async def test_request_no_retry_on_500_post(self, hass):
        """Test no retry on 500 error for POST request (non-idempotent)."""
        with patch(
            "custom_components.bazarr_sync.client.async_get_clientsession"
        ) as mock_get_session:
            session = AsyncMock()
            mock_get_session.return_value = session
            client = BazarrClient(
                hass,
                "http://localhost:6767",
                "test-key",
                max_retries=2,
                retry_base_delay=0.01,
            )
            client._session = session

            call_count = 0

            def mock_request(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                raise ClientResponseError(
                    request_info=MagicMock(),
                    history=(),
                    status=500,
                    message="Internal Server Error",
                )

            client._session.request = mock_request

            with pytest.raises(BazarrError):
                await client._request("POST", "/api/test")
            assert call_count == 1

    async def test_request_no_retry_on_401(self, hass, client):
        """Test no retry on 401 error."""
        mock_response = MockResponse(401)
        tracker = make_mock_request(mock_response)
        client._session.request = tracker

        with pytest.raises(BazarrAuthError):
            await client._request("GET", "/api/test")
        assert tracker.call_count == 1

    async def test_request_no_retry_on_404(self, hass, client):
        """Test no retry on 404 error."""
        mock_response = MockResponse(404)
        tracker = make_mock_request(mock_response)
        client._session.request = tracker

        with pytest.raises(BazarrNotFoundError):
            await client._request("GET", "/api/test")
        assert tracker.call_count == 1

    async def test_request_retry_on_timeout_get(self, hass):
        """Test retry on timeout for GET request."""
        with patch(
            "custom_components.bazarr_sync.client.async_get_clientsession"
        ) as mock_get_session:
            session = AsyncMock()
            mock_get_session.return_value = session
            client = BazarrClient(
                hass,
                "http://localhost:6767",
                "test-key",
                max_retries=2,
                retry_base_delay=0.01,
            )
            client._session = session

            call_count = 0

            def mock_request(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count <= 1:
                    raise TimeoutError()
                return MockRequestContextManager(MockResponse(200, {"data": "success"}))

            client._session.request = mock_request

            result = await client._request("GET", "/api/test")
            assert result == {"data": "success"}
            assert call_count == 2

    async def test_request_retry_on_network_error_get(self, hass):
        """Test retry on network error for GET request."""
        with patch(
            "custom_components.bazarr_sync.client.async_get_clientsession"
        ) as mock_get_session:
            session = AsyncMock()
            mock_get_session.return_value = session
            client = BazarrClient(
                hass,
                "http://localhost:6767",
                "test-key",
                max_retries=2,
                retry_base_delay=0.01,
            )
            client._session = session

            call_count = 0

            def mock_request(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count <= 1:
                    raise aiohttp.ClientError("Connection failed")
                return MockRequestContextManager(MockResponse(200, {"data": "success"}))

            client._session.request = mock_request

            result = await client._request("GET", "/api/test")
            assert result == {"data": "success"}
            assert call_count == 2

    async def test_request_max_retries_exceeded(self, hass):
        """Test max retries exceeded raises error."""
        with patch(
            "custom_components.bazarr_sync.client.async_get_clientsession"
        ) as mock_get_session:
            session = AsyncMock()
            mock_get_session.return_value = session
            client = BazarrClient(
                hass,
                "http://localhost:6767",
                "test-key",
                max_retries=2,
                retry_base_delay=0.01,
            )
            client._session = session

            call_count = 0

            def mock_request(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                raise ClientResponseError(
                    request_info=MagicMock(),
                    history=(),
                    status=500,
                    message="Internal Server Error",
                )

            client._session.request = mock_request

            with pytest.raises(BazarrError, match="Request failed after 3 attempts"):
                await client._request("GET", "/api/test")
            assert call_count == 3

    async def test_request_503_retry(self, hass):
        """Test retry on 503 Service Unavailable."""
        with patch(
            "custom_components.bazarr_sync.client.async_get_clientsession"
        ) as mock_get_session:
            session = AsyncMock()
            mock_get_session.return_value = session
            client = BazarrClient(
                hass,
                "http://localhost:6767",
                "test-key",
                max_retries=1,
                retry_base_delay=0.01,
            )
            client._session = session

            call_count = 0

            def mock_request(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise ClientResponseError(
                        request_info=MagicMock(),
                        history=(),
                        status=503,
                        message="Service Unavailable",
                    )
                return MockRequestContextManager(MockResponse(200, {"data": "success"}))

            client._session.request = mock_request

            result = await client._request("GET", "/api/test")
            assert result == {"data": "success"}
            assert call_count == 2

    async def test_init_with_custom_retry_params(self, hass):
        """Test client initialization with custom retry parameters."""
        with patch("custom_components.bazarr_sync.client.async_get_clientsession"):
            client = BazarrClient(
                hass,
                "http://localhost:6767",
                "test-key",
                max_concurrent=10,
                max_retries=5,
                retry_base_delay=1.0,
            )
            assert client._semaphore._value == 10
            assert client._max_retries == 5
            assert client._retry_base_delay == 1.0

    async def test_external_reference_id_generation(self, hass):
        """Test that external reference ID generation is deterministic."""
        path = "/subs/movie.en.srt"
        _ = generate_external_reference_id(path)

        # Test that the ID is deterministic
        id1 = generate_external_reference_id(path)
        id2 = generate_external_reference_id(path)
        assert id1 == id2
        assert len(id1) == 16

        # Test that different paths generate different IDs
        path2 = "/subs/movie.pt.srt"
        id2 = generate_external_reference_id(path2)
        assert id2 != generate_external_reference_id(path)

        # Test that empty path returns empty string
        assert generate_external_reference_id("") == ""
