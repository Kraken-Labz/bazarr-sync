"""Tests for MediaResolver - human-friendly media resolution."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.bazarr_sync.media_resolver import (
    MediaNotFoundError,
    MediaResolutionError,
    MediaResolver,
    _normalize_string,
)
from custom_components.bazarr_sync.models import ResolvedMedia


class TestNormalizeString:
    """Tests for _normalize_string function."""

    def test_empty_string(self):
        assert _normalize_string("") == ""

    def test_whitespace_only(self):
        assert _normalize_string("   ") == ""

    def test_case_insensitive(self):
        assert _normalize_string("Interstellar") == "interstellar"
        assert _normalize_string("INTERSTELLAR") == "interstellar"
        assert _normalize_string("InTeRsTeLlAr") == "interstellar"

    def test_whitespace_collapse(self):
        assert _normalize_string("  The   Matrix  ") == "the matrix"
        assert _normalize_string("\tInterstellar\n") == "interstellar"

    def test_accent_normalization(self):
        assert _normalize_string("Café") == "cafe"
        assert _normalize_string("São Paulo") == "sao paulo"
        assert _normalize_string("Piñata") == "pinata"

    def test_punctuation_preserved(self):
        assert _normalize_string("The Matrix!") == "the matrix!"
        assert _normalize_string("Dune: Part One") == "dune: part one"


class TestMediaResolverMovies:
    """Tests for movie resolution."""

    @pytest.fixture
    def mock_client(self):
        """Create a mocked BazarrClient."""
        client = MagicMock()
        return client

    @pytest.fixture
    def resolver(self, mock_client):
        return MediaResolver(mock_client)

    @pytest.fixture
    def movie_data(self):
        """Sample movie data from Bazarr."""
        return [
            {"radarrId": 244, "title": "Interstellar", "year": 2014},
            {"radarrId": 245, "title": "The Matrix", "year": 1999},
            {"radarrId": 246, "title": "Dune", "year": 1984},
            {"radarrId": 247, "title": "Dune", "year": 2021},
        ]

    @pytest.mark.asyncio
    async def test_exact_title_match(self, resolver, mock_client, movie_data):
        """Test exact title match."""
        mock_client.async_get_movies = AsyncMock(return_value={"data": movie_data})

        result = await resolver.resolve_movie("Interstellar", year=None)

        assert isinstance(result, ResolvedMedia)
        assert result.media_type == "movie"
        assert result.title == "Interstellar"
        assert result.year == 2014
        assert result.media_id == 244

    @pytest.mark.asyncio
    async def test_case_insensitive_match(self, resolver, mock_client, movie_data):
        """Test case-insensitive title matching."""
        mock_client.async_get_movies = AsyncMock(return_value={"data": movie_data})

        result = await resolver.resolve_movie("interstellar", year=None)

        assert result.title == "Interstellar"
        assert result.media_id == 244

    @pytest.mark.asyncio
    async def test_whitespace_normalization(self, resolver, mock_client, movie_data):
        """Test surrounding and repeated whitespace handling."""
        mock_client.async_get_movies = AsyncMock(return_value={"data": movie_data})

        result = await resolver.resolve_movie("  The   Matrix  ", year=None)

        assert result.title == "The Matrix"
        assert result.media_id == 245

    @pytest.mark.asyncio
    async def test_accent_normalization(self, resolver, mock_client):
        """Test accent normalization."""
        movie_data = [{"radarrId": 1, "title": "São Paulo", "year": 2002}]
        mock_client.async_get_movies = AsyncMock(return_value={"data": movie_data})

        result = await resolver.resolve_movie("Sao Paulo", year=None)

        assert result.title == "São Paulo"
        assert result.media_id == 1

    @pytest.mark.asyncio
    async def test_title_with_year(self, resolver, mock_client, movie_data):
        """Test title + year exact match."""
        mock_client.async_get_movies = AsyncMock(return_value={"data": movie_data})

        result = await resolver.resolve_movie("Dune", year=2021)

        assert result.title == "Dune"
        assert result.year == 2021
        assert result.media_id == 247

    @pytest.mark.asyncio
    async def test_same_title_different_years_ambiguous(
        self, resolver, mock_client, movie_data
    ):
        """Test same title with different years -> ambiguous without year."""
        mock_client.async_get_movies = AsyncMock(return_value={"data": movie_data})

        with pytest.raises(Exception) as exc_info:
            await resolver.resolve_movie("Dune", year=None)

        assert exc_info.type.__name__ == "AmbiguousMediaError"
        assert "Multiple movies match" in str(exc_info.value)
        # Check suggestions include both years
        suggestions = exc_info.value.suggestions
        years = {s["year"] for s in suggestions}
        assert 1984 in years
        assert 2021 in years

    @pytest.mark.asyncio
    async def test_same_title_with_year_resolves(
        self, resolver, mock_client, movie_data
    ):
        """Test same title + year resolves correctly."""
        mock_client.async_get_movies = AsyncMock(return_value={"data": movie_data})

        result = await resolver.resolve_movie("Dune", year=1984)

        assert result.year == 1984
        assert result.media_id == 246

    @pytest.mark.asyncio
    async def test_wrong_year_not_found(self, resolver, mock_client, movie_data):
        """Test wrong year returns not found."""
        mock_client.async_get_movies = AsyncMock(return_value={"data": movie_data})

        with pytest.raises(Exception) as exc_info:
            await resolver.resolve_movie("Dune", year=2000)

        assert exc_info.type.__name__ == "MediaNotFoundError"

    @pytest.mark.asyncio
    async def test_empty_title_raises(self, resolver):
        """Test empty title raises error."""
        with pytest.raises(MediaResolutionError):
            await resolver.resolve_movie("", year=None)

    @pytest.mark.asyncio
    async def test_no_match(self, resolver, mock_client, movie_data):
        """Test no matching movie."""
        mock_client.async_get_movies = AsyncMock(return_value={"data": movie_data})

        with pytest.raises(MediaNotFoundError):
            await resolver.resolve_movie("NonExistentMovie", year=None)


class TestMediaResolverEpisodes:
    """Tests for episode resolution."""

    @pytest.fixture
    def mock_client(self):
        client = MagicMock()
        return client

    @pytest.fixture
    def resolver(self, mock_client):
        return MediaResolver(mock_client)

    @pytest.fixture
    def series_data(self):
        return [
            {"sonarrSeriesId": 100, "title": "Doctor Who", "year": 2005},
            {"sonarrSeriesId": 101, "title": "The Office", "year": 2005},
            {"sonarrSeriesId": 102, "title": "The Office", "year": 2001},
        ]

    @pytest.fixture
    def episodes_data(self):
        """Episodes for Doctor Who (seriesId 100)."""
        return [
            {
                "sonarrEpisodeId": 1000,
                "title": "The Pilot",
                "seasonNumber": 1,
                "episodeNumber": 1,
            },
            {
                "sonarrEpisodeId": 1001,
                "title": "The Doctor's Daughter",
                "seasonNumber": 4,
                "episodeNumber": 6,
            },
            {
                "sonarrEpisodeId": 1002,
                "title": "The End of Time",
                "seasonNumber": 4,
                "episodeNumber": 15,
            },
        ]

    @pytest.mark.asyncio
    async def test_exact_series_title(
        self, resolver, mock_client, series_data, episodes_data
    ):
        """Test exact series title match."""
        mock_client.async_get_series = AsyncMock(return_value={"data": series_data})
        mock_client.async_get_episodes = AsyncMock(return_value=episodes_data)

        result = await resolver.resolve_episode("Doctor Who", 1, 1, series_year=None)

        assert result.media_type == "episode"
        assert result.title == "Doctor Who"
        assert result.series_id == 100
        assert result.season == 1
        assert result.episode == 1
        assert result.episode_title == "The Pilot"
        assert result.media_id == 1000

    @pytest.mark.asyncio
    async def test_case_accent_whitespace_normalization(
        self, resolver, mock_client, series_data, episodes_data
    ):
        """Test normalization for series title."""
        mock_client.async_get_series = AsyncMock(return_value={"data": series_data})
        mock_client.async_get_episodes = AsyncMock(return_value=episodes_data)

        result = await resolver.resolve_episode(
            "  doctor who  ", 1, 1, series_year=None
        )

        assert result.title == "Doctor Who"
        assert result.series_id == 100

    @pytest.mark.asyncio
    async def test_duplicate_series_ambiguous_without_year(
        self, resolver, mock_client, series_data, episodes_data
    ):
        """Test duplicate series names -> ambiguous without year."""
        mock_client.async_get_series = AsyncMock(return_value={"data": series_data})
        mock_client.async_get_episodes = AsyncMock(return_value=episodes_data)

        with pytest.raises(Exception) as exc_info:
            await resolver.resolve_episode("The Office", 1, 1, series_year=None)

        assert exc_info.type.__name__ == "AmbiguousMediaError"
        suggestions = exc_info.value.suggestions
        years = {s["year"] for s in suggestions}
        assert 2005 in years
        assert 2001 in years

    @pytest.mark.asyncio
    async def test_duplicate_series_year_resolves(
        self, resolver, mock_client, series_data, episodes_data
    ):
        """Test duplicate series + year resolves correctly."""
        mock_client.async_get_series = AsyncMock(return_value={"data": series_data})
        mock_client.async_get_episodes = AsyncMock(return_value=episodes_data)

        result = await resolver.resolve_episode("The Office", 1, 1, series_year=2005)

        assert result.title == "The Office"
        assert result.year == 2005
        assert result.series_id == 101

    @pytest.mark.asyncio
    async def test_exact_season_episode(
        self, resolver, mock_client, series_data, episodes_data
    ):
        """Test exact season/episode resolution."""
        mock_client.async_get_series = AsyncMock(return_value={"data": series_data})
        mock_client.async_get_episodes = AsyncMock(return_value=episodes_data)

        result = await resolver.resolve_episode("Doctor Who", 4, 6, series_year=None)

        assert result.season == 4
        assert result.episode == 6
        assert result.episode_title == "The Doctor's Daughter"
        assert result.media_id == 1001

    @pytest.mark.asyncio
    async def test_season_not_found(
        self, resolver, mock_client, series_data, episodes_data
    ):
        """Test season not found."""
        mock_client.async_get_series = AsyncMock(return_value={"data": series_data})
        mock_client.async_get_episodes = AsyncMock(return_value=episodes_data)

        with pytest.raises(MediaNotFoundError) as exc_info:
            await resolver.resolve_episode("Doctor Who", 99, 1, series_year=None)

        assert "Season" in str(exc_info.value) or "Episode" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_episode_not_found(
        self, resolver, mock_client, series_data, episodes_data
    ):
        """Test episode not found in existing season."""
        mock_client.async_get_series = AsyncMock(return_value={"data": series_data})
        mock_client.async_get_episodes = AsyncMock(return_value=episodes_data)

        with pytest.raises(MediaNotFoundError) as exc_info:
            await resolver.resolve_episode("Doctor Who", 1, 99, series_year=None)

        assert "Episode" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_empty_series_title(self, resolver):
        """Test empty series title raises error."""
        with pytest.raises(Exception) as exc_info:
            await resolver.resolve_episode("", 1, 1, series_year=None)

        assert exc_info.type.__name__ == "MediaResolutionError"

    @pytest.mark.asyncio
    async def test_invalid_season(self, resolver):
        """Test invalid season raises error."""
        with pytest.raises(MediaResolutionError):
            await resolver.resolve_episode("Test", 0, 1, series_year=None)

    @pytest.mark.asyncio
    async def test_invalid_episode(self, resolver):
        """Test invalid episode raises error."""
        with pytest.raises(MediaResolutionError):
            await resolver.resolve_episode("Test", 1, -1, series_year=None)


class TestMediaResolverIntegration:
    """Integration-style tests for MediaResolver."""

    @pytest.fixture
    def mock_client(self):
        client = MagicMock()
        return client

    @pytest.fixture
    def resolver(self, mock_client):
        return MediaResolver(mock_client)

    @pytest.mark.asyncio
    async def test_get_installed_subtitles_for_media(self, resolver, mock_client):
        """Test getting installed subtitles for resolved media."""
        # Mock the client to return movie data with subtitles
        mock_client.async_get_movies = AsyncMock(
            return_value={
                "data": [
                    {
                        "radarrId": 244,
                        "title": "Interstellar",
                        "year": 2014,
                        "subtitles": [
                            {
                                "path": "/subs/interstellar.en.srt",
                                "name": "English",
                                "hi": False,
                                "forced": False,
                                "code2": "en",
                                "code3": "eng",
                                "file_size": 12345,
                                "embedded_track_id": None,
                            },
                            {
                                "path": "/subs/interstellar.pt.srt",
                                "name": "Portuguese",
                                "hi": False,
                                "forced": False,
                                "code2": "pt",
                                "code3": "por",
                                "file_size": 11000,
                                "embedded_track_id": None,
                            },
                        ],
                    }
                ]
            }
        )

        resolved = ResolvedMedia(
            media_type="movie",
            title="Interstellar",
            year=2014,
            media_id=244,
        )

        subtitles = await resolver.get_installed_subtitles_for_media(resolved)

        assert len(subtitles) == 2
        assert subtitles[0]["language"] == "English"
        assert subtitles[0]["subtitle_id"] is not None
        assert "subtitle_id" in subtitles[0]

    @pytest.mark.asyncio
    async def test_get_installed_subtitles_episodes(self, resolver, mock_client):
        """Test getting installed subtitles for episodes."""
        mock_client.async_get_episodes = AsyncMock(
            return_value=[
                {
                    "sonarrEpisodeId": 1000,
                    "title": "The Pilot",
                    "seasonNumber": 1,
                    "episodeNumber": 1,
                    "subtitles": [
                        {
                            "path": "/subs/dw_s01e01.en.srt",
                            "name": "English",
                            "hi": False,
                            "forced": False,
                            "code2": "en",
                            "code3": "eng",
                            "file_size": 10000,
                            "embedded_track_id": None,
                        },
                    ],
                }
            ]
        )

        resolved = ResolvedMedia(
            media_type="episode",
            title="Doctor Who",
            year=2005,
            season=1,
            episode=1,
            media_id=1000,
            series_id=100,
        )

        subtitles = await resolver.get_installed_subtitles_for_media(resolved)

        assert len(subtitles) == 1
        assert subtitles[0]["language"] == "English"
