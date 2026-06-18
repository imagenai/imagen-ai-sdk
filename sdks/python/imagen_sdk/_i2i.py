"""
Image-to-image (I2I) mixin for ImagenClient.

I2I is a separate project type that takes input images and produces transformed
output images (e.g. HDR merge, sky replacement, perspective correction), distinct
from the classic RAW/JPG cull-edit-export workflow.

Adds the full ``/v1/i2i/...`` project family:

- create_i2i_project / list_i2i_projects / validate_i2i_project_name / get_i2i_project
- upload_i2i_images: the recommended upload entry point; routes each file by size
  (small -> single PUT, large -> multipart) so callers never choose a method
- multipart upload primitives for large files: create / complete / abort, plus the
  high-level upload_i2i_file_multipart helper (used by upload_i2i_images, also public
  as an advanced escape hatch)
- start_i2i_editing (trigger only; there is no I2I status endpoint, completion is
  signalled via callback_url or by download links becoming available)
- get_i2i_download_links / get_i2i_download_link / get_i2i_upload_link
"""

from __future__ import annotations

import asyncio
import math
from collections.abc import Callable
from pathlib import Path
from typing import Any

import aiofiles
import httpx

from ._core import _CoreClientMixin
from .exceptions import ProjectError, UploadError
from .models import (
    CompleteMultipartUploadRequest,
    CreateFilesUploadLinksRequest,
    CreateMultipartUploadLinksRequest,
    DownloadLinksList,
    FileUploadInfo,
    I2IEditOptions,
    MessageResponse,
    MultipartUploadLinksResponse,
    PresignedUrlList,
    ProjectCreationResponseData,
    ProjectListItem,
    ProjectListResponse,
    SingleDownloadLink,
    TemporaryFileUploadData,
    UploadResult,
    UploadSummary,
)

# S3 multipart part size: 64 MB (must be >= 5 MB except for the final part).
DEFAULT_MULTIPART_PART_SIZE = 64 * 1024 * 1024


class I2IMixin(_CoreClientMixin):
    """Image-to-image project creation, uploads (incl. multipart), editing, and downloads."""

    # -- Project lifecycle ----------------------------------------------------

    async def create_i2i_project(self, name: str | None = None) -> str:
        """
        Create a new image-to-image (I2I) project.

        Args:
            name: Optional unique project name. A UUID is generated server-side if omitted.

        Returns:
            The created project's UUID.

        Raises:
            ProjectError: If the response cannot be parsed.
        """
        data: dict[str, Any] = {}
        if name:
            data["name"] = name

        self._logger.info(f"Creating I2I project: {name or 'Unnamed'}")
        response_json = await self._make_request("POST", "/i2i/projects/", json=data)
        project_uuid = self._parse_model(
            response_json, ProjectCreationResponseData, "I2I project creation response", ProjectError
        ).project_uuid
        self._logger.info(f"Created I2I project with UUID: {project_uuid}")
        return project_uuid

    async def list_i2i_projects(
        self,
        size: int = 20,
        page: int = 0,
        is_archived: bool | None = False,
    ) -> ProjectListResponse:
        """
        List I2I projects with pagination.

        Args:
            size: Page size (1-100, default 20).
            page: Zero-based page index (default 0).
            is_archived: Filter by archived state, or None for all (default False).

        Returns:
            ProjectListResponse with the page of projects and pagination metadata.
            Ordering is defined by the API, not the SDK; in practice projects come
            back newest-first, so page 0 holds your most recently created projects.
        """
        params: dict[str, object] = {"size": size, "page": page}
        if is_archived is not None:
            params["is_archived"] = is_archived

        self._logger.debug(f"Listing I2I projects (page={page}, size={size})")
        response_json = await self._make_request("GET", "/i2i/projects", params=params)
        return self._parse_model(response_json, ProjectListResponse, "I2I project list response", ProjectError)

    async def validate_i2i_project_name(self, name: str) -> bool:
        """
        Check whether an I2I project name is valid/available.

        Args:
            name: The candidate project name.

        Returns:
            True if the name is valid/available, False otherwise. A successful (2xx)
            response with no explicit flag is treated as valid.
        """
        self._logger.debug(f"Validating I2I project name: {name}")
        response_json = await self._make_request("GET", "/i2i/projects/is_valid_name", params={"name": name})
        data = self._unwrap(response_json)
        if isinstance(data, bool):
            return data
        if isinstance(data, dict):
            for key in ("is_valid", "valid"):
                if key in data:
                    return bool(data[key])
        return True

    async def get_i2i_project(self, project_uuid: str, get_thumbnail: bool = True) -> ProjectListItem:
        """
        Get a single I2I project by UUID.

        Args:
            project_uuid: UUID of the I2I project.
            get_thumbnail: Whether to include the thumbnail URL (default True).

        Returns:
            ProjectListItem describing the project.
        """
        self._logger.debug(f"Getting I2I project {project_uuid}")
        response_json = await self._make_request("GET", f"/i2i/projects/{project_uuid}", params={"get_thumbnail": get_thumbnail})
        return self._parse_model(response_json, ProjectListItem, "I2I project response", ProjectError)

    # -- Uploads --------------------------------------------------------------

    async def upload_i2i_images(
        self,
        project_uuid: str,
        image_paths: list[str | Path],
        max_concurrent: int = 5,
        calculate_md5: bool = False,
        progress_callback: Callable[[int, int, str], None] | None = None,
        multipart_threshold: int = DEFAULT_MULTIPART_PART_SIZE,
    ) -> UploadSummary:
        """
        Upload images to an I2I project, picking the right mechanism per file.

        This is the recommended I2I upload entry point: each file is routed
        automatically based on its size, so callers never choose an upload method.

        - Files at or below ``multipart_threshold`` are batched into a single
          ``get_temporary_upload_links`` request and uploaded concurrently with a
          single presigned PUT each.
        - Files above the threshold are uploaded with S3 multipart
          (``upload_i2i_file_multipart``), which chunks the file and is resilient on
          large/slow transfers.

        Multipart is only available for I2I projects (the standard ``upload_images``
        flow has no multipart option), which is why auto-routing lives here.

        Args:
            project_uuid: UUID of the I2I project.
            image_paths: Local image file paths to upload.
            max_concurrent: Maximum concurrent uploads / parts (default 5).
            calculate_md5: Whether to compute MD5 hashes for integrity (default False).
            progress_callback: Optional progress callback (index, total, file path).
                Reported for the single-PUT batch; multipart files are reported once each.
            multipart_threshold: Size in bytes above which a file uses multipart upload
                (default 64 MB). Set higher to prefer single PUT, lower to chunk sooner.

        Returns:
            UploadSummary with per-file results and aggregate counts across both paths.
        """
        if max_concurrent < 1:
            raise ValueError("max_concurrent must be at least 1")

        self._logger.info(f"Starting I2I upload of {len(image_paths)} images to project {project_uuid}")
        files_to_upload, valid_paths = await self._prepare_upload_infos(image_paths, calculate_md5)

        # Route each file by size: small -> batched single PUT, large -> multipart.
        small_infos: list[FileUploadInfo] = []
        small_paths: list[Path] = []
        large_paths: list[Path] = []
        for info, path in zip(files_to_upload, valid_paths):
            if path.stat().st_size > multipart_threshold:
                large_paths.append(path)
            else:
                small_infos.append(info)
                small_paths.append(path)

        results: list[UploadResult] = []

        if small_paths:
            upload_request = CreateFilesUploadLinksRequest(files_list=small_infos)
            response_json = await self._make_request(
                "POST",
                f"/i2i/projects/{project_uuid}/get_temporary_upload_links",
                json=upload_request.to_api_dict(),
            )
            upload_links = self._parse_model(response_json, PresignedUrlList, "I2I presigned URL response", UploadError)
            upload_links_map = {url.file_name: url.upload_link for url in upload_links.files_list}
            batch = await self._run_concurrent_uploads(small_paths, upload_links_map, max_concurrent, progress_callback)
            results.extend(batch.results)

        for path in large_paths:
            self._logger.info(f"Routing large file to multipart upload: {path.name}")
            try:
                await self.upload_i2i_file_multipart(project_uuid, path, max_concurrent=max_concurrent)
                results.append(UploadResult(file=str(path), success=True, error=None))
            except Exception as e:
                self._logger.error(f"Multipart upload failed for {path.name}: {e}")
                results.append(UploadResult(file=str(path), success=False, error=str(e)))
            if progress_callback:
                progress_callback(len(results), len(valid_paths), str(path))

        return UploadSummary(
            total=len(results),
            successful=sum(1 for r in results if r.success),
            failed=sum(1 for r in results if not r.success),
            results=results,
        )

    async def get_i2i_upload_link(self, project_uuid: str, file_name: str) -> TemporaryFileUploadData:
        """
        Get a presigned upload link for a single I2I output image.

        Args:
            project_uuid: UUID of the I2I project.
            file_name: Output image file name.

        Returns:
            TemporaryFileUploadData with the file name and presigned upload link.
        """
        self._logger.debug(f"Getting I2I upload link for {file_name} in {project_uuid}")
        response_json = await self._make_request("GET", f"/i2i/projects/{project_uuid}/get_upload_link", params={"file_name": file_name})
        return self._parse_model(response_json, TemporaryFileUploadData, "I2I upload link response", ProjectError)

    # -- Multipart uploads ----------------------------------------------------

    async def create_i2i_multipart_upload(self, project_uuid: str, file_name: str, part_count: int) -> MultipartUploadLinksResponse:
        """
        Initiate a multipart upload and obtain presigned URLs for each part.

        Args:
            project_uuid: UUID of the I2I project.
            file_name: Name of the file to upload.
            part_count: Number of parts (1-10000).

        Returns:
            MultipartUploadLinksResponse with the upload ID, storage key, and part URLs.
        """
        request = CreateMultipartUploadLinksRequest(file_name=file_name, part_count=part_count)
        self._logger.debug(f"Creating multipart upload for {file_name} ({part_count} parts) in {project_uuid}")
        response_json = await self._make_request(
            "POST",
            f"/i2i/projects/{project_uuid}/multipart_uploads",
            json=request.to_api_dict(),
        )
        return self._parse_model(response_json, MultipartUploadLinksResponse, "multipart upload links response", UploadError)

    async def complete_i2i_multipart_upload(self, project_uuid: str, upload_id: str, file_name: str) -> None:
        """
        Complete a multipart upload after all parts have been uploaded.

        Args:
            project_uuid: UUID of the I2I project.
            upload_id: Multipart upload ID from ``create_i2i_multipart_upload``.
            file_name: Name of the uploaded file.
        """
        request = CompleteMultipartUploadRequest(file_name=file_name)
        self._logger.debug(f"Completing multipart upload {upload_id} for {file_name} in {project_uuid}")
        await self._make_request(
            "POST",
            f"/i2i/projects/{project_uuid}/multipart_uploads/{upload_id}/complete",
            json=request.to_api_dict(),
        )

    async def abort_i2i_multipart_upload(self, project_uuid: str, upload_id: str, key: str) -> None:
        """
        Abort an in-progress multipart upload.

        Args:
            project_uuid: UUID of the I2I project.
            upload_id: Multipart upload ID from ``create_i2i_multipart_upload``.
            key: Storage key from ``create_i2i_multipart_upload``.
        """
        # The body is sent via the `content`/`json` of a DELETE request.
        self._logger.debug(f"Aborting multipart upload {upload_id} in {project_uuid}")
        await self._make_request(
            "DELETE",
            f"/i2i/projects/{project_uuid}/multipart_uploads/{upload_id}",
            json={"key": key},
        )

    async def upload_i2i_file_multipart(
        self,
        project_uuid: str,
        file_path: str | Path,
        part_size: int = DEFAULT_MULTIPART_PART_SIZE,
        max_concurrent: int = 4,
    ) -> MultipartUploadLinksResponse:
        """
        Upload a single large file to an I2I project using multipart upload.

        Splits the file into ``part_size`` chunks, uploads each part to its presigned
        URL concurrently, then completes the multipart upload. On any failure the
        upload is aborted before the error is re-raised.

        Args:
            project_uuid: UUID of the I2I project.
            file_path: Local path of the file to upload.
            part_size: Bytes per part (default 64 MB; S3 requires >= 5 MB except the last part).
            max_concurrent: Maximum concurrent part uploads (default 4).

        Returns:
            The MultipartUploadLinksResponse used for the upload.

        Raises:
            UploadError: If the file is missing/invalid or any part fails to upload.
        """
        if max_concurrent < 1:
            raise ValueError("max_concurrent must be at least 1")

        path = Path(file_path)
        if not path.exists() or not path.is_file():
            raise UploadError(f"File not found for multipart upload: {path}")

        file_size = path.stat().st_size
        # S3 allows at most 10000 parts; grow part_size if needed to stay within that.
        if file_size:
            part_size = max(part_size, math.ceil(file_size / 10000))
        part_count = max(1, math.ceil(file_size / part_size))
        self._logger.info(f"Multipart-uploading {path.name} ({file_size} bytes, {part_count} parts) to {project_uuid}")

        links = await self.create_i2i_multipart_upload(project_uuid, path.name, part_count)

        semaphore = asyncio.Semaphore(max_concurrent)

        async def upload_part(http_client: httpx.AsyncClient, part) -> None:
            # Read inside the semaphore so at most max_concurrent chunks are held in
            # memory at once (bounds peak memory to max_concurrent * part_size).
            async with semaphore:
                offset = (part.part_number - 1) * part_size
                async with aiofiles.open(path, "rb") as f:
                    await f.seek(offset)
                    chunk = await f.read(part_size)
                response = await http_client.put(part.upload_url, content=chunk)
                response.raise_for_status()
            self._logger.debug(f"Uploaded part {part.part_number}/{part_count} of {path.name}")

        try:
            # Reuse a single client across all parts so the connection pool is shared.
            async with httpx.AsyncClient(timeout=300.0) as http_client:
                await asyncio.gather(*(upload_part(http_client, part) for part in links.parts))
            await self.complete_i2i_multipart_upload(project_uuid, links.upload_id, path.name)
        except Exception as e:
            self._logger.error(f"Multipart upload of {path.name} failed: {e}; aborting upload {links.upload_id}")
            try:
                await self.abort_i2i_multipart_upload(project_uuid, links.upload_id, links.key)
            except Exception as abort_error:
                self._logger.error(f"Failed to abort multipart upload {links.upload_id}: {abort_error}")
            raise UploadError(f"Multipart upload of {path.name} failed: {e}")

        self._logger.info(f"Completed multipart upload of {path.name}")
        return links

    # -- Editing & downloads --------------------------------------------------

    async def start_i2i_editing(
        self,
        project_uuid: str,
        edit_options: I2IEditOptions | None = None,
    ) -> MessageResponse:
        """
        Trigger image-to-image editing for a project.

        Unlike the standard edit flow, the I2I API exposes no status endpoint, so this
        method only triggers the edit and returns immediately. Completion is signalled
        via ``callback_url`` (if provided in ``edit_options``) or by polling
        ``get_i2i_download_links`` until links are available (it returns
        ``400 "...status In Progress."`` while the edit is still running).

        Args:
            project_uuid: UUID of the I2I project.
            edit_options: Optional I2I editing parameters (hdr_merge, sky_replacement,
                sky_replacement_template_id, perspective_correction, callback_url).

        Returns:
            MessageResponse with a human-readable confirmation ``message``.

        Raises:
            ImagenError: If the response cannot be parsed.
        """
        edit_data = edit_options.to_api_dict() if edit_options else {}
        self._logger.info(f"Triggering I2I edit for project {project_uuid}")
        response_json = await self._make_request(
            "POST",
            f"/i2i/projects/{project_uuid}/edit",
            json=edit_data,
        )
        return self._parse_model(response_json, MessageResponse, "I2I edit trigger response", ProjectError)

    async def get_i2i_download_links(self, project_uuid: str) -> list[str]:
        """
        Get download links for all images in an I2I project.

        Args:
            project_uuid: UUID of the I2I project.

        Returns:
            List of temporary download URLs.

        Raises:
            ProjectError: If the response cannot be parsed.
        """
        self._logger.debug(f"Getting I2I download links for project {project_uuid}")
        response_json = await self._make_request("GET", f"/i2i/projects/{project_uuid}/get_temporary_download_links")
        links_list = self._parse_model(response_json, DownloadLinksList, "I2I download links response", ProjectError)
        links = [link.download_link for link in links_list.files_list]
        self._logger.info(f"Retrieved {len(links)} I2I download links")
        return links

    async def get_i2i_download_link(self, project_uuid: str, file_name: str) -> SingleDownloadLink:
        """
        Get the download link for a single I2I output image.

        Args:
            project_uuid: UUID of the I2I project.
            file_name: Name of the file to download.

        Returns:
            SingleDownloadLink with the temporary ``download_link``.

        Raises:
            ImagenError: If the response cannot be parsed.
        """
        self._logger.debug(f"Getting I2I download link for {file_name} in {project_uuid}")
        response_json = await self._make_request("GET", f"/i2i/projects/{project_uuid}/get_download_link", params={"file_name": file_name})
        return self._parse_model(response_json, SingleDownloadLink, "I2I download link response", ProjectError)
