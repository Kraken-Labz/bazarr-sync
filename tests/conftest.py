"""Test configuration and fixtures."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientResponseError

from custom_components.bazarr_sync.client import (
    BazarrClient,
)


@pytest.fixture
def mock_hass():
    """Mock Home Assistant."""
    hass = MagicMock()
    return hass


@pytest.fixture
def mock_session():
    """Mock aiohttp client session."""
    session = AsyncMock()
    return session


@pytest.fixture
def bazarr_client(mock_hass, mock_session):
    """Create a BazarrClient with mocked session."""
    with patch(
        "custom_components.bazarr_sync.client.async_get_clientsession"
    ) as mock_get_session:
        mock_get_session.return_value = mock_session
        client = BazarrClient(mock_hass, "http://localhost:6767", "test-api-key")
        client._session = mock_session
        yield client


class MockResponse:
    """Mock aiohttp response."""

    def __init__(
        self, status: int = 200, json_data: dict | None = None, text_data: str = ""
    ):
        self.status = status
        self._json_data = json_data or {}
        self._text_data = text_data
        self.headers = {"Content-Type": "application/json"}
        self.content_length = len(text_data) if text_data else 2

    def raise_for_status(self):
        if self.status >= 400:
            raise ClientResponseError(
                request_info=MagicMock(),
                history=(),
                status=self.status,
                message=f"HTTP {self.status}",
            )

    async def json(self):
        return self._json_data

    async def text(self):
        return self._text_data

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class MockRequestContextManager:
    """Mock async context manager for session.request."""

    def __init__(self, response: MockResponse):
        self.response = response

    async def __aenter__(self):
        return self.response

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class MockRequestTracker:
    """Track calls to mock request."""

    def __init__(self, response: MockResponse):
        self.response = response
        self.call_args = None
        self.call_count = 0

    def __call__(self, *args, **kwargs):
        self.call_args = (args, kwargs)
        self.call_count += 1
        return MockRequestContextManager(self.response)


def make_mock_request(response: MockResponse) -> MockRequestTracker:
    """Create a mock request that returns an async context manager and tracks calls."""
    return MockRequestTracker(response)


# Re-export for convenience
__all__ = [
    "MockResponse",
    "bazarr_client",
    "make_mock_request",
    "mock_hass",
    "mock_session",
    "patch",
    "pytest",
]
