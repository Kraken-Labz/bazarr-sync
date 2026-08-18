"""Tests for models."""

from __future__ import annotations

from custom_components.bazarr_sync.models import (
    InstalledSubtitle,
    MediaReference,
    SubtitleCandidate,
    SyncReference,
    SyncReferences,
)


class TestMediaReference:
    """Test MediaReference."""

    def test_create(self):
        """Test creating a MediaReference."""
        ref = MediaReference(media_type="movie", media_id=1, title="Test Movie")
        assert ref.media_type == "movie"
        assert ref.media_id == 1
        assert ref.title == "Test Movie"


class TestSubtitleCandidate:
    """Test SubtitleCandidate."""

    def test_from_bazarr(self):
        """Test creating from Bazarr API response."""
        data = {
            "provider": "opensubtitles",
            "subtitle": "sub123",
            "language": "en",
            "score": 95,
            "matches": ["match1"],
            "dont_matches": ["dont1"],
            "release_info": ["release1"],
            "uploader": "user1",
            "hearing_impaired": "True",
            "forced": "False",
            "original_format": "srt",
            "url": "http://example.com",
        }
        candidate = SubtitleCandidate.from_bazarr(data)
        assert candidate.provider == "opensubtitles"
        assert candidate.subtitle_id == "sub123"
        assert candidate.language == "en"
        assert candidate.score == 95
        assert candidate.matches == ["match1"]
        assert candidate.dont_matches == ["dont1"]
        assert candidate.release_info == ["release1"]
        assert candidate.uploader == "user1"
        assert candidate.hearing_impaired is True
        assert candidate.forced is False
        assert candidate.original_format == "srt"
        assert candidate.url == "http://example.com"

    def test_from_bazarr_false_strings(self):
        """Test boolean string parsing."""
        data = {
            "hearing_impaired": "False",
            "forced": "True",
        }
        candidate = SubtitleCandidate.from_bazarr(data)
        assert candidate.hearing_impaired is False
        assert candidate.forced is True

    def test_as_dict(self):
        """Test converting to dictionary."""
        candidate = SubtitleCandidate(
            provider="opensubtitles",
            subtitle_id="sub123",
            language="en",
            score=95,
        )
        d = candidate.as_dict()
        assert d["provider"] == "opensubtitles"
        assert d["subtitle_id"] == "sub123"
        assert d["language"] == "en"
        assert d["score"] == 95


class TestInstalledSubtitle:
    """Test InstalledSubtitle."""

    def test_from_bazarr(self):
        """Test creating from Bazarr API response."""
        data = {
            "path": "/subs/movie.en.srt",
            "name": "English",
            "code2": "en",
            "code3": "eng",
            "forced": True,
            "hi": False,
            "file_size": 1024,
            "embedded_track_id": 0,
        }
        sub = InstalledSubtitle.from_bazarr(data)
        assert sub.path == "/subs/movie.en.srt"
        assert sub.language == "English"
        assert sub.code2 == "en"
        assert sub.code3 == "eng"
        assert sub.forced is True
        assert sub.hearing_impaired is False
        assert sub.file_size == 1024
        assert sub.embedded_track_id == 0


class TestSyncReference:
    """Test SyncReference."""

    def test_from_audio_track(self):
        """Test creating from audio track."""
        data = {"stream": "a:0", "name": "English", "language": "en"}
        ref = SyncReference.from_audio_track(data)
        assert ref.kind == "audio"
        assert ref.identifier == "a:0"
        assert ref.label == "English"
        assert ref.language == "en"

    def test_from_embedded_subtitle(self):
        """Test creating from embedded subtitle."""
        data = {
            "stream": "s:0",
            "name": "English",
            "language": "en",
            "forced": True,
            "hearing_impaired": False,
        }
        ref = SyncReference.from_embedded_subtitle(data)
        assert ref.kind == "embedded_subtitle"
        assert ref.identifier == "s:0"
        assert ref.forced is True

    def test_from_external_subtitle(self):
        """Test creating from external subtitle."""
        data = {
            "path": "/subs/movie.en.srt",
            "name": "English",
            "language": "en",
            "forced": False,
            "hearing_impaired": True,
        }
        ref = SyncReference.from_external_subtitle(data)
        assert ref.kind == "external_subtitle"
        # identifier is now an opaque hash, not the path
        assert ref.identifier != "/subs/movie.en.srt"
        assert len(ref.identifier) == 16
        assert ref.hearing_impaired is True

    def test_external_subtitle_id_is_deterministic(self):
        """Test that external subtitle ID is deterministic."""
        data = {
            "path": "/subs/movie.en.srt",
            "name": "English",
            "language": "en",
        }
        ref1 = SyncReference.from_external_subtitle(data)
        ref2 = SyncReference.from_external_subtitle(data)
        # Same path should generate the same opaque ID
        assert ref1.identifier == ref2.identifier
        assert len(ref1.identifier) == 16


class TestSyncReferences:
    """Test SyncReferences."""

    def test_from_bazarr(self):
        """Test creating from Bazarr API response."""
        data = {
            "audio_tracks": [{"stream": "a:0", "name": "English", "language": "en"}],
            "embedded_subtitles_tracks": [
                {"stream": "s:0", "name": "English", "language": "en"}
            ],
            "external_subtitles_tracks": [
                {"path": "/sub.srt", "name": "English", "language": "en"}
            ],
        }
        refs = SyncReferences.from_bazarr(data)
        assert len(refs.audio_tracks) == 1
        assert len(refs.embedded_subtitles) == 1
        assert len(refs.external_subtitles) == 1
        assert refs.audio_tracks[0].kind == "audio"
        assert refs.embedded_subtitles[0].kind == "embedded_subtitle"
        assert refs.external_subtitles[0].kind == "external_subtitle"
