"""Human-friendly media resolver for Bazarr Sync."""

from __future__ import annotations

import unicodedata
from typing import Any

from homeassistant.exceptions import HomeAssistantError

from .client import BazarrClient
from .models import ResolvedMedia


class MediaResolutionError(HomeAssistantError):
    """Error during media resolution."""


class AmbiguousMediaError(MediaResolutionError):
    """Multiple media items match the query."""

    def __init__(
        self, message: str, suggestions: list[dict[str, Any]] | None = None
    ) -> None:
        super().__init__(message)
        self.suggestions = suggestions or []


class MediaNotFoundError(MediaResolutionError):
    """No media found matching the query."""


def _normalize_string(value: str) -> str:
    """Normalize a string for comparison: trim, casefold, normalize unicode, collapse spaces."""
    if not value:
        return ""
    # Normalize unicode (NFKD decomposes accented chars)
    normalized = unicodedata.normalize("NFKD", value)
    # Remove combining characters (accents)
    normalized = "".join(c for c in normalized if not unicodedata.combining(c))
    # Casefold for case-insensitive comparison
    normalized = normalized.casefold()
    # Collapse whitespace
    normalized = " ".join(normalized.split())
    return normalized


def _matches_title(query: str, candidate: str, year: int | None = None) -> bool:
    """Check if a candidate title matches the query."""
    norm_query = _normalize_string(query)
    norm_candidate = _normalize_string(candidate)

    # Exact match after normalization
    if norm_query == norm_candidate:
        return True

    # If year provided, check if candidate contains year
    if year is not None and str(year) in candidate:
        # Check base title without year
        candidate_no_year = candidate.replace(str(year), "").strip(" ()-")
        if _normalize_string(query) == _normalize_string(candidate_no_year):
            return True

    return False


class MediaResolver:
    """Resolves human-readable media references to Bazarr IDs."""

    def __init__(self, client: BazarrClient) -> None:
        self._client = client

    async def resolve_movie(self, title: str, year: int | None = None) -> ResolvedMedia:
        """Resolve a movie by title and optional year.

        Raises:
            AmbiguousMediaError: Multiple movies match without year disambiguation.
            MediaNotFoundError: No matching movie found.
        """
        if not title or not title.strip():
            raise MediaResolutionError("Movie title is required")

        # Get all movies from Bazarr
        result = await self._client.async_get_movies(length=-1)
        movies = result.get("data", [])

        matches = []

        for movie in movies:
            movie_title = movie.get("title", "")
            movie_year = movie.get("year")

            if _matches_title(title, movie_title, year):
                # Check year if provided
                if year is not None and movie_year != year:
                    continue
                matches.append(movie)

        if not matches:
            raise MediaNotFoundError(
                f"No movie found matching '{title}'" + (f" ({year})" if year else "")
            )

        if len(matches) > 1:
            # Build suggestions for error message
            suggestions = [
                {
                    "title": m.get("title", ""),
                    "year": m.get("year"),
                    "radarrId": m.get("radarrId"),
                }
                for m in matches
            ]
            raise AmbiguousMediaError(
                f"Multiple movies match '{title}'. Please specify the year.",
                suggestions=suggestions,
            )

        movie = matches[0]
        return ResolvedMedia(
            media_type="movie",
            title=movie.get("title", ""),
            year=movie.get("year"),
            media_id=movie.get("radarrId", 0),
        )

    async def resolve_episode(
        self,
        series_title: str,
        season: int,
        episode: int,
        series_year: int | None = None,
    ) -> ResolvedMedia:
        """Resolve an episode by series title, season, and episode number.

        Raises:
            AmbiguousMediaError: Multiple series match without year disambiguation.
            MediaNotFoundError: No matching series or episode found.
        """
        if not series_title or not series_title.strip():
            raise MediaResolutionError("Series title is required")

        if season <= 0:
            raise MediaResolutionError("Season must be a positive integer")
        if episode <= 0:
            raise MediaResolutionError("Episode must be a positive integer")

        # Step 1: Find the series
        series_result = await self._client.async_get_series(length=-1)
        series_list = series_result.get("data", [])

        series_matches = []

        for series in series_list:
            series_name = series.get("title", "")
            series_year_data = series.get("year")

            if _matches_title(series_title, series_name, series_year):
                if (
                    series_year is not None
                    and series_year_data is not None
                    and series_year_data != series_year
                ):
                    continue
                series_matches.append(series)

        if not series_matches:
            raise MediaNotFoundError(f"No series found matching '{series_title}'")

        if len(series_matches) > 1:
            if series_year is None:
                suggestions = [
                    {
                        "title": s.get("title", ""),
                        "year": s.get("year"),
                        "sonarrSeriesId": s.get("sonarrSeriesId"),
                    }
                    for s in series_matches
                ]
                raise AmbiguousMediaError(
                    f"Multiple series match '{series_title}'. Please specify the year.",
                    suggestions=suggestions,
                )
            # Try to disambiguate with year
            year_matches = [s for s in series_matches if s.get("year") == series_year]
            if len(year_matches) == 1:
                series_matches = year_matches
            elif len(year_matches) > 1:
                suggestions = [
                    {
                        "title": s.get("title", ""),
                        "year": s.get("year"),
                        "sonarrSeriesId": s.get("sonarrSeriesId"),
                    }
                    for s in series_matches
                ]
                raise AmbiguousMediaError(
                    f"Multiple series match '{series_title}' ({series_year}).",
                    suggestions=suggestions,
                )
            else:
                suggestions = [
                    {
                        "title": s.get("title", ""),
                        "year": s.get("year"),
                        "sonarrSeriesId": s.get("sonarrSeriesId"),
                    }
                    for s in series_matches
                ]
                raise AmbiguousMediaError(
                    f"No series match '{series_title}' with year {series_year}.",
                    suggestions=suggestions,
                )

        series = series_matches[0]
        sonarr_series_id = series.get("sonarrSeriesId")

        # Step 2: Get episodes for this series
        episodes = await self._client.async_get_episodes(series_ids=[sonarr_series_id])

        # Find the exact season/episode
        episode_match = None
        for ep in episodes:
            if ep.get("seasonNumber") == season and ep.get("episodeNumber") == episode:
                episode_match = ep
                break

        if not episode_match:
            # Get available seasons/episodes for error message
            available = {}
            for ep in episodes:
                s = ep.get("seasonNumber")
                e = ep.get("episodeNumber")
                if s not in available:
                    available[s] = []
                available[s].append(e)

            raise MediaNotFoundError(
                f"Episode S{season:02d}E{episode:02d} not found for series '{series.get('title', '')}'. "
                f"Available: {available}"
            )

        return ResolvedMedia(
            media_type="episode",
            title=series.get("title", ""),
            year=series.get("year"),
            season=season,
            episode=episode,
            episode_title=episode_match.get("title"),
            media_id=episode_match.get("sonarrEpisodeId", 0),
            series_id=sonarr_series_id,
        )

    async def get_installed_subtitles_for_media(
        self, resolved: ResolvedMedia
    ) -> list[dict[str, Any]]:
        """Get installed subtitles for a resolved media item."""
        if resolved.media_type == "movie":
            result = await self._client.async_get_movies(radarr_ids=[resolved.media_id])
            data = result.get("data", [])
        else:
            if resolved.series_id is None:
                raise ValueError("series_id is required for episodes")
            data = await self._client.async_get_episodes(
                episode_ids=[resolved.media_id]
            )

        if not data:
            return []

        item = data[0]
        subtitles = item.get("subtitles", [])

        result = []
        for sub in subtitles:
            path = sub.get("path")
            subtitle_id = (
                self._generate_subtitle_id(resolved.media_type, resolved.media_id, path)
                if path
                else None
            )
            result.append(
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
        return result

    def _generate_subtitle_id(
        self, media_type: str, media_id: int, subtitle_path: str
    ) -> str:
        """Generate an opaque subtitle ID from media info and subtitle path."""
        import hashlib

        content = f"{media_type}:{media_id}:{subtitle_path}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
