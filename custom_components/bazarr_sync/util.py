"""Utility helpers for Bazarr Sync."""

from __future__ import annotations

import hashlib


def generate_external_reference_id(path: str) -> str:
    """Generate an opaque external reference ID from a filesystem path."""
    if not path:
        return ""
    return hashlib.sha256(path.encode()).hexdigest()[:16]
