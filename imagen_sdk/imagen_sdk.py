"""
Imagen AI Python SDK

A streamlined, robust SDK for the Imagen AI API workflow.
"""

import asyncio
import base64
import hashlib
import logging
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import aiofiles
import httpx
from pydantic import ValidationError

from .enums import PhotographyType
from .exceptions import (
    AuthenticationError,
    DownloadError,
    ImagenError,
    ProjectError,
    UploadError,
)
from .models import (
    DownloadLinksResponse,
    EditOptions,
    FileUploadInfo,
    PresignedUrlResponse,
    Profile,
    ProfileApiData,
    ProjectCreationResponse,
    QuickEditResult,
    StatusDetails,
    StatusResponse,
    UploadResult,
    UploadSummary,
)

# Default logger for the SDK
_default_logger = logging.getLogger("imagen_sdk.ImagenClient")

RAW_EXTENSIONS = {
    ".dng",
    ".nef",
    ".cr2",
    ".arw",
    ".nrw",
    ".crw",
    ".srf",
    ".sr2",
    ".orf",
    ".raw",
    ".rw2",
    ".raf",
    ".ptx",
    ".pef",
    ".rwl",
    ".srw",
    ".cr3",
    ".3fr",
    ".fff",
}
JPG_EXTENSIONS = {".jpg", ".jpeg"}
SUPPORTED_FILE_FORMATS = RAW_EXTENSIONS | JPG_EXTENSIONS


# =============================================================================
# IMAGEN CLIENT
# =============================================================================


class ImagenClient:
    """
    Main Imagen AI client for handling the complete photo editing workflow.

    This client provides a full-featured interface to the Imagen AI API, supporting
    project creation, image uploads, AI-powered editing, status monitoring, and
    download management. It handles authentication, error management, and resource
    cleanup automatically.

    Features:
        - Async context manager support for automatic session cleanup
        - Concurrent uploads and downloads with configurable limits
        - Progress tracking callbacks for long-running operations
        - Comprehensive error handling with specific exception types
        - Automatic retry and status polling for editing operations
        - Support for both RAW and JPEG file formats
        - MD5 hash verification for upload integrity
        - Custom logging configuration

    Example:
        Basic usage with context manager:
        ```python
        async with ImagenClient("your_api_key") as client:
            project_uuid = await client.create_project("My Project")
            upload_summary = await client.upload_images(project_uuid, ["photo1.jpg"])
            await client.start_editing(project_uuid, profile_key=5700)
            download_links = await client.get_download_links(project_uuid)
            files = await client.download_files(download_links, "output")
        ```

    Attributes:
        api_key (str): The Imagen AI API key for authentication
        base_url (str): Base URL for the Imagen AI API
        logger (logging.Logger): Logger instance for debugging and monitoring
    """

    _logger = _default_logger

    @classmethod
    def set_logger(cls, logger: logging.Logger, level: int | None = None):
        """
        Set a custom logger and optional logging level for all ImagenClient instances.

        This class method allows you to configure logging for all SDK operations.
        Useful for integrating with existing logging infrastructure or adjusting
        verbosity levels.

        Args:
            logger (logging.Logger): A logging.Logger instance to use for all SDK operations
            level (Optional[int]): Optional logging level (e.g., logging.INFO, logging.DEBUG)

        Example:
            ```python
            import logging

            # Create custom logger
            custom_logger = logging.getLogger("my_app.imagen")
            custom_logger.setLevel(logging.INFO)

            # Set for all client instances
            ImagenClient.set_logger(custom_logger, logging.DEBUG)
            ```
        """
        cls._logger = logger
        if level is not None:
            cls._logger.setLevel(level)

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api-beta.imagen-ai.com/v1",
        logger: logging.Logger | None = None,
        logger_level: int | None = None,
    ):
        """
        Initialize the Imagen AI client.

        Args:
            api_key (str): Your Imagen AI API key obtained from the Imagen AI platform
            base_url (str): Base URL for the API (default: production URL)
            logger (Optional[logging.Logger]): Optional custom logger instance for this client
            logger_level (Optional[int]): Optional logging level for the logger

        Raises:
            ValueError: If api_key is empty or None

        Example:
            ```python
            # Basic initialization
            client = ImagenClient("your_api_key")

            # With custom logging
            import logging
            custom_logger = logging.getLogger("my_app")
            client = ImagenClient("your_api_key", logger=custom_logger, logger_level=logging.DEBUG)
            ```
        """
        if not api_key or not api_key.strip():
            raise ValueError("API key cannot be empty")

        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self._session: httpx.AsyncClient | None = None
        if logger is not None:
            self._logger = logger
            if logger_level is not None:
                self._logger.setLevel(logger_level)
        else:
            self._logger = self.__class__._logger
            if logger_level is not None:
                self._logger.setLevel(logger_level)
        self._logger.debug(f"Initialized ImagenClient with base_url: {self.base_url}")

    def _get_session(self) -> httpx.AsyncClient:
        """
        Get or create an HTTP session with proper authentication headers.

        Returns:
            httpx.AsyncClient: Configured HTTP client with API key authentication
        """
        if self._session is None:
            self._session = httpx.AsyncClient(
                headers={
                    "x-api-key": self.api_key,
                    "User-Agent": "Imagen-Python-SDK/1.0.0",
                },
                timeout=httpx.Timeout(300.0),
            )
            self._logger.debug("Created new HTTP session")
        return self._session

    async def close(self):
        """
        Close the HTTP session and clean up resources.

        This method should be called when you're done with the client to ensure
        proper cleanup of network resources. When using the client as an async
        context manager, this is called automatically.

        Example:
            ```python
            client = ImagenClient("api_key")
            try:
                # Use client
                pass
            finally:
                await client.close()
            ```
        """
        if self._session:
            await self._session.aclose()
            self._session = None
            self._logger.debug("Closed HTTP session")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> dict[str, Any]:
        """
        Make an HTTP request to the API with proper error handling.

        Args:
            method (str): HTTP method (GET, POST, etc.)
            endpoint (str): API endpoint path
            **kwargs: Additional request parameters passed to httpx

        Returns:
            Dict[str, Any]: JSON response as dictionary

        Raises:
            AuthenticationError: If authentication fails (401)
            ImagenError: For other API errors
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        session = self._get_session()

        self._logger.debug(f"Making {method} request to {url}")

        try:
            response = await session.request(method, url, **kwargs)
            self._logger.debug(f"Response status: {response.status_code}")

            # Check for authentication errors first
            if response.status_code == 401:
                self._logger.error("Authentication failed")
                raise AuthenticationError("Invalid API key or unauthorized.")

            # Check for other client or server errors
            elif response.status_code >= 400:
                try:
                    # Try to parse a detailed error message from the JSON response
                    error_data = response.json()
                    message = error_data.get("detail", response.text)
                except Exception:
                    # Fallback to the raw response text if JSON parsing fails
                    message = response.text

                self._logger.error(f"API error {response.status_code}: {message}")
                raise ImagenError(f"API Error ({response.status_code}): {message}")

            # Handle successful responses
            if response.status_code == 204:  # No Content
                return {}
            else:
                return response.json()

        except httpx.RequestError as e:
            self._logger.error(f"Request failed: {e}")
            raise ImagenError(f"Request failed: {e}")

    async def create_project(self, name: str | None = None) -> str:
        """
        Create a new project in the Imagen AI platform.

        Projects are containers for organizing related images and edits. Each project
        can contain either RAW files or JPEG files, but not both types mixed together.
        Project names must be unique across your account.

        Args:
            name (Optional[str]): Optional project name. If not provided, a UUID will be generated.
                                Must be unique across your account.

        Returns:
            str: Project UUID that can be used for subsequent operations

        Raises:
            ProjectError: If project creation fails (e.g., name already exists)
            AuthenticationError: If API key is invalid
            ImagenError: For other API-related errors

        Example:
            ```python
            # Create project with custom name
            project_uuid = await client.create_project("Wedding_Photos_2024")

            # Create project with auto-generated UUID
            project_uuid = await client.create_project()
            ```

        Note:
            Project names must be unique. If a project with the same name already exists,
            this method will raise a ProjectError. Consider using timestamps or client
            identifiers in project names to ensure uniqueness.
        """
        data = {}
        if name:
            data["name"] = name

        self._logger.info(f"Creating project: {name or 'Unnamed'}")
        response_json = await self._make_request("POST", "/projects/", json=data)

        try:
            # Validate the response and extract the UUID
            project_response = ProjectCreationResponse.model_validate(response_json)
            project_uuid = project_response.data.project_uuid
            self._logger.info(f"Created project with UUID: {project_uuid}")
            return project_uuid
        except ValidationError as e:
            self._logger.error(f"Failed to parse project creation response: {e}")
            raise ProjectError(f"Could not parse project creation response: {e}")

    async def upload_images(
        self,
        project_uuid: str,
        image_paths: list[str | Path],
        max_concurrent: int = 5,
        calculate_md5: bool = False,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> UploadSummary:
        """
        Upload images to a project with concurrent processing and progress tracking.

        This method handles the complete upload workflow: validates files, obtains
        presigned URLs from the API, and uploads files concurrently to cloud storage.
        Supports both RAW and JPEG formats, but all files in a single project must
        be of the same type.

        Args:
            project_uuid (str): UUID of the target project from create_project()
            image_paths (List[Union[str, Path]]): List of local image file paths to upload.
                                                All files must be of the same type (RAW or JPEG).
            max_concurrent (int): Maximum concurrent uploads (default: 5).
                                Adjust based on your internet connection speed.
            calculate_md5 (bool): Whether to calculate MD5 hashes for upload verification (default: False).
                                 Enables integrity checking but increases processing time.
            progress_callback (Optional[Callable[[int, int, str], None]]): Optional callback function
                             called during upload progress. Receives (current_index, total_files, current_file_path).

        Returns:
            UploadSummary: Object containing upload statistics and detailed results:
                - total: Total number of files attempted
                - successful: Number of successfully uploaded files
                - failed: Number of failed uploads
                - results: List of UploadResult objects with details for each file

        Raises:
            UploadError: If no valid files found or upload fails
            ValueError: If max_concurrent < 1
            ProjectError: If project doesn't exist or is invalid
            AuthenticationError: If API key is invalid

        Example:
            ```python
            def show_progress(current, total, filename):
                percent = (current / total) * 100
                print(f"Uploading: {percent:.1f}% - {filename}")

            upload_summary = await client.upload_images(
                project_uuid="project-123",
                image_paths=["photo1.cr2", "photo2.nef", "photo3.dng"],
                max_concurrent=3,  # Slower connection
                calculate_md5=True,  # Enable integrity checking
                progress_callback=show_progress
            )

            print(f"Uploaded {upload_summary.successful}/{upload_summary.total} files")
            ```

        Note:
            - All files in a project must be the same type (all RAW or all JPEG)
            - Larger max_concurrent values may improve speed but use more bandwidth
            - MD5 calculation adds processing time but ensures upload integrity
            - Invalid file paths are automatically skipped and logged
        """
        if max_concurrent < 1:
            raise ValueError("max_concurrent must be at least 1")

        self._logger.info(f"Starting upload of {len(image_paths)} images to project {project_uuid}")

        files_to_upload: list[FileUploadInfo] = []
        valid_paths: list[Path] = []

        for path_str in image_paths:
            path = Path(path_str)
            if path.exists() and path.is_file():
                md5_hash = await self._calculate_md5(path) if calculate_md5 else None
                files_to_upload.append(FileUploadInfo(file_name=path.name, md5=md5_hash))
                valid_paths.append(path)
            else:
                self._logger.warning(f"Skipping invalid path: {path}")

        if not valid_paths:
            raise UploadError("No valid local files found to upload.")

        # Get presigned URLs from the API
        upload_payload = {"files_list": [f.model_dump(exclude_none=True) for f in files_to_upload]}
        response_json = await self._make_request(
            "POST",
            f"/projects/{project_uuid}/get_temporary_upload_links",
            json=upload_payload,
        )

        try:
            upload_links_response = PresignedUrlResponse.model_validate(response_json)
        except ValidationError as e:
            raise UploadError(f"Could not parse presigned URL response: {e}")

        # Create a mapping of filenames to their upload URLs for easy access
        upload_links_map = {url.file_name: url.upload_link for url in upload_links_response.data.files_list}

        # Inner function to handle the upload of a single file
        async def upload_single_file(file_path: Path, index: int) -> UploadResult:
            # Report progress before starting the upload
            if progress_callback:
                progress_callback(index, len(valid_paths), str(file_path))

            try:
                upload_url = upload_links_map.get(file_path.name)
                if not upload_url:
                    raise UploadError(f"No upload link found for {file_path.name}")

                await self._upload_to_s3(file_path, upload_url)
                self._logger.debug(f"Successfully uploaded: {file_path.name}")
                return UploadResult(file=str(file_path), success=True, error=None)
            except Exception as e:
                self._logger.error(f"Failed to upload {file_path.name}: {e}")
                return UploadResult(file=str(file_path), success=False, error=str(e))
            finally:
                # Report progress after the upload attempt is complete
                if progress_callback:
                    progress_callback(index + 1, len(valid_paths), str(file_path))

        # Create and run upload tasks concurrently with semaphore
        semaphore = asyncio.Semaphore(max_concurrent)

        async def bounded_upload(file_path: Path, index: int) -> UploadResult:
            async with semaphore:
                return await upload_single_file(file_path, index)

        tasks = [bounded_upload(path, i) for i, path in enumerate(valid_paths)]
        results: list[UploadResult] = await asyncio.gather(*tasks)

        summary = UploadSummary(
            total=len(valid_paths),
            successful=sum(1 for r in results if r.success),
            failed=sum(1 for r in results if not r.success),
            results=results,
        )

        self._logger.info(f"Upload completed: {summary.successful}/{summary.total} successful")
        return summary

    async def start_editing(
        self,
        project_uuid: str,
        profile_key: int,
        photography_type: PhotographyType | None = None,
        edit_options: EditOptions | None = None,
    ) -> StatusDetails:
        """
        Start AI-powered editing of images in a project and wait for completion.

        This method initiates the editing process using your trained AI profile and
        optional editing parameters. It automatically polls the status until the
        editing is complete or fails. The AI applies your learned editing style
        consistently across all images in the project.

        Args:
            project_uuid (str): UUID of the project containing uploaded images
            profile_key (int): Profile ID representing your trained editing style.
                              Obtain this from the Imagen AI app after training your profile.
            photography_type (Optional[PhotographyType]): Optional photography type for optimization.
                                                        Helps the AI understand the image context.
                                                        Options: PORTRAITS, WEDDING, EVENTS, etc.
            edit_options (Optional[EditOptions]): Optional editing parameters to customize the process:
                                                 - crop: Auto-crop images
                                                 - straighten: Auto-straighten horizons
                                                 - portrait_crop: Portrait-specific cropping
                                                 - smooth_skin: Skin smoothing for portraits
                                                 - hdr_merge: HDR bracket merging

        Returns:
            StatusDetails: Final status information when editing completes:
                          - status: "Completed" or "Failed"
                          - progress: Final progress percentage
                          - details: Additional status information

        Raises:
            ProjectError: If editing fails or project doesn't exist
            AuthenticationError: If API key is invalid
            ImagenError: For other API-related errors

        Example:
            ```python
            from imagen_sdk import PhotographyType, EditOptions

            # Basic editing
            status = await client.start_editing(
                project_uuid="project-123",
                profile_key=5700
            )

            # Advanced editing with options
            edit_options = EditOptions(
                crop=True,
                straighten=True,
                portrait_crop=True,
                smooth_skin=True
            )

            status = await client.start_editing(
                project_uuid="project-123",
                profile_key=5700,
                photography_type=PhotographyType.WEDDING,
                edit_options=edit_options
            )
            ```

        Note:
            - This method blocks until editing completes (can take several minutes)
            - Progress is logged automatically during the process
            - Profile keys are obtained from training in the Imagen AI app
            - The AI generates XMP files compatible with Lightroom/Photoshop
        """
        edit_data: dict[str, Any] = {"profile_key": int(profile_key)}
        if photography_type:
            edit_data["photography_type"] = photography_type.value
        if edit_options:
            edit_data.update(edit_options.to_api_dict())

        self._logger.info(f"Starting editing for project {project_uuid} with profile {profile_key}")
        # The Imagen AI API endpoint for starting an edit requires a POST request
        # but does not expect a 'Content-Type' header for the JSON payload, which
        # is non-standard. httpx automatically adds this header, so we explicitly
        # override it to be empty to comply with the API's specific requirement.
        await self._make_request(
            "POST",
            f"/projects/{project_uuid}/edit",
            json=edit_data,
            headers={"Content-Type": ""},
        )
        return await self._wait_for_completion(project_uuid, "edit")

    async def get_download_links(self, project_uuid: str) -> list[str]:
        """
        Get download links for edited images (XMP files).

        After editing completes, this method retrieves temporary download URLs for
        the generated XMP edit files. These XMP files contain Lightroom-compatible
        edit instructions that can be applied to your original images.

        Args:
            project_uuid (str): UUID of the project with completed editing

        Returns:
            List[str]: List of temporary download URLs for XMP files.
                      URLs are valid for a limited time and should be used promptly.

        Raises:
            ProjectError: If getting links fails or project doesn't exist
            AuthenticationError: If API key is invalid
            ImagenError: For other API-related errors

        Example:
            ```python
            # Get download links after editing completes
            download_links = await client.get_download_links("project-123")
            print(f"Ready to download {len(download_links)} XMP files")

            # Download the files
            local_files = await client.download_files(download_links, "my_edits")
            ```

        Note:
            - Download URLs are temporary and expire after a certain time
            - XMP files can be opened in Lightroom, Photoshop, or other compatible software
            - The original image files are not modified; XMP files contain edit instructions
        """
        self._logger.debug(f"Getting download links for project {project_uuid}")
        response_json = await self._make_request("GET", f"/projects/{project_uuid}/edit/get_temporary_download_links")
        try:
            # Validate the full response structure
            links_response = DownloadLinksResponse.model_validate(response_json)
            # Access the list via .data and extract just the URL strings
            links = [link.download_link for link in links_response.data.files_list]
            self._logger.info(f"Retrieved {len(links)} download links")
            return links
        except ValidationError as e:
            raise ProjectError(f"Could not parse download links response: {e}")

    async def export_project(self, project_uuid: str) -> StatusDetails:
        """
        Export project images to final JPEG format and wait for completion.

        This method converts the AI-edited images to final JPEG files that can be
        delivered directly to clients. The export process applies all edits and
        generates high-quality JPEG files ready for use.

        Args:
            project_uuid (str): UUID of the project with completed editing

        Returns:
            StatusDetails: Final status information when export completes:
                          - status: "Completed" or "Failed"
                          - progress: Final progress percentage
                          - details: Additional status information

        Raises:
            ProjectError: If export fails or project doesn't exist
            AuthenticationError: If API key is invalid
            ImagenError: For other API-related errors

        Example:
            ```python
            # Export after editing completes
            await client.start_editing(project_uuid, profile_key=5700)

            # Export to JPEG
            export_status = await client.export_project(project_uuid)
            print(f"Export completed with status: {export_status.status}")

            # Get export download links
            export_links = await client.get_export_links(project_uuid)
            ```

        Note:
            - This method blocks until export completes
            - Export generates final JPEG files ready for delivery
            - Progress is logged automatically during the process
            - Use get_export_links() after this completes to download JPEG files
        """
        self._logger.info(f"Starting export for project {project_uuid}")
        await self._make_request("POST", f"/projects/{project_uuid}/export")
        return await self._wait_for_completion(project_uuid, "export")

    async def get_export_links(self, project_uuid: str) -> list[str]:
        """
        Get download links for exported JPEG images.

        After export completes, this method retrieves temporary download URLs for
        the final JPEG files. These are the client-ready, fully processed images
        with all AI edits applied.

        Args:
            project_uuid (str): UUID of the project with completed export

        Returns:
            List[str]: List of temporary download URLs for JPEG files.
                      URLs are valid for a limited time and should be used promptly.

        Raises:
            ProjectError: If getting links fails or project doesn't exist
            AuthenticationError: If API key is invalid
            ImagenError: For other API-related errors

        Example:
            ```python
            # Get export links after export completes
            export_links = await client.get_export_links("project-123")
            print(f"Ready to download {len(export_links)} JPEG files")

            # Download the exported files
            jpeg_files = await client.download_files(export_links, "client_delivery")
            ```

        Note:
            - Download URLs are temporary and expire after a certain time
            - JPEG files are final, client-ready images
            - These files have all AI edits applied and are ready for delivery
        """
        self._logger.debug(f"Getting export links for project {project_uuid}")
        response_json = await self._make_request("GET", f"/projects/{project_uuid}/export/get_temporary_download_links")
        try:
            # Validate the full response structure
            links_response = DownloadLinksResponse.model_validate(response_json)
            # Access the list via .data and extract just the URL strings
            links = [link.download_link for link in links_response.data.files_list]
            self._logger.info(f"Retrieved {len(links)} export links")
            return links
        except ValidationError as e:
            raise ProjectError(f"Could not parse export links response: {e}")

    async def download_files(
        self,
        download_links: list[str],
        output_dir: str | Path = "downloads",
        max_concurrent: int = 5,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> list[str]:
        """
        Download files from provided URLs with concurrent processing and progress tracking.

        This method handles downloading multiple files concurrently from the temporary
        URLs provided by get_download_links() or get_export_links(). It automatically
        creates the output directory and manages concurrent downloads for optimal performance.

        Args:
            download_links (List[str]): List of download URLs from get_download_links() or get_export_links()
            output_dir (Union[str, Path]): Directory to save downloaded files (default: "downloads").
                                         Directory will be created if it doesn't exist.
            max_concurrent (int): Maximum number of concurrent downloads (default: 5).
                                Adjust based on your internet connection speed.
            progress_callback (Optional[Callable[[int, int, str], None]]): Optional callback function
                             called during download progress. Receives (current_index, total_files, status_message).

        Returns:
            List[str]: List of local file paths where files were successfully downloaded

        Raises:
            DownloadError: If no files could be downloaded or output directory issues
            ValueError: If max_concurrent < 1
            ImagenError: For network-related download failures

        Example:
            ```python
            def download_progress(current, total, message):
                percent = (current / total) * 100
                print(f"Download: {percent:.1f}% - {message}")

            # Download XMP files
            download_links = await client.get_download_links(project_uuid)
            xmp_files = await client.download_files(
                download_links,
                output_dir="edited_xmps",
                max_concurrent=3,
                progress_callback=download_progress
            )

            # Download JPEG files
            export_links = await client.get_export_links(project_uuid)
            jpeg_files = await client.download_files(
                export_links,
                output_dir="final_jpegs",
                progress_callback=download_progress
            )

            print(f"Downloaded {len(xmp_files)} XMP and {len(jpeg_files)} JPEG files")
            ```

        Note:
            - Downloads are performed concurrently for better performance
            - Failed downloads are logged but don't stop other downloads
            - Filenames are automatically extracted from URLs when possible
            - Progress callback is called before and after each file download
            - Output directory is created automatically if it doesn't exist
        """
        if max_concurrent < 1:
            raise ValueError("max_concurrent must be at least 1")

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        if not download_links:
            raise DownloadError("No download links provided.")

        self._logger.info(f"Starting download of {len(download_links)} files to {output_path}")
        semaphore = asyncio.Semaphore(max_concurrent)

        async def download_single_file(url: str, index: int) -> str | None:
            """Download a single file and return the local path."""
            async with semaphore:
                if progress_callback:
                    progress_callback(index, len(download_links), f"Starting download {index + 1}")

                try:
                    # Extract filename from URL or generate one
                    filename = self._extract_filename_from_url(url, index)
                    local_path = output_path / filename

                    async with httpx.AsyncClient(timeout=300.0) as client:
                        response = await client.get(url)
                        response.raise_for_status()

                        # Write file to disk
                        async with aiofiles.open(local_path, "wb") as f:
                            await f.write(response.content)

                    if progress_callback:
                        progress_callback(index + 1, len(download_links), f"Downloaded {filename}")

                    self._logger.debug(f"Downloaded: {filename}")
                    return str(local_path)

                except Exception as e:
                    self._logger.error(f"Failed to download file {index + 1}: {e}")
                    if progress_callback:
                        progress_callback(
                            index + 1,
                            len(download_links),
                            f"Failed to download file {index + 1}: {e}",
                        )
                    return None

        # Create download tasks
        tasks = [download_single_file(url, i) for i, url in enumerate(download_links)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter successful downloads
        successful_downloads = [path for path in results if isinstance(path, str) and path is not None]

        if not successful_downloads:
            raise DownloadError("Failed to download any files.")

        self._logger.info(f"Downloaded {len(successful_downloads)}/{len(download_links)} files successfully")
        return successful_downloads

    @staticmethod
    def _extract_filename_from_url(url: str, index: int) -> str:
        """
        Extract filename from URL or generate a default name.

        Args:
            url: The download URL
            index: Index for generating default names

        Returns:
            Filename to use for the downloaded file
        """
        try:
            # Try to extract filename from URL
            parsed_url = urlparse(url)

            # Get the path and extract filename
            path = unquote(parsed_url.path)
            filename = Path(path).name

            # If we got a valid filename with extension, use it
            if filename and "." in filename and len(filename) > 1:
                return filename

        except Exception as e:
            _default_logger.debug(f"Failed to extract filename from {url}: {e}")

        # Fallback to generated filename
        return f"imagen_edited_{index + 1:05d}.jpg"

    async def get_profiles(self) -> list[Profile]:
        """
        Get available editing profiles from your Imagen AI account.

        Profiles represent your trained AI editing styles. Each profile is created
        by training the AI with your manually edited photos in the Imagen AI app.
        You'll use the profile_key from these profiles in editing operations.

        Returns:
            List[Profile]: List of available profiles with details:
                          - profile_key: Unique identifier for use in editing
                          - profile_name: Human-readable name of the profile
                          - profile_type: Type/tier of the profile
                          - image_type: Whether profile works with "RAW" or "JPG" files

        Raises:
            ImagenError: If getting profiles fails
            AuthenticationError: If API key is invalid

        Example:
            ```python
            profiles = await client.get_profiles()
            for profile in profiles:
                print(f"Profile: {profile.profile_name}")
                print(f"  Key: {profile.profile_key}")
                print(f"  Type: {profile.image_type}")
                print(f"  Tier: {profile.profile_type}")

            # Use a specific profile for editing
            wedding_profile = next(p for p in profiles if "wedding" in p.profile_name.lower())
            await client.start_editing(project_uuid, wedding_profile.profile_key)
            ```

        Note:
            - Profiles are created by training in the Imagen AI app
            - Each profile works with either RAW or JPEG files, not both
            - Profile keys are required for all editing operations
            - Profile names and types help you identify the right style for your project
        """
        self._logger.debug("Getting available profiles")
        response_json = await self._make_request("GET", "/profiles")
        try:
            # Validate the full response structure
            api_data = ProfileApiData.model_validate(response_json)
            # Return the nested list of profiles
            profiles = api_data.data.profiles
            self._logger.info(f"Retrieved {len(profiles)} profiles")
            return profiles
        except ValidationError as e:
            raise ImagenError(f"Failed to parse profiles from API response: {e}")

    @staticmethod
    async def _calculate_md5(file_path: Path) -> str:
        """
        Calculate MD5 hash of a file for integrity verification.

        Args:
            file_path: Path to the file

        Returns:
            Base64-encoded MD5 hash string
        """
        async with aiofiles.open(file_path, "rb") as file:
            data = await file.read()
        md5_digest = hashlib.md5(data).digest()
        base64_encoded_md5 = base64.b64encode(md5_digest).decode("utf-8")
        return base64_encoded_md5

    @staticmethod
    async def _upload_to_s3(file_path: Path, upload_url: str):
        """
        Upload a file to S3 using a presigned URL.

        Args:
            file_path: Local file path
            upload_url: Presigned S3 URL

        Raises:
            UploadError: If upload fails
        """
        try:
            async with aiofiles.open(file_path, "rb") as f:
                content = await f.read()

            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.put(upload_url, content=content)
                response.raise_for_status()
        except Exception as e:
            raise UploadError(f"Failed to upload {file_path.name}: {e}")

    async def _wait_for_completion(self, project_uuid: str, operation: str) -> StatusDetails:
        """
        Poll the status of an operation until it's completed or failed.

        Args:
            project_uuid: UUID of the project
            operation: Operation type ('edit' or 'export')

        Returns:
            Final status details

        Raises:
            ProjectError: If operation fails or status parsing fails
        """
        check_interval, max_interval = 10.0, 60.0
        start_time = time.time()
        max_wait_time = 72000  # 20 hours max wait time

        self._logger.info(f"⏳ Waiting for {operation} to complete... (will check status periodically)")

        while True:
            elapsed = time.time() - start_time

            # Check for timeout
            if elapsed > max_wait_time:
                raise ProjectError(f"{operation.title()} timed out after {max_wait_time} seconds")

            endpoint = f"/projects/{project_uuid}/{operation}/status"
            status_json = await self._make_request("GET", endpoint)

            try:
                # Validate the full response, including the 'data' wrapper
                status_response = StatusResponse.model_validate(status_json)
            except ValidationError as e:
                raise ProjectError(f"Could not parse status response for {operation}: {e}")

            # Access the actual status details through the .data attribute
            status_details = status_response.data
            elapsed_int = int(elapsed)

            # Construct a progress string if progress data is available
            progress_str = f" ({status_details.progress:.1f}%)" if status_details.progress is not None else ""
            self._logger.info(f"  - Status: {status_details.status}{progress_str} (elapsed: {elapsed_int}s)")

            if status_details.status == "Completed":
                self._logger.info(f"✅ {operation.title()} completed successfully!")
                return status_details  # Return the inner details object

            if status_details.status == "Failed":
                error_msg = f"{operation.title()} failed."
                if status_details.details:
                    error_msg += f" Details: {status_details.details}"
                raise ProjectError(error_msg)

            await asyncio.sleep(check_interval)
            check_interval = min(check_interval * 1.2, max_interval)

    @property
    def logger(self) -> logging.Logger:
        """
        Get the logger instance used by this client.

        Returns:
            logging.Logger: The logger instance for this client
        """
        return self._logger


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


async def get_profiles(api_key: str, base_url: str = "https://api-beta.imagen-ai.com/v1") -> list[Profile]:
    """
    Get available editing profiles using a standalone function.

    This is a convenience function that creates a temporary client to fetch profiles.
    Use this when you just need to check available profiles without creating a full client.

    Args:
        api_key (str): Your Imagen AI API key
        base_url (str): API base URL (default: production URL)

    Returns:
        List[Profile]: List of available profiles with their details

    Raises:
        ImagenError: If getting profiles fails
        AuthenticationError: If API key is invalid

    Example:
        ```python
        from imagen_sdk import get_profiles

        # Quick profile check
        profiles = await get_profiles("your_api_key")
        for profile in profiles:
            print(f"{profile.profile_name} (key: {profile.profile_key})")
        ```
    """
    async with ImagenClient(api_key, base_url) as client:
        return await client.get_profiles()


def check_files_match_profile_type(image_paths: list[str | Path], profile: Profile, logger: logging.Logger):
    """
    Validate that all files match the profile's image_type (RAW or JPG).

    This utility function ensures file type consistency before upload. Projects can
    contain either all RAW files or all JPEG files, but not a mix. This validation
    prevents upload errors and provides clear error messages.

    Args:
        image_paths (List[Union[str, Path]]): List of image file paths to validate
        profile (Profile): Profile object with image_type specification
        logger (logging.Logger): Logger for error reporting

    Raises:
        UploadError: If files don't match profile type or are mixed types

    Example:
        ```python
        from imagen_sdk import get_profile, check_files_match_profile_type
        import logging

        # Get profile and validate files
        profile = await get_profile("api_key", profile_key=5700)
        files = ["photo1.cr2", "photo2.nef", "photo3.dng"]  # All RAW

        logger = logging.getLogger("my_app")
        check_files_match_profile_type(files, profile, logger)

        # Now safe to upload - all files match profile type
        ```

    Note:
        - RAW profiles only accept RAW files (.cr2, .nef, .dng, etc.)
        - JPG profiles only accept JPEG files (.jpg, .jpeg)
        - Mixed file types will raise an UploadError with specific details
        - This check should be done before calling upload_images()
    """
    if profile.image_type.upper() == "RAW":
        type_label = "RAW"
    elif profile.image_type.upper() == "JPG":
        type_label = "JPG"
    else:
        raise UploadError(f"Profile type '{profile.image_type}' is not supported for file validation.")

    raw_files = []
    jpg_files = []
    invalid_files = []
    for path in image_paths:
        ext = Path(path).suffix.lower()
        if ext in RAW_EXTENSIONS:
            raw_files.append(str(path))
        elif ext in JPG_EXTENSIONS:
            jpg_files.append(str(path))
        else:
            invalid_files.append(str(path))

    # Check for mix or mismatch
    if type_label == "RAW":
        if jpg_files:
            logger.error(f"RAW profile cannot be used with JPG files: {jpg_files}")
            raise UploadError(f"RAW profile cannot be used with JPG files: {jpg_files}")
        if invalid_files:
            logger.error(f"RAW profile cannot be used with unsupported files: {invalid_files}")
            raise UploadError(f"RAW profile cannot be used with unsupported files: {invalid_files}")
    elif type_label == "JPG":
        if raw_files:
            logger.error(f"JPG profile cannot be used with RAW files: {raw_files}")
            raise UploadError(f"JPG profile cannot be used with RAW files: {raw_files}")
        if invalid_files:
            logger.error(f"JPG profile cannot be used with unsupported files: {invalid_files}")
            raise UploadError(f"JPG profile cannot be used with unsupported files: {invalid_files}")


async def quick_edit(
    api_key: str,
    profile_key: int,
    image_paths: list[str | Path],
    project_name: str | None = None,
    photography_type: PhotographyType | None = None,
    export: bool = False,
    edit_options: EditOptions | None = None,
    download: bool = False,
    download_dir: str | Path = "downloads",
    export_download_dir: str | Path | None = None,
    base_url: str = "https://api-beta.imagen-ai.com/v1",
    logger: logging.Logger | None = None,
    logger_level: int | None = None,
) -> QuickEditResult:
    """
    Complete one-line workflow: create project, upload, edit, and optionally export and download.

    This is the main convenience function that handles the entire Imagen AI workflow
    in a single call. It's perfect for simple automation scripts and batch processing.
    The function automatically handles file validation, project creation, uploads,
    editing, and optional export/download steps.

    Args:
        api_key (str): Your Imagen AI API key
        profile_key (int): Profile ID to use for editing (from get_profiles())
        image_paths (List[Union[str, Path]]): List of local image file paths to upload.
                                            All files must be same type (RAW or JPEG).
        project_name (Optional[str]): Optional name for the project. Must be unique.
        photography_type (Optional[PhotographyType]): Optional photography type for AI optimization.
                                                     e.g., PhotographyType.WEDDING, PhotographyType.PORTRAITS
        export (bool): Whether to export final JPEG files (default: False)
        edit_options (Optional[EditOptions]): Optional editing parameters for customization
        download (bool): Whether to automatically download edited files (default: False)
        download_dir (Union[str, Path]): Directory to save downloaded files (default: "downloads")
        export_download_dir (Optional[Union[str, Path]]): Directory for exported files.
                                                         Defaults to a subdirectory inside 'download_dir'.
        base_url (str): API base URL (default: production URL)
        logger (Optional[logging.Logger]): Optional custom logger for workflow logging
        logger_level (Optional[int]): Optional logging level

    Returns:
        QuickEditResult: Complete result object containing:
                        - project_uuid: UUID of created project
                        - upload_summary: Upload statistics and results
                        - download_links: URLs for downloading XMP files
                        - export_links: URLs for downloading JPEG files (if export=True)
                        - downloaded_files: Local paths of downloaded XMP files (if download=True)
                        - exported_files: Local paths of downloaded JPEG files (if export=True and download=True)

    Raises:
        UploadError: If no files uploaded successfully or file type validation fails
        ProjectError: If project creation, editing, or export fails
        AuthenticationError: If API key is invalid
        DownloadError: If download=True but download fails
        Various other errors from individual operations

    Example:
        ```python
        from imagen_sdk import quick_edit, EditOptions, PhotographyType

        # Advanced workflow with custom export directory
        result = await quick_edit(
            api_key="your_api_key",
            profile_key=5700,
            image_paths=["photo1.cr2", "photo2.nef"],
            export=True,
            download=True,
            download_dir="wedding_delivery",
            export_download_dir="wedding_delivery/final_jpegs"
        )
        ```

    Note:
        - All files must be the same type (all RAW or all JPEG)
        - Project names must be unique across your account
        - Setting download=True automatically downloads both XMP and JPEG files (if export=True)
        - This function handles all error cases and provides detailed error messages
    """
    _logger = logger if logger is not None else _default_logger
    if logger_level is not None:
        _logger.setLevel(logger_level)
    _logger.info(f"Starting quick_edit workflow with {len(image_paths)} images")

    async with ImagenClient(api_key, base_url, logger=logger, logger_level=logger_level) as client:
        # --- Profile and file type validation ---
        profile = await get_profile(api_key, profile_key, base_url)
        _logger.info(f"Using profile: {profile.profile_name} (type: {profile.image_type})")

        # Use the helper for file type validation
        check_files_match_profile_type(image_paths, profile, _logger)

        # --- Continue with workflow ---
        project_uuid = await client.create_project(project_name)
        upload_summary = await client.upload_images(project_uuid, image_paths)

        if upload_summary.successful == 0:
            raise UploadError("quick_edit failed because no files were uploaded successfully.")

        await client.start_editing(project_uuid, profile_key, photography_type, edit_options=edit_options)
        download_links = await client.get_download_links(project_uuid)

        export_links = None
        downloaded_files = None
        exported_files = None

        # Handle export with proper error propagation
        if export:
            try:
                await client.export_project(project_uuid)
                export_links = await client.get_export_links(project_uuid)
            except Exception as e:
                # Re-raise any export-related errors (ProjectError, etc.)
                _logger.error(f"Export failed: {e}")
                raise

        # Handle downloads with proper error propagation
        if download:
            try:
                downloaded_files = await client.download_files(download_links, download_dir)
                if export_links:
                    # Use the configurable export directory, or default to a sub-directory
                    final_export_dir = export_download_dir or (Path(download_dir) / "exported")
                    exported_files = await client.download_files(export_links, final_export_dir)
            except Exception as e:
                # Re-raise any download-related errors (DownloadError, etc.)
                _logger.error(f"Download failed: {e}")
                raise

        result = QuickEditResult(
            project_uuid=project_uuid,
            upload_summary=upload_summary,
            download_links=download_links,
            export_links=export_links,
            downloaded_files=downloaded_files,
            exported_files=exported_files,
        )

        _logger.info(f"Quick edit workflow completed successfully for project {project_uuid}")
        return result


async def get_profile(api_key: str, profile_key: int, base_url: str = "https://api-beta.imagen-ai.com/v1") -> Profile:
    """
    Fetch a specific profile by its key.

    This convenience function retrieves a single profile by its profile_key.
    Useful for validating profile keys and getting profile details before editing.

    Args:
        api_key (str): Your Imagen AI API key
        profile_key (int): The specific profile key to retrieve
        base_url (str): API base URL (default: production URL)

    Returns:
        Profile: The profile object with details like name, type, and image_type

    Raises:
        UploadError: If profile with the given key is not found
        ImagenError: If API request fails
        AuthenticationError: If API key is invalid

    Example:
        ```python
        from imagen_sdk import get_profile

        # Get specific profile details
        profile = await get_profile("your_api_key", 5700)
        print(f"Profile: {profile.profile_name}")
        print(f"Works with: {profile.image_type} files")

        # Use profile info for validation
        if profile.image_type == "RAW":
            print("This profile works with RAW files (.cr2, .nef, etc.)")
        else:
            print("This profile works with JPEG files (.jpg)")
        ```
    """
    profiles = await get_profiles(api_key, base_url)
    for p in profiles:
        if p.profile_key == profile_key:
            return p
    raise UploadError(f"Profile with key {profile_key} not found.")


if __name__ == "__main__":
    # This file is intended to be used as a library.
    # See the 'examples.py' file for usage demonstrations.
    _default_logger.info("Imagen AI SDK loaded. See examples.py for usage.")
