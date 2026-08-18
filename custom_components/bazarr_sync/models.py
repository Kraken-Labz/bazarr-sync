"""Models for Bazarr integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MediaReference:
    """Reference to a movie or episode in Bazarr."""

    media_type: str  # "movie" or "episode"
    media_id: int
    series_id: int | None = None
    title: str = ""
    path: str = ""


@dataclass
class SubtitleCandidate:
    """Subtitle candidate from manual search."""

    provider: str
    subtitle_id: str
    language: str
    score: int
    matches: list[str] = field(default_factory=list)
    dont_matches: list[str] = field(default_factory=list)
    release_info: list[str] = field(default_factory=list)
    uploader: str = ""
    hearing_impaired: bool = False
    forced: bool = False
    original_format: str = ""
    url: str = ""

    @classmethod
    def from_bazarr(cls, data: dict[str, Any]) -> SubtitleCandidate:
        """Create from Bazarr API response."""
        return cls(
            provider=data.get("provider", ""),
            subtitle_id=data.get("subtitle", ""),
            language=data.get("language", ""),
            score=data.get("score", 0),
            matches=data.get("matches", []),
            dont_matches=data.get("dont_matches", []),
            release_info=data.get("release_info", []),
            uploader=data.get("uploader", ""),
            hearing_impaired=data.get("hearing_impaired", "False") == "True",
            forced=data.get("forced", "False") == "True",
            original_format=data.get("original_format", ""),
            url=data.get("url", ""),
        )

    def as_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "provider": self.provider,
            "subtitle_id": self.subtitle_id,
            "language": self.language,
            "score": self.score,
            "matches": self.matches,
            "dont_matches": self.dont_matches,
            "release_info": self.release_info,
            "uploader": self.uploader,
            "hearing_impaired": self.hearing_impaired,
            "forced": self.forced,
            "original_format": self.original_format,
            "url": self.url,
        }


@dataclass
class InstalledSubtitle:
    """Installed subtitle on disk."""

    path: str
    language: str
    hearing_impaired: bool = False
    forced: bool = False
    code2: str = ""
    code3: str = ""
    file_size: int = 0
    embedded_track_id: int | None = None

    @classmethod
    def from_bazarr(cls, data: dict[str, Any]) -> InstalledSubtitle:
        """Create from Bazarr API response (subtitles field)."""
        return cls(
            path=data.get("path", ""),
            language=data.get("name", ""),
            hearing_impaired=data.get("hi", False),
            forced=data.get("forced", False),
            code2=data.get("code2", ""),
            code3=data.get("code3", ""),
            file_size=data.get("file_size", 0),
            embedded_track_id=data.get("embedded_track_id"),
        )


@dataclass
class SyncReference:
    """Sync reference (audio track, embedded subtitle, or external subtitle)."""

    kind: str  # "audio" | "embedded_subtitle" | "external_subtitle"
    identifier: str
    label: str
    language: str
    forced: bool = False
    hearing_impaired: bool = False

    @classmethod
    def from_audio_track(cls, data: dict[str, Any]) -> SyncReference:
        """Create from audio track."""
        return cls(
            kind="audio",
            identifier=data.get("stream", ""),
            label=data.get("name", ""),
            language=data.get("language", ""),
        )

    @classmethod
    def from_embedded_subtitle(cls, data: dict[str, Any]) -> SyncReference:
        """Create from embedded subtitle track."""
        return cls(
            kind="embedded_subtitle",
            identifier=data.get("stream", ""),
            label=data.get("name", ""),
            language=data.get("language", ""),
            forced=data.get("forced", False),
            hearing_impaired=data.get("hearing_impaired", False),
        )

    @classmethod
    def from_external_subtitle(cls, data: dict[str, Any]) -> SyncReference:
        """Create from external subtitle."""
        return cls(
            kind="external_subtitle",
            identifier=data.get("path", ""),
            label=data.get("name", ""),
            language=data.get("language", ""),
            forced=data.get("forced", False),
            hearing_impaired=data.get("hearing_impaired", False),
        )


@dataclass
class SyncReferences:
    """All sync references for a media item."""

    audio_tracks: list[SyncReference] = field(default_factory=list)
    embedded_subtitles: list[SyncReference] = field(default_factory=list)
    external_subtitles: list[SyncReference] = field(default_factory=list)

    @classmethod
    def from_bazarr(cls, data: dict[str, Any]) -> SyncReferences:
        """Create from Bazarr API response."""
        return cls(
            audio_tracks=[
                SyncReference.from_audio_track(t) for t in data.get("audio_tracks", [])
            ],
            embedded_subtitles=[
                SyncReference.from_embedded_subtitle(t)
                for t in data.get("embedded_subtitles_tracks", [])
            ],
            external_subtitles=[
                SyncReference.from_external_subtitle(t)
                for t in data.get("external_subtitles_tracks", [])
            ],
        )
