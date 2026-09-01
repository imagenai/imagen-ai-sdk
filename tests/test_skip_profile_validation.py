"""Tests for the skip_profile_validation flag on quick_edit."""

from unittest.mock import AsyncMock, patch

import pytest

from imagen_sdk import UploadSummary, quick_edit


def _mock_client():
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.create_project.return_value = "uuid-1"
    client.upload_images.return_value = UploadSummary(total=1, successful=1, failed=0, results=[])
    client.get_download_links.return_value = ["https://d1"]
    return client


@pytest.mark.asyncio
async def test_quick_edit_skip_profile_validation_bypasses_profile_fetch():
    """With skip_profile_validation=True, quick_edit never fetches profiles and still edits."""
    with (
        patch("imagen_sdk.imagen_sdk.ImagenClient") as client_class,
        patch("imagen_sdk.imagen_sdk.get_profile") as get_profile_mock,
    ):
        client = _mock_client()
        client_class.return_value = client

        result = await quick_edit(
            api_key="k",
            profile_key=999999,
            image_paths=["img1.jpg"],
            skip_profile_validation=True,
        )

        get_profile_mock.assert_not_called()
        client.start_editing.assert_called_once_with("uuid-1", 999999, None, edit_options=None)
        assert result.project_uuid == "uuid-1"
