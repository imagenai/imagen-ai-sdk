"""Tests for the image-to-image (I2I) mixin, including multipart uploads."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from imagen_sdk import I2IEditOptions, MultipartUploadLinksResponse, ProjectError, UploadError


class TestI2IProjectLifecycle:
    @pytest.mark.asyncio
    async def test_create_i2i_project(self, client, mock_request_factory):
        with mock_request_factory({"project_uuid": "i2i-1"}):
            uuid = await client.create_i2i_project("My I2I")
            assert uuid == "i2i-1"
            client._make_request.assert_called_once_with("POST", "/i2i/projects/", json={"name": "My I2I"})

    @pytest.mark.asyncio
    async def test_create_i2i_project_wrapped(self, client, mock_request_factory):
        with mock_request_factory({"data": {"project_uuid": "i2i-2"}}):
            assert await client.create_i2i_project() == "i2i-2"

    @pytest.mark.asyncio
    async def test_list_i2i_projects(self, client, mock_request_factory):
        response = {"projects": [], "pagination": {"total": 0, "size": 20, "page": 0}}
        with mock_request_factory(response):
            result = await client.list_i2i_projects()
            assert result.pagination.total == 0
            args, _ = client._make_request.call_args
            assert args == ("GET", "/i2i/projects")

    @pytest.mark.asyncio
    async def test_validate_name_true(self, client, mock_request_factory):
        with mock_request_factory({"is_valid": True}):
            assert await client.validate_i2i_project_name("ok") is True

    @pytest.mark.asyncio
    async def test_validate_name_false(self, client, mock_request_factory):
        with mock_request_factory({"is_valid": False}):
            assert await client.validate_i2i_project_name("taken") is False

    @pytest.mark.asyncio
    async def test_validate_name_empty_response_means_valid(self, client, mock_request_factory):
        with mock_request_factory({}):
            assert await client.validate_i2i_project_name("ok") is True


class TestI2IEditingAndDownloads:
    @pytest.mark.asyncio
    async def test_start_i2i_editing_with_options(self, client, mock_request_factory):
        with mock_request_factory({"message": "Project proj sent for I2I editing successfully."}):
            result = await client.start_i2i_editing("proj", I2IEditOptions(hdr_merge=True, perspective_correction=True))
            assert result.message == "Project proj sent for I2I editing successfully."
            args, kwargs = client._make_request.call_args
            assert args == ("POST", "/i2i/projects/proj/edit")
            assert kwargs["json"] == {"hdr_merge": True, "perspective_correction": True}

    @pytest.mark.asyncio
    async def test_start_i2i_editing_no_options(self, client, mock_request_factory):
        with mock_request_factory({"message": "ok"}):
            await client.start_i2i_editing("proj")
            _, kwargs = client._make_request.call_args
            assert kwargs["json"] == {}

    @pytest.mark.asyncio
    async def test_get_i2i_download_links(self, client, mock_request_factory):
        response = {"files_list": [{"file_name": "a.jpg", "download_link": "https://dl1"}]}
        with mock_request_factory(response):
            links = await client.get_i2i_download_links("proj")
            assert links == ["https://dl1"]

    @pytest.mark.asyncio
    async def test_get_i2i_download_link(self, client, mock_request_factory):
        with mock_request_factory({"download_link": "https://dl/single.jpg"}):
            result = await client.get_i2i_download_link("proj", "single.jpg")
            assert result.download_link == "https://dl/single.jpg"
            args, kwargs = client._make_request.call_args
            assert args == ("GET", "/i2i/projects/proj/get_download_link")
            assert kwargs["params"] == {"file_name": "single.jpg"}


class TestI2IUpload:
    @pytest.mark.asyncio
    async def test_upload_i2i_images(self, client, tmp_path, mock_request_factory):
        f1 = tmp_path / "img1.jpg"
        f1.write_bytes(b"data")
        response = {"files_list": [{"file_name": "img1.jpg", "upload_link": "https://up1"}]}
        with mock_request_factory(response):
            with patch.object(client, "_upload_to_s3", new=AsyncMock()) as mock_put:
                summary = await client.upload_i2i_images("proj", [str(f1)])
                assert summary.successful == 1
                mock_put.assert_awaited_once()
                args, _ = client._make_request.call_args
                assert args == ("POST", "/i2i/projects/proj/get_temporary_upload_links")

    @pytest.mark.asyncio
    async def test_large_file_auto_routes_to_multipart(self, client, tmp_path, mock_request_factory):
        big = tmp_path / "big.bin"
        big.write_bytes(b"x" * 50)
        # threshold below the file size -> must use multipart, never the batch endpoint
        with mock_request_factory({"files_list": []}):
            with patch.object(client, "upload_i2i_file_multipart", new=AsyncMock()) as mp:
                summary = await client.upload_i2i_images("proj", [str(big)], multipart_threshold=10)
                assert summary.successful == 1 and summary.total == 1
                mp.assert_awaited_once()
                client._make_request.assert_not_called()  # no batch single-PUT request

    @pytest.mark.asyncio
    async def test_mixed_sizes_split_between_paths(self, client, tmp_path, mock_request_factory):
        small = tmp_path / "small.jpg"
        small.write_bytes(b"x" * 5)
        big = tmp_path / "big.bin"
        big.write_bytes(b"x" * 100)
        response = {"files_list": [{"file_name": "small.jpg", "upload_link": "https://up"}]}
        with mock_request_factory(response):
            with (
                patch.object(client, "_upload_to_s3", new=AsyncMock()) as put,
                patch.object(client, "upload_i2i_file_multipart", new=AsyncMock()) as mp,
            ):
                summary = await client.upload_i2i_images("proj", [str(small), str(big)], multipart_threshold=10)
                assert summary.total == 2 and summary.successful == 2
                put.assert_awaited_once()  # small via single PUT
                mp.assert_awaited_once()  # big via multipart
                # batch request sent only the small file
                _, kwargs = client._make_request.call_args
                assert [f["file_name"] for f in kwargs["json"]["files_list"]] == ["small.jpg"]

    @pytest.mark.asyncio
    async def test_large_file_multipart_failure_recorded(self, client, tmp_path, mock_request_factory):
        big = tmp_path / "big.bin"
        big.write_bytes(b"x" * 50)
        with mock_request_factory({"files_list": []}):
            with patch.object(client, "upload_i2i_file_multipart", new=AsyncMock(side_effect=Exception("boom"))):
                summary = await client.upload_i2i_images("proj", [str(big)], multipart_threshold=10)
                assert summary.failed == 1 and summary.successful == 0
                assert "boom" in summary.results[0].error


class TestI2IMultipart:
    @pytest.mark.asyncio
    async def test_create_multipart_payload(self, client, mock_request_factory):
        response = {"upload_id": "uid", "key": "k", "parts": [{"part_number": 1, "upload_url": "https://u1"}]}
        with mock_request_factory(response):
            result = await client.create_i2i_multipart_upload("proj", "big.arw", 1)
            assert result.upload_id == "uid"
            args, kwargs = client._make_request.call_args
            assert args == ("POST", "/i2i/projects/proj/multipart_uploads")
            assert kwargs["json"] == {"file_name": "big.arw", "part_count": 1}

    @pytest.mark.asyncio
    async def test_complete_multipart_payload(self, client, mock_request_factory):
        with mock_request_factory({}):
            await client.complete_i2i_multipart_upload("proj", "uid", "big.arw")
            args, kwargs = client._make_request.call_args
            assert args == ("POST", "/i2i/projects/proj/multipart_uploads/uid/complete")
            assert kwargs["json"] == {"file_name": "big.arw"}

    @pytest.mark.asyncio
    async def test_abort_multipart_payload(self, client, mock_request_factory):
        with mock_request_factory({}):
            await client.abort_i2i_multipart_upload("proj", "uid", "k")
            args, kwargs = client._make_request.call_args
            assert args == ("DELETE", "/i2i/projects/proj/multipart_uploads/uid")
            assert kwargs["json"] == {"key": "k"}

    @pytest.mark.asyncio
    async def test_upload_file_multipart_success(self, client, tmp_path):
        big = tmp_path / "big.bin"
        big.write_bytes(b"0123456789" * 3)  # 30 bytes

        links = MultipartUploadLinksResponse(
            upload_id="uid",
            key="k",
            parts=[
                {"part_number": 1, "upload_url": "https://u1"},
                {"part_number": 2, "upload_url": "https://u2"},
                {"part_number": 3, "upload_url": "https://u3"},
            ],
        )

        # Mock the S3 PUT for each part.
        put_response = MagicMock()
        put_response.raise_for_status = MagicMock()
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=None)
        mock_http.put = AsyncMock(return_value=put_response)

        with (
            patch.object(client, "create_i2i_multipart_upload", new=AsyncMock(return_value=links)),
            patch.object(client, "complete_i2i_multipart_upload", new=AsyncMock()) as mock_complete,
            patch("imagen_sdk._i2i.httpx.AsyncClient", return_value=mock_http),
        ):
            result = await client.upload_i2i_file_multipart("proj", str(big), part_size=10)
            assert result.upload_id == "uid"
            assert mock_http.put.await_count == 3
            mock_complete.assert_awaited_once_with("proj", "uid", "big.bin")

    @pytest.mark.asyncio
    async def test_create_multipart_rejects_too_many_parts(self, client):
        # S3 caps multipart uploads at 10000 parts; the request model enforces it.
        with pytest.raises(ValidationError):
            await client.create_i2i_multipart_upload("proj", "big.arw", 10001)

    @pytest.mark.asyncio
    async def test_upload_file_multipart_rejects_invalid_concurrency(self, client, tmp_path):
        f = tmp_path / "f.bin"
        f.write_bytes(b"data")
        with pytest.raises(ValueError, match="max_concurrent"):
            await client.upload_i2i_file_multipart("proj", str(f), max_concurrent=0)

    @pytest.mark.asyncio
    async def test_upload_file_multipart_missing_file(self, client):
        with pytest.raises(UploadError):
            await client.upload_i2i_file_multipart("proj", "/nonexistent/file.bin")

    @pytest.mark.asyncio
    async def test_upload_file_multipart_aborts_on_failure(self, client, tmp_path):
        big = tmp_path / "big.bin"
        big.write_bytes(b"0123456789" * 2)

        links = MultipartUploadLinksResponse(
            upload_id="uid",
            key="k",
            parts=[{"part_number": 1, "upload_url": "https://u1"}],
        )
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=None)
        mock_http.put = AsyncMock(side_effect=Exception("network down"))

        with (
            patch.object(client, "create_i2i_multipart_upload", new=AsyncMock(return_value=links)),
            patch.object(client, "abort_i2i_multipart_upload", new=AsyncMock()) as mock_abort,
            patch("imagen_sdk._i2i.httpx.AsyncClient", return_value=mock_http),
        ):
            with pytest.raises(UploadError):
                await client.upload_i2i_file_multipart("proj", str(big), part_size=10)
            mock_abort.assert_awaited_once_with("proj", "uid", "k")


class TestI2IGetProject:
    @pytest.mark.asyncio
    async def test_get_i2i_project_invalid(self, client, mock_request_factory):
        with mock_request_factory({"bad": 1}):
            with pytest.raises(ProjectError):
                await client.get_i2i_project("uuid")
