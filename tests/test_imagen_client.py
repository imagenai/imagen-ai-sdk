"""
Unit tests for the ImagenClient class

Run with: pytest test_imagen_client.py -v
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import httpx
import pytest
from pydantic import ValidationError

from imagen_sdk import (
    AuthenticationError,
    DownloadError,
    EditOptions,
    ImagenClient,
    ImagenError,
    PhotographyType,
    ProjectError,
    StatusDetails,
    UploadError,
)


class MockHelpers:
    """Helper class for creating common mock objects."""

    @staticmethod
    def create_http_response(status_code: int, json_data: dict = None, text: str = ""):
        """Create a mock HTTP response."""
        mock_response = Mock()
        mock_response.status_code = status_code
        mock_response.text = text

        if json_data is not None:
            mock_response.json.return_value = json_data
        else:
            mock_response.json.side_effect = Exception("Not JSON")

        return mock_response

    @staticmethod
    def create_async_file_mock(content: bytes):
        """Create a mock async file object."""
        mock_file = MagicMock()
        mock_file.__aenter__ = AsyncMock(return_value=mock_file)
        mock_file.__aexit__ = AsyncMock(return_value=None)
        mock_file.read = AsyncMock(side_effect=[content, b""])  # First call returns content, second empty
        return mock_file

    @staticmethod
    def create_async_http_client_mock(response_mock: Mock = None):
        """Create a mock async HTTP client."""
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        if response_mock:
            mock_client.put = AsyncMock(return_value=response_mock)
            mock_client.request = AsyncMock(return_value=response_mock)

        return mock_client

    @staticmethod
    def create_path_mock(name: str, exists: bool = True):
        """Create a mock Path object."""
        mock_path = Mock(spec=Path)
        mock_path.exists.return_value = exists
        mock_path.name = name
        return mock_path


@pytest.fixture
def mock_helpers():
    """Fixture providing MockHelpers instance."""
    return MockHelpers()


@pytest.fixture
def api_key():
    """Fixture providing test API key."""
    return "test-api-key"


@pytest.fixture
def client(api_key):
    """Fixture providing ImagenClient instance."""
    return ImagenClient(api_key)


@pytest.fixture
def mock_request_factory(client):
    """Factory fixture for creating mock _make_request patches."""

    def _create_mock_request(return_value: dict):
        return patch.object(client, "_make_request", return_value=return_value)

    return _create_mock_request


class TestImagenClientInit:
    """Test ImagenClient initialization and basic properties."""

    def test_default_initialization(self, api_key):
        client = ImagenClient(api_key)
        assert client.api_key == api_key
        assert client.base_url == "https://api-beta.imagen-ai.com/v1"
        assert client._session is None

    def test_custom_base_url(self, api_key):
        client = ImagenClient(api_key, "https://custom.api.com/v2/")
        assert client.base_url == "https://custom.api.com/v2"

    def test_base_url_trailing_slash_removal(self, api_key):
        client = ImagenClient(api_key, "https://api.com/v1/")
        assert client.base_url == "https://api.com/v1"

    def test_empty_api_key_raises_error(self):
        with pytest.raises(ValueError, match="API key cannot be empty"):
            ImagenClient("")

    def test_none_api_key_raises_error(self):
        with pytest.raises(ValueError, match="API key cannot be empty"):
            ImagenClient(None)

    def test_get_session_creation(self, client):
        session = client._get_session()

        assert isinstance(session, httpx.AsyncClient)
        assert session.headers["x-api-key"] == "test-api-key"
        assert "Imagen-Python-SDK" in session.headers["User-Agent"]

        # Should return the same session instance
        session2 = client._get_session()
        assert session is session2


class TestImagenClientAsync:
    """Test async methods of ImagenClient."""

    @pytest.mark.asyncio
    async def test_close(self, client):
        session_mock = AsyncMock()
        client._session = session_mock

        await client.close()

        session_mock.aclose.assert_called_once()
        assert client._session is None

    @pytest.mark.asyncio
    async def test_context_manager(self, api_key):
        async with ImagenClient(api_key) as client:
            assert isinstance(client, ImagenClient)
        # Context manager should close automatically


class TestImagenClientRequests:
    """Test HTTP request handling in ImagenClient."""

    @pytest.mark.asyncio
    async def test_make_request_success_200(self, client, mock_helpers):
        json_data = {"data": "test"}
        mock_response = mock_helpers.create_http_response(200, json_data)

        with patch.object(client, "_get_session") as mock_session:
            mock_session.return_value.request = AsyncMock(return_value=mock_response)

            result = await client._make_request("GET", "/test")

            assert result == json_data
            mock_session.return_value.request.assert_called_once_with("GET", "https://api-beta.imagen-ai.com/v1/test")

    @pytest.mark.asyncio
    async def test_make_request_success_204(self, client, mock_helpers):
        mock_response = mock_helpers.create_http_response(204)

        with patch.object(client, "_get_session") as mock_session:
            mock_session.return_value.request = AsyncMock(return_value=mock_response)

            result = await client._make_request("POST", "/test")

            assert result == {}

    @pytest.mark.asyncio
    async def test_make_request_with_leading_slash(self, client, mock_helpers):
        mock_response = mock_helpers.create_http_response(200, {})

        with patch.object(client, "_get_session") as mock_session:
            mock_session.return_value.request = AsyncMock(return_value=mock_response)

            await client._make_request("GET", "///test///")

            # Should normalize the URL
            expected_url = "https://api-beta.imagen-ai.com/v1/test///"
            mock_session.return_value.request.assert_called_once_with("GET", expected_url)

    @pytest.mark.asyncio
    async def test_make_request_401_authentication_error(self, client, mock_helpers):
        mock_response = mock_helpers.create_http_response(401)

        with patch.object(client, "_get_session") as mock_session:
            mock_session.return_value.request = AsyncMock(return_value=mock_response)

            with pytest.raises(AuthenticationError, match="Invalid API key"):
                await client._make_request("GET", "/test")

    @pytest.mark.asyncio
    async def test_make_request_400_with_json_error(self, client, mock_helpers):
        json_data = {"detail": "Bad request details"}
        mock_response = mock_helpers.create_http_response(400, json_data, "Bad request")

        with patch.object(client, "_get_session") as mock_session:
            mock_session.return_value.request = AsyncMock(return_value=mock_response)

            with pytest.raises(ImagenError, match="API Error \\(400\\): Bad request details"):
                await client._make_request("GET", "/test")

    @pytest.mark.asyncio
    async def test_make_request_500_no_json(self, client, mock_helpers):
        mock_response = mock_helpers.create_http_response(500, None, "Internal server error")

        with patch.object(client, "_get_session") as mock_session:
            mock_session.return_value.request = AsyncMock(return_value=mock_response)

            with pytest.raises(ImagenError, match="API Error \\(500\\): Internal server error"):
                await client._make_request("GET", "/test")

    @pytest.mark.asyncio
    async def test_make_request_network_error(self, client):
        with patch.object(client, "_get_session") as mock_session:
            mock_session.return_value.request = AsyncMock(side_effect=httpx.RequestError("Network timeout"))

            with pytest.raises(ImagenError, match="Request failed: Network timeout"):
                await client._make_request("GET", "/test")


class TestImagenClientProjects:
    """Test project-related methods."""

    @pytest.mark.asyncio
    async def test_create_project_with_name(self, client, mock_request_factory):
        response_data = {"data": {"project_uuid": "test-uuid-123"}}

        with mock_request_factory(response_data):
            project_uuid = await client.create_project("Test Project")

            assert project_uuid == "test-uuid-123"
            client._make_request.assert_called_once_with("POST", "/projects/", json={"name": "Test Project"})

    @pytest.mark.asyncio
    async def test_create_project_without_name(self, client, mock_request_factory):
        response_data = {"data": {"project_uuid": "test-uuid-456"}}

        with mock_request_factory(response_data):
            project_uuid = await client.create_project()

            assert project_uuid == "test-uuid-456"
            client._make_request.assert_called_once_with("POST", "/projects/", json={})

    @pytest.mark.asyncio
    async def test_create_project_invalid_response(self, client, mock_request_factory):
        invalid_response = {"invalid": "structure"}

        with mock_request_factory(invalid_response):
            with pytest.raises(ProjectError, match="Could not parse project creation response"):
                await client.create_project()


class TestImagenClientProfiles:
    """Test profile-related methods."""

    @pytest.mark.asyncio
    async def test_get_profiles_success(self, client, mock_request_factory):
        response_data = {
            "data": {
                "profiles": [
                    {
                        "image_type": "portrait",
                        "profile_key": 123,
                        "profile_name": "Portrait Pro",
                        "profile_type": "premium",
                    },
                    {
                        "image_type": "wedding",
                        "profile_key": 456,
                        "profile_name": "Wedding Classic",
                        "profile_type": "standard",
                    },
                ]
            }
        }

        with mock_request_factory(response_data):
            profiles = await client.get_profiles()

            assert len(profiles) == 2
            assert profiles[0].profile_name == "Portrait Pro"
            assert profiles[0].profile_key == 123
            assert profiles[1].profile_name == "Wedding Classic"
            assert profiles[1].profile_key == 456

            client._make_request.assert_called_once_with("GET", "/profiles")

    @pytest.mark.asyncio
    async def test_get_profiles_empty_list(self, client, mock_request_factory):
        response_data = {"data": {"profiles": []}}

        with mock_request_factory(response_data):
            profiles = await client.get_profiles()
            assert len(profiles) == 0

    @pytest.mark.asyncio
    async def test_get_profiles_invalid_response(self, client, mock_request_factory):
        invalid_response = {"wrong": "format"}

        with mock_request_factory(invalid_response):
            with pytest.raises(ImagenError, match="Failed to parse profiles from API response"):
                await client.get_profiles()


class TestImagenClientDownloadFiles:
    """Test the download_files method comprehensively."""

    @pytest.mark.asyncio
    async def test_download_files_success(self, client, mock_helpers):
        """Test successful file downloads."""
        download_links = [
            "https://example.com/file1.jpg",
            "https://example.com/file2.jpg",
        ]

        # Let's create a simpler approach - mock the internal operations
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.content = b"fake image data"

        mock_file = AsyncMock()
        mock_file.__aenter__ = AsyncMock(return_value=mock_file)
        mock_file.__aexit__ = AsyncMock(return_value=None)
        mock_file.write = AsyncMock()

        with patch("httpx.AsyncClient") as mock_http_client:
            with patch("aiofiles.open", return_value=mock_file):
                with patch("pathlib.Path.mkdir"):
                    # Create a properly mocked HTTP client
                    mock_client_instance = AsyncMock()
                    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
                    mock_client_instance.__aexit__ = AsyncMock(return_value=None)
                    mock_client_instance.get = AsyncMock(return_value=mock_response)
                    mock_http_client.return_value = mock_client_instance

                    result = await client.download_files(download_links, "test_downloads")

                    # Verify results
                    assert len(result) == 2
                    assert all("test_downloads" in path for path in result)
                    assert any("file1.jpg" in path for path in result)
                    assert any("file2.jpg" in path for path in result)

    @pytest.mark.asyncio
    async def test_download_files_with_progress_callback(self, client):
        """Test download_files with progress callback."""
        download_links = ["https://example.com/file1.jpg"]
        progress_calls = []

        def progress_callback(current, total, message):
            progress_calls.append((current, total, message))

        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.content = b"fake image data"

        mock_file = AsyncMock()
        mock_file.__aenter__ = AsyncMock(return_value=mock_file)
        mock_file.__aexit__ = AsyncMock(return_value=None)
        mock_file.write = AsyncMock()

        with patch("httpx.AsyncClient") as mock_http_client:
            with patch("aiofiles.open", return_value=mock_file):
                with patch("pathlib.Path.mkdir"):
                    mock_client_instance = AsyncMock()
                    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
                    mock_client_instance.__aexit__ = AsyncMock(return_value=None)
                    mock_client_instance.get = AsyncMock(return_value=mock_response)
                    mock_http_client.return_value = mock_client_instance

                    result = await client.download_files(download_links, progress_callback=progress_callback)

                    # Verify we got a result
                    assert len(result) == 1

                    # Verify progress callback was called (at least once for start)
                    assert len(progress_calls) >= 1

    @pytest.mark.asyncio
    async def test_download_files_empty_links_error(self, client):
        """Test download_files with empty links list."""
        with pytest.raises(DownloadError, match="No download links provided"):
            await client.download_files([])

    @pytest.mark.asyncio
    async def test_download_files_max_concurrent_validation(self, client):
        """Test download_files max_concurrent parameter validation."""
        with pytest.raises(ValueError, match="max_concurrent must be at least 1"):
            await client.download_files(["https://test.com"], max_concurrent=0)

    @pytest.mark.asyncio
    async def test_download_files_all_downloads_fail(self, client):
        """Test download_files when all downloads fail."""
        download_links = [
            "https://example.com/file1.jpg",
            "https://example.com/file2.jpg",
        ]

        with patch("httpx.AsyncClient") as mock_http_client:
            with patch("pathlib.Path.mkdir"):
                mock_client_instance = AsyncMock()
                mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
                mock_client_instance.__aexit__ = AsyncMock(return_value=None)
                mock_client_instance.get = AsyncMock(side_effect=Exception("Network error"))
                mock_http_client.return_value = mock_client_instance

                with pytest.raises(DownloadError, match="Failed to download any files"):
                    await client.download_files(download_links)

    @pytest.mark.asyncio
    async def test_download_files_partial_failure(self, client):
        """Test download_files with some successful and some failed downloads."""
        download_links = [
            "https://example.com/file1.jpg",  # This will succeed
            "https://example.com/file2.jpg",  # This will fail
        ]

        mock_response_success = Mock()
        mock_response_success.raise_for_status = Mock()
        mock_response_success.content = b"fake image data"

        mock_file = AsyncMock()
        mock_file.__aenter__ = AsyncMock(return_value=mock_file)
        mock_file.__aexit__ = AsyncMock(return_value=None)
        mock_file.write = AsyncMock()

        call_count = 0

        async def mock_get_side_effect(url):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # First call succeeds
                return mock_response_success
            else:  # Second call fails
                raise Exception("Download failed")

        with patch("httpx.AsyncClient") as mock_http_client:
            with patch("aiofiles.open", return_value=mock_file):
                with patch("pathlib.Path.mkdir"):
                    mock_client_instance = AsyncMock()
                    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
                    mock_client_instance.__aexit__ = AsyncMock(return_value=None)
                    mock_client_instance.get = AsyncMock(side_effect=mock_get_side_effect)
                    mock_http_client.return_value = mock_client_instance

                    result = await client.download_files(download_links)

                    # Should return only successful downloads
                    assert len(result) == 1
                    assert "file1.jpg" in result[0]

    @pytest.mark.asyncio
    async def test_download_files_filename_extraction(self, client):
        """Test filename extraction from various URL formats."""
        download_links = [
            "https://example.com/path/image.jpg",
            "https://example.com/image.png?param=value",
        ]

        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.content = b"fake image data"

        mock_file = AsyncMock()
        mock_file.__aenter__ = AsyncMock(return_value=mock_file)
        mock_file.__aexit__ = AsyncMock(return_value=None)
        mock_file.write = AsyncMock()

        with patch("httpx.AsyncClient") as mock_http_client:
            with patch("aiofiles.open", return_value=mock_file):
                with patch("pathlib.Path.mkdir"):
                    mock_client_instance = AsyncMock()
                    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
                    mock_client_instance.__aexit__ = AsyncMock(return_value=None)
                    mock_client_instance.get = AsyncMock(return_value=mock_response)
                    mock_http_client.return_value = mock_client_instance

                    result = await client.download_files(download_links)

                    # Verify filenames were extracted correctly
                    assert len(result) == 2
                    assert any("image.jpg" in path for path in result)
                    assert any("image.png" in path for path in result)

    @pytest.mark.asyncio
    async def test_download_files_http_error(self, client):
        """Test download_files when HTTP request returns error status."""
        download_links = ["https://example.com/file1.jpg"]

        mock_response = Mock()
        mock_response.raise_for_status = Mock(side_effect=httpx.HTTPStatusError("404 Not Found", request=Mock(), response=Mock()))

        with patch("httpx.AsyncClient") as mock_http_client:
            with patch("pathlib.Path.mkdir"):
                mock_client_instance = AsyncMock()
                mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
                mock_client_instance.__aexit__ = AsyncMock(return_value=None)
                mock_client_instance.get = AsyncMock(return_value=mock_response)
                mock_http_client.return_value = mock_client_instance

                with pytest.raises(DownloadError, match="Failed to download any files"):
                    await client.download_files(download_links)

    @pytest.mark.asyncio
    async def test_download_files_custom_output_directory(self, client):
        """Test download_files with custom output directory."""
        download_links = ["https://example.com/file1.jpg"]
        custom_dir = "custom_downloads"

        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.content = b"fake image data"

        mock_file = AsyncMock()
        mock_file.__aenter__ = AsyncMock(return_value=mock_file)
        mock_file.__aexit__ = AsyncMock(return_value=None)
        mock_file.write = AsyncMock()

        with patch("httpx.AsyncClient") as mock_http_client:
            with patch("aiofiles.open", return_value=mock_file):
                with patch("pathlib.Path.mkdir") as mock_mkdir:
                    mock_client_instance = AsyncMock()
                    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
                    mock_client_instance.__aexit__ = AsyncMock(return_value=None)
                    mock_client_instance.get = AsyncMock(return_value=mock_response)
                    mock_http_client.return_value = mock_client_instance

                    result = await client.download_files(download_links, output_dir=custom_dir)

                    # Verify custom directory was used
                    assert len(result) == 1
                    assert custom_dir in result[0]
                    mock_mkdir.assert_called()

    @pytest.mark.asyncio
    async def test_download_files_fallback_filename(self, client):
        """Test download_files with URL that requires fallback filename."""
        download_links = ["https://example.com/noextension"]  # No file extension

        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.content = b"fake image data"

        mock_file = AsyncMock()
        mock_file.__aenter__ = AsyncMock(return_value=mock_file)
        mock_file.__aexit__ = AsyncMock(return_value=None)
        mock_file.write = AsyncMock()

        with patch("httpx.AsyncClient") as mock_http_client:
            with patch("aiofiles.open", return_value=mock_file):
                with patch("pathlib.Path.mkdir"):
                    mock_client_instance = AsyncMock()
                    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
                    mock_client_instance.__aexit__ = AsyncMock(return_value=None)
                    mock_client_instance.get = AsyncMock(return_value=mock_response)
                    mock_http_client.return_value = mock_client_instance

                    result = await client.download_files(download_links)

                    # Should use fallback filename
                    assert len(result) == 1
                    assert "imagen_edited_" in result[0]


class TestImagenClientDownloads:
    """Test download link methods."""

    def _create_download_response(self, files_data: list[dict]):
        """Helper to create download response data."""
        return {"data": {"files_list": files_data}}

    @pytest.mark.asyncio
    async def test_get_download_links_success(self, client, mock_request_factory):
        files_data = [
            {
                "file_name": "image1.jpg",
                "download_link": "https://example.com/download1.jpg",
            },
            {
                "file_name": "image2.jpg",
                "download_link": "https://example.com/download2.jpg",
            },
        ]
        response_data = self._create_download_response(files_data)

        with mock_request_factory(response_data):
            links = await client.get_download_links("test-uuid")

            assert len(links) == 2
            assert links[0] == "https://example.com/download1.jpg"
            assert links[1] == "https://example.com/download2.jpg"

            client._make_request.assert_called_once_with("GET", "/projects/test-uuid/edit/get_temporary_download_links")

    @pytest.mark.asyncio
    async def test_get_export_links_success(self, client, mock_request_factory):
        files_data = [
            {
                "file_name": "export1.jpg",
                "download_link": "https://example.com/export1.jpg",
            }
        ]
        response_data = self._create_download_response(files_data)

        with mock_request_factory(response_data):
            links = await client.get_export_links("test-uuid")

            assert len(links) == 1
            assert links[0] == "https://example.com/export1.jpg"

            client._make_request.assert_called_once_with("GET", "/projects/test-uuid/export/get_temporary_download_links")

    @pytest.mark.asyncio
    async def test_get_download_links_invalid_response(self, client, mock_request_factory):
        invalid_response = {"bad": "format"}

        with mock_request_factory(invalid_response):
            with pytest.raises(ProjectError, match="Could not parse download links response"):
                await client.get_download_links("test-uuid")


class TestImagenClientEditing:
    """Test editing-related methods."""

    @pytest.mark.asyncio
    async def test_start_editing_basic(self, client):
        with patch.object(client, "_make_request") as mock_request:
            with patch.object(client, "_wait_for_completion") as mock_wait:
                mock_wait.return_value = StatusDetails(status="Completed")

                result = await client.start_editing("test-uuid", 123)

                mock_request.assert_called_once_with(
                    "POST",
                    "/projects/test-uuid/edit",
                    json={"profile_key": 123},
                    headers={"Content-Type": ""},
                )

                mock_wait.assert_called_once_with("test-uuid", "edit")
                assert result.status == "Completed"

    @pytest.mark.asyncio
    async def test_start_editing_with_options(self, client):
        photography_type = PhotographyType.PORTRAITS
        edit_options = EditOptions(crop=True, straighten=False)

        with patch.object(client, "_make_request") as mock_request:
            with patch.object(client, "_wait_for_completion") as mock_wait:
                mock_wait.return_value = StatusDetails(status="Completed")

                await client.start_editing("test-uuid", 123, photography_type, edit_options)

                expected_json = {
                    "profile_key": 123,
                    "photography_type": "PORTRAITS",
                    "crop": True,
                    "straighten": False,
                }

                mock_request.assert_called_once_with(
                    "POST",
                    "/projects/test-uuid/edit",
                    json=expected_json,
                    headers={"Content-Type": ""},
                )

    @pytest.mark.asyncio
    async def test_export_project(self, client):
        with patch.object(client, "_make_request") as mock_request:
            with patch.object(client, "_wait_for_completion") as mock_wait:
                mock_wait.return_value = StatusDetails(status="Completed")

                result = await client.export_project("test-uuid")

                mock_request.assert_called_once_with("POST", "/projects/test-uuid/export")
                mock_wait.assert_called_once_with("test-uuid", "export")
                assert result.status == "Completed"


class TestImagenClientStatusPolling:
    """Test status polling functionality."""

    def _create_status_response(self, status: str, progress: float = None, details: str = None):
        """Helper to create status response data."""
        data = {"status": status}
        if progress is not None:
            data["progress"] = progress
        if details is not None:
            data["details"] = details
        return {"data": data}

    @pytest.mark.asyncio
    async def test_wait_for_completion_immediate_success(self, client, mock_request_factory):
        response_data = self._create_status_response("Completed", 100.0)

        with mock_request_factory(response_data):
            with patch("builtins.print"):  # Suppress print output
                result = await client._wait_for_completion("test-uuid", "edit")

                assert result.status == "Completed"
                assert result.progress == 100.0
                client._make_request.assert_called_once_with("GET", "/projects/test-uuid/edit/status")

    @pytest.mark.asyncio
    async def test_wait_for_completion_with_progress(self, client):
        # Mock multiple status responses: processing -> completed
        status_responses = [
            self._create_status_response("Processing", 25.0),
            self._create_status_response("Processing", 75.0),
            self._create_status_response("Completed", 100.0),
        ]

        call_count = 0

        def mock_request_side_effect(*args, **kwargs):
            nonlocal call_count
            response = status_responses[call_count]
            call_count += 1
            return response

        with patch.object(client, "_make_request", side_effect=mock_request_side_effect):
            with patch("asyncio.sleep"):  # Skip actual waiting
                with patch("builtins.print"):  # Suppress print output
                    result = await client._wait_for_completion("test-uuid", "edit")

                    assert result.status == "Completed"
                    assert result.progress == 100.0
                    assert call_count == 3

    @pytest.mark.asyncio
    async def test_wait_for_completion_failure(self, client, mock_request_factory):
        response_data = self._create_status_response("Failed", details="Processing error occurred")

        with mock_request_factory(response_data):
            with patch("builtins.print"):  # Suppress print output
                with pytest.raises(ProjectError, match="Edit failed.*Processing error occurred"):
                    await client._wait_for_completion("test-uuid", "edit")

    @pytest.mark.asyncio
    async def test_wait_for_completion_invalid_response(self, client, mock_request_factory):
        invalid_response = {"wrong": "format"}

        with mock_request_factory(invalid_response):
            with patch("builtins.print"):  # Suppress print output
                with pytest.raises(ProjectError, match="Could not parse status response"):
                    await client._wait_for_completion("test-uuid", "edit")


class TestImagenClientFileOperations:
    """Test file operation static methods."""

    @pytest.mark.asyncio
    async def test_calculate_md5(self, mock_helpers):
        test_content = b"test file content for md5"
        expected_md5 = "CldbCd+F12oPFPJyZ2uDrw=="

        mock_file = mock_helpers.create_async_file_mock(test_content)

        with patch("aiofiles.open", return_value=mock_file):
            result = await ImagenClient._calculate_md5(Path("test.txt"))
            assert result == expected_md5

    @pytest.mark.asyncio
    async def test_upload_to_s3_success(self, mock_helpers):
        test_content = b"test image data"
        upload_url = "https://s3.amazonaws.com/test-bucket/test.jpg"

        # Mock file operations
        mock_file = mock_helpers.create_async_file_mock(test_content)

        # Mock HTTP client
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_client = mock_helpers.create_async_http_client_mock(mock_response)

        with patch("aiofiles.open", return_value=mock_file):
            with patch("httpx.AsyncClient", return_value=mock_client):
                await ImagenClient._upload_to_s3(Path("test.jpg"), upload_url)

                mock_client.put.assert_called_once_with(upload_url, content=test_content)
                mock_response.raise_for_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_to_s3_failure(self, mock_helpers):
        test_content = b"test image data"
        upload_url = "https://s3.amazonaws.com/test-bucket/test.jpg"

        mock_file = mock_helpers.create_async_file_mock(test_content)

        # Mock HTTP client to raise an error
        mock_response = Mock()
        mock_response.raise_for_status = Mock(side_effect=httpx.HTTPStatusError("Upload failed", request=Mock(), response=Mock()))
        mock_client = mock_helpers.create_async_http_client_mock(mock_response)

        with patch("aiofiles.open", return_value=mock_file):
            with patch("httpx.AsyncClient", return_value=mock_client):
                # Fix: Expect UploadError instead of HTTPStatusError (the SDK wraps exceptions)
                with pytest.raises(UploadError, match="Failed to upload test.jpg"):
                    await ImagenClient._upload_to_s3(Path("test.jpg"), upload_url)


class TestImagenClientUploadImages:
    """Test the upload_images method."""

    def _create_presigned_response(self, files_data: list[dict]):
        """Helper to create presigned URL response."""
        return {"data": {"files_list": files_data}}

    def _create_mock_path(self, name: str, exists: bool = True):
        """Create a mock Path that can be used in place of real Path objects."""
        mock_path = Mock()
        mock_path.exists.return_value = exists
        mock_path.name = name
        mock_path.__str__ = Mock(return_value=name)
        mock_path.__fspath__ = Mock(return_value=name)
        return mock_path

    @pytest.mark.asyncio
    async def test_upload_images_no_valid_files(self, client):
        # Mock Path constructor to return paths that don't exist
        def mock_path_constructor(path_str):
            mock_path = self._create_mock_path(path_str, exists=False)
            return mock_path

        with patch("imagen_sdk.imagen_sdk.Path", side_effect=mock_path_constructor):
            with pytest.raises(UploadError, match="No valid local files found"):
                await client.upload_images("test-uuid", ["nonexistent.jpg"])

    @pytest.mark.asyncio
    async def test_upload_images_success(self, client, mock_request_factory):
        image_paths = ["img1.jpg", "img2.jpg"]

        # Mock presigned URL response
        files_data = [
            {"file_name": "img1.jpg", "upload_link": "https://s3.com/upload1"},
            {"file_name": "img2.jpg", "upload_link": "https://s3.com/upload2"},
        ]
        presigned_response = self._create_presigned_response(files_data)

        # Mock Path constructor to return mock paths that exist
        def mock_path_constructor(path_str):
            return self._create_mock_path(path_str, exists=True)

        with patch("imagen_sdk.imagen_sdk.Path", side_effect=mock_path_constructor):
            with mock_request_factory(presigned_response):
                with patch.object(client, "_upload_to_s3") as mock_upload:
                    result = await client.upload_images("test-uuid", image_paths)

                    assert result.total == 2
                    assert result.successful == 2
                    assert result.failed == 0
                    assert len(result.results) == 2

                    # Verify the presigned URL request
                    expected_payload = {
                        "files_list": [
                            {"file_name": "img1.jpg"},
                            {"file_name": "img2.jpg"},
                        ]
                    }
                    client._make_request.assert_called_once_with(
                        "POST",
                        "/projects/test-uuid/get_temporary_upload_links",
                        json=expected_payload,
                    )

                    # Verify S3 uploads were called
                    assert mock_upload.call_count == 2

    @pytest.mark.asyncio
    async def test_upload_images_with_md5(self, client, mock_request_factory):
        image_paths = ["img1.jpg"]

        files_data = [{"file_name": "img1.jpg", "upload_link": "https://s3.com/upload1"}]
        presigned_response = self._create_presigned_response(files_data)

        # Mock Path constructor
        def mock_path_constructor(path_str):
            return self._create_mock_path(path_str, exists=True)

        with patch("imagen_sdk.imagen_sdk.Path", side_effect=mock_path_constructor):
            with mock_request_factory(presigned_response):
                with patch.object(client, "_calculate_md5", return_value="test-md5-hash"):
                    with patch.object(client, "_upload_to_s3"):
                        await client.upload_images("test-uuid", image_paths, calculate_md5=True)

                        # Verify the request included MD5
                        expected_payload = {"files_list": [{"file_name": "img1.jpg", "md5": "test-md5-hash"}]}
                        client._make_request.assert_called_once_with(
                            "POST",
                            "/projects/test-uuid/get_temporary_upload_links",
                            json=expected_payload,
                        )

    @pytest.mark.asyncio
    async def test_upload_images_partial_failure(self, client, mock_request_factory):
        image_paths = ["img1.jpg", "img2.jpg"]

        files_data = [
            {"file_name": "img1.jpg", "upload_link": "https://s3.com/upload1"},
            {"file_name": "img2.jpg", "upload_link": "https://s3.com/upload2"},
        ]
        presigned_response = self._create_presigned_response(files_data)

        # Mock Path constructor
        def mock_path_constructor(path_str):
            return self._create_mock_path(path_str, exists=True)

        # Mock one upload success, one failure
        async def mock_upload_side_effect(path, url):
            if "img2" in str(path):
                raise Exception("Upload failed")

        with patch("imagen_sdk.imagen_sdk.Path", side_effect=mock_path_constructor):
            with mock_request_factory(presigned_response):
                with patch.object(client, "_upload_to_s3", side_effect=mock_upload_side_effect):
                    result = await client.upload_images("test-uuid", image_paths)

                    assert result.total == 2
                    assert result.successful == 1
                    assert result.failed == 1

                    # Check individual results
                    successful_result = next(r for r in result.results if r.success)
                    failed_result = next(r for r in result.results if not r.success)

                    assert successful_result.error is None
                    assert failed_result.error == "Upload failed"


# Parametrized tests for testing multiple scenarios
class TestPhotographyTypeValues:
    """Test PhotographyType enum values with parametrized tests."""

    @pytest.mark.parametrize(
        "photo_type,expected_value",
        [
            ("NO_TYPE", "NO_TYPE"),
            ("OTHER", "OTHER"),
            ("PORTRAITS", "PORTRAITS"),
            ("WEDDING", "WEDDING"),
            ("REAL_ESTATE", "REAL_ESTATE"),
            ("LANDSCAPE_NATURE", "LANDSCAPE_NATURE"),
            ("EVENTS", "EVENTS"),
            ("FAMILY_NEWBORN", "FAMILY_NEWBORN"),
            ("BOUDOIR", "BOUDOIR"),
            ("SPORTS", "SPORTS"),
        ],
    )
    def test_photography_type_values(self, photo_type, expected_value):
        assert getattr(PhotographyType, photo_type).value == expected_value


class TestEditOptionsValidation:
    """Test EditOptions model validation and conversion."""

    def test_edit_options_to_api_dict_all_options(self):
        """Test EditOptions conversion with all options set."""
        options = EditOptions(
            crop=True,
            straighten=False,
            hdr_merge=True,
            portrait_crop=None,
            smooth_skin=True,
        )

        api_dict = options.to_api_dict()

        # Should exclude None values
        expected = {
            "crop": True,
            "straighten": False,
            "hdr_merge": True,
            "smooth_skin": True,
        }
        assert api_dict == expected
        assert "portrait_crop" not in api_dict

    def test_edit_options_empty(self):
        """Test EditOptions with no values set."""
        options = EditOptions()
        api_dict = options.to_api_dict()
        assert api_dict == {}

    def test_edit_options_only_none_values(self):
        """Test EditOptions with only None values."""
        options = EditOptions(
            crop=None,
            straighten=None,
            hdr_merge=None,
            portrait_crop=None,
            smooth_skin=None,
        )
        api_dict = options.to_api_dict()
        assert api_dict == {}


# Integration-style tests
class TestImagenClientIntegration:
    """Test integration scenarios across multiple methods."""

    @pytest.mark.asyncio
    async def test_full_workflow_simulation(self, client):
        """Test a simplified full workflow simulation."""
        # Instead of trying to mock the entire sequence, let's test each step individually
        # with proper mocking to avoid the complex call ordering issues

        # Test get_profiles
        profiles_response = {
            "data": {
                "profiles": [
                    {
                        "image_type": "portrait",
                        "profile_key": 1,
                        "profile_name": "Test Profile",
                        "profile_type": "standard",
                    }
                ]
            }
        }

        with patch.object(client, "_make_request", return_value=profiles_response):
            profiles = await client.get_profiles()
            assert len(profiles) == 1
            assert profiles[0].profile_name == "Test Profile"

        # Test create_project
        project_response = {"data": {"project_uuid": "workflow-test-uuid"}}

        with patch.object(client, "_make_request", return_value=project_response):
            project_uuid = await client.create_project("Test Project")
            assert project_uuid == "workflow-test-uuid"

        # Test upload_images (simplified)
        upload_response = {"data": {"files_list": [{"file_name": "test.jpg", "upload_link": "https://s3.com/upload"}]}}

        def mock_path_constructor(path_str):
            mock_path = Mock()
            mock_path.exists.return_value = True
            mock_path.name = "test.jpg"
            mock_path.__str__ = Mock(return_value=path_str)
            mock_path.__fspath__ = Mock(return_value=path_str)
            return mock_path

        with patch("imagen_sdk.imagen_sdk.Path", side_effect=mock_path_constructor):
            with patch.object(client, "_upload_to_s3"):
                with patch.object(client, "_make_request", return_value=upload_response):
                    upload_result = await client.upload_images(project_uuid, ["test.jpg"])
                    assert upload_result.successful == 1

        # Test start_editing (mock the _wait_for_completion method directly)
        status_details = StatusDetails(status="Completed", progress=100.0)

        with patch.object(client, "_make_request", return_value={}):  # POST returns empty
            with patch.object(client, "_wait_for_completion", return_value=status_details):
                edit_result = await client.start_editing(project_uuid, profiles[0].profile_key)
                assert edit_result.status == "Completed"

        # Test get_download_links
        download_response = {
            "data": {
                "files_list": [
                    {
                        "file_name": "test_edited.jpg",
                        "download_link": "https://download.com/test.jpg",
                    }
                ]
            }
        }

        with patch.object(client, "_make_request", return_value=download_response):
            download_links = await client.get_download_links(project_uuid)
            assert len(download_links) == 1
            assert download_links[0] == "https://download.com/test.jpg"

    @pytest.mark.asyncio
    async def test_error_handling_chain(self, client):
        """Test error handling across multiple method calls."""
        # Test that errors in early steps prevent later steps from being called
        project_response = {"data": {"project_uuid": "error-test-uuid"}}

        with patch.object(client, "_make_request", return_value=project_response) as mock_request:
            # First call succeeds (create project)
            project_uuid = await client.create_project("Error Test")
            assert project_uuid == "error-test-uuid"

            # Second call fails (upload images with invalid response)
            mock_request.return_value = {"invalid": "response"}

            with pytest.raises(Exception):  # Should raise validation error
                await client.upload_images(project_uuid, ["test.jpg"])


# Error handling tests with parametrization
class TestErrorHandling:
    """Test various error scenarios with parametrized tests."""

    @pytest.mark.parametrize(
        "status_code,error_type,error_message",
        [
            (401, AuthenticationError, "Invalid API key"),
            (400, ImagenError, "API Error \\(400\\)"),
            (404, ImagenError, "API Error \\(404\\)"),
            (500, ImagenError, "API Error \\(500\\)"),
        ],
    )
    @pytest.mark.asyncio
    async def test_http_error_handling(self, client, mock_helpers, status_code, error_type, error_message):
        """Test different HTTP error status codes."""
        mock_response = mock_helpers.create_http_response(status_code, text="Error message")

        with patch.object(client, "_get_session") as mock_session:
            mock_session.return_value.request = AsyncMock(return_value=mock_response)

            with pytest.raises(error_type, match=error_message):
                await client._make_request("GET", "/test")

    @pytest.mark.parametrize(
        "invalid_response",
        [
            {"wrong": "format"},
            {"data": "not_an_object"},
            {},
            {"data": {}},
        ],
    )
    @pytest.mark.asyncio
    async def test_invalid_response_formats(self, client, mock_request_factory, invalid_response):
        """Test handling of various invalid response formats."""
        with mock_request_factory(invalid_response):
            with pytest.raises((ProjectError, ImagenError, ValidationError)):
                await client.create_project("Test")


# Performance and edge case tests
class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_upload_images_max_concurrent_validation(self, client):
        """Test max_concurrent parameter validation."""
        with pytest.raises(ValueError, match="max_concurrent must be at least 1"):
            await client.upload_images("test-uuid", ["test.jpg"], max_concurrent=0)

    @pytest.mark.asyncio
    async def test_empty_image_paths_list(self, client):
        """Test behavior with empty image paths list."""
        with pytest.raises(UploadError, match="No valid local files found"):
            await client.upload_images("test-uuid", [])

    @pytest.mark.asyncio
    async def test_download_files_empty_links(self, client):
        """Test download_files with empty links list."""
        # Now that DownloadError is exported, we can import it normally
        with pytest.raises(DownloadError, match="No download links provided"):
            await client.download_files([])

    @pytest.mark.asyncio
    async def test_download_files_max_concurrent_validation(self, client):
        """Test download_files max_concurrent parameter validation."""
        with pytest.raises(ValueError, match="max_concurrent must be at least 1"):
            await client.download_files(["https://test.com"], max_concurrent=0)

    def test_extract_filename_from_url_edge_cases(self):
        """Test filename extraction from various URL formats."""
        # Test normal URL
        filename = ImagenClient._extract_filename_from_url("https://example.com/path/image.jpg", 0)
        assert filename == "image.jpg"

        # Test URL with query parameters
        filename = ImagenClient._extract_filename_from_url("https://example.com/image.jpg?param=value", 1)
        assert filename == "image.jpg"

        # Test URL without extension (should use fallback)
        filename = ImagenClient._extract_filename_from_url("https://example.com/noextension", 2)
        assert filename == "imagen_edited_00003.jpg"

        # Test malformed URL (should use fallback)
        filename = ImagenClient._extract_filename_from_url("not-a-url", 3)
        assert filename == "imagen_edited_00004.jpg"

    @pytest.mark.asyncio
    async def test_status_polling_timeout_simulation(self, client):
        """Test status polling with timeout (without actually waiting)."""
        # Mock a response that would normally cause timeout
        never_complete_response = {"data": {"status": "Processing", "progress": 50.0}}

        with patch.object(client, "_make_request", return_value=never_complete_response):
            with patch("time.time", side_effect=[0, 73000]):  # Simulate time passing beyond timeout
                with patch("builtins.print"):  # Suppress print output
                    with pytest.raises(ProjectError, match="timed out after"):
                        await client._wait_for_completion("test-uuid", "edit")


# Marks for organizing tests
pytestmark = [
    pytest.mark.unit,  # Mark all tests in this file as unit tests
]


# Test configuration for this module
def pytest_configure(config):
    """Configure pytest for this test module."""
    config.addinivalue_line("markers", "unit: Unit tests for individual components")
    config.addinivalue_line("markers", "integration: Integration tests across components")
    config.addinivalue_line("markers", "slow: Slow running tests")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
