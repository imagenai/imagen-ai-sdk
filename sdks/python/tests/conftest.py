"""Shared pytest fixtures for the Imagen SDK test suite."""

from unittest.mock import patch

import pytest

from imagen_sdk import ImagenClient


@pytest.fixture
def api_key():
    """Test API key."""
    return "test-api-key"


@pytest.fixture
def client(api_key):
    """An ImagenClient instance for tests."""
    return ImagenClient(api_key)


@pytest.fixture
def mock_request_factory(client):
    """Factory that patches client._make_request to return a fixed value.

    `unittest.mock.patch` auto-detects the async method and substitutes an
    AsyncMock, so the patched coroutine is awaitable.
    """

    def _create_mock_request(return_value):
        return patch.object(client, "_make_request", return_value=return_value)

    return _create_mock_request
