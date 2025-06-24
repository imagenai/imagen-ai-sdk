"""
Imagen AI Python SDK (Pydantic Edition)

A streamlined, robust SDK for the Imagen AI API workflow.
"""

import asyncio
import hashlib
import logging
import time
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any, Union, Callable
from urllib.parse import urlparse, unquote

import aiofiles
import httpx
from pydantic import BaseModel, ValidationError, Field

# Configure logging
logger = logging.getLogger(__name__)

# =============================================================================
# ENUMS
# =============================================================================

class PhotographyType(Enum):
    """Photography types for AI optimization (from API spec)."""
    NO_TYPE = "NO_TYPE"
    OTHER = "OTHER"
    PORTRAITS = "PORTRAITS"
    WEDDING = "WEDDING"
    REAL_ESTATE = "REAL_ESTATE"
    LANDSCAPE_NATURE = "LANDSCAPE_NATURE"
    EVENTS = "EVENTS"
    FAMILY_NEWBORN = "FAMILY_NEWBORN"
    BOUDOIR = "BOUDOIR"
    SPORTS = "SPORTS"


class CropAspectRatio(Enum):
    """Crop aspect ratios (from API spec)."""
    RATIO_2X3 = "2X3"
    RATIO_4X5 = "4X5"
    RATIO_5X7 = "5X7"


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class Profile(BaseModel):
    """Represents an editing profile."""
    image_type: str = Field(..., description="Type of images this profile handles")
    profile_key: int = Field(..., description="Unique identifier for the profile")
    profile_name: str = Field(..., description="Human-readable name of the profile")
    profile_type: str = Field(..., description="Type/tier of the profile")


class ProfileApiResponse(BaseModel):
    """API response wrapper for profiles list."""
    profiles: List[Profile]


class ProfileApiData(BaseModel):
    """Top-level API response for profiles endpoint."""
    data: ProfileApiResponse


class ProjectCreationResponseData(BaseModel):
    """Project creation response data."""
    project_uuid: str = Field(..., description="Unique identifier for the created project")


class ProjectCreationResponse(BaseModel):
    """API response for project creation."""
    data: ProjectCreationResponseData


class FileUploadInfo(BaseModel):
    """Information about a file to be uploaded."""
    file_name: str = Field(..., description="Name of the file")
    md5: Optional[str] = Field(None, description="MD5 hash of the file content")


class PresignedUrl(BaseModel):
    """Presigned URL for uploading a file."""
    file_name: str = Field(..., description="Name of the file")
    upload_link: str = Field(..., description="Presigned URL for upload")


class PresignedUrlList(BaseModel):
    """List of presigned URLs."""
    files_list: List[PresignedUrl]


class PresignedUrlResponse(BaseModel):
    """API response containing presigned URLs."""
    data: PresignedUrlList


class EditOptions(BaseModel):
    """Options for editing operations."""
    crop: Optional[bool] = Field(None, description="Whether to apply cropping")
    straighten: Optional[bool] = Field(None, description="Whether to straighten the image")
    hdr_merge: Optional[bool] = Field(None, description="Whether to apply HDR merge")
    portrait_crop: Optional[bool] = Field(None, description="Whether to apply portrait cropping")
    smooth_skin: Optional[bool] = Field(None, description="Whether to apply skin smoothing")

    def to_api_dict(self) -> Dict[str, Any]:
        """Convert to dictionary excluding unset values."""
        return self.model_dump(exclude_none=True)


class StatusDetails(BaseModel):
    """Represents the core details of a status check."""
    status: str = Field(..., description="Current status of the operation")
    progress: Optional[float] = Field(None, description="Progress percentage (0-100)")
    details: Optional[str] = Field(None, description="Additional status details")


class StatusResponse(BaseModel):
    """Represents the top-level API response for a status check."""
    data: StatusDetails


class DownloadLink(BaseModel):
    """Represents a download link for a single file."""
    file_name: str = Field(..., description="Name of the file")
    download_link: str = Field(..., description="URL to download the file")


class DownloadLinksList(BaseModel):
    """Represents the list of download links inside the 'data' object."""
    files_list: List[DownloadLink]


class DownloadLinksResponse(BaseModel):
    """Represents the top-level API response for download links."""
    data: DownloadLinksList


class UploadResult(BaseModel):
    """Result of uploading a single file."""
    file: str = Field(..., description="Path of the uploaded file")
    success: bool = Field(..., description="Whether the upload was successful")
    error: Optional[str] = Field(None, description="Error message if upload failed")


class UploadSummary(BaseModel):
    """Summary of upload operation results."""
    total: int = Field(..., description="Total number of files attempted")
    successful: int = Field(..., description="Number of successfully uploaded files")
    failed: int = Field(..., description="Number of failed uploads")
    results: List[UploadResult] = Field(..., description="Detailed results for each file")


class QuickEditResult(BaseModel):
    """Result of a complete quick edit workflow."""
    project_uuid: str = Field(..., description="UUID of the created project")
    upload_summary: UploadSummary = Field(..., description="Summary of upload results")
    download_links: List[str] = Field(..., description="URLs to download edited images")
    export_links: Optional[List[str]] = Field(None, description="URLs to download exported images")
    downloaded_files: Optional[List[str]] = Field(None, description="Local paths of downloaded edited files")
    exported_files: Optional[List[str]] = Field(None, description="Local paths of downloaded exported files")


# =============================================================================
# EXCEPTIONS
# =============================================================================

class ImagenError(Exception):
    """Base exception for Imagen SDK errors."""
    pass


class AuthenticationError(ImagenError):
    """Raised when authentication fails."""
    pass


class ProjectError(ImagenError):
    """Raised when project operations fail."""
    pass


class UploadError(ImagenError):
    """Raised when upload operations fail."""
    pass


class DownloadError(ImagenError):
    """Raised when download operations fail."""
    pass


# =============================================================================
# IMAGEN CLIENT
# =============================================================================

class ImagenClient:
    """Main Imagen AI client for handling the editing workflow."""

    def __init__(self, api_key: str, base_url: str = "https://api-beta.imagen-ai.com/v1"):
        """
        Initialize the Imagen AI client.

        Args:
            api_key: Your Imagen AI API key
            base_url: Base URL for the API (default: production URL)

        Raises:
            ValueError: If api_key is empty or None
        """
        if not api_key or not api_key.strip():
            raise ValueError("API key cannot be empty")

        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip('/')
        self._session: Optional[httpx.AsyncClient] = None

        logger.debug(f"Initialized ImagenClient with base_url: {self.base_url}")

    def _get_session(self) -> httpx.AsyncClient:
        """Get or create an HTTP session."""
        if self._session is None:
            self._session = httpx.AsyncClient(
                headers={
                    'x-api-key': self.api_key,
                    'User-Agent': 'Imagen-Python-SDK/4.0.0'
                },
                timeout=httpx.Timeout(300.0)
            )
            logger.debug("Created new HTTP session")
        return self._session

    async def close(self):
        """Close the HTTP session."""
        if self._session:
            await self._session.aclose()
            self._session = None
            logger.debug("Closed HTTP session")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make an HTTP request to the API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            **kwargs: Additional request parameters

        Returns:
            JSON response as dictionary

        Raises:
            AuthenticationError: If authentication fails (401)
            ImagenError: For other API errors
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        session = self._get_session()

        logger.debug(f"Making {method} request to {url}")

        try:
            response = await session.request(method, url, **kwargs)
            logger.debug(f"Response status: {response.status_code}")

            # Check for authentication errors first
            if response.status_code == 401:
                logger.error("Authentication failed")
                raise AuthenticationError("Invalid API key or unauthorized.")

            # Check for other client or server errors
            elif response.status_code >= 400:
                try:
                    # Try to parse a detailed error message from the JSON response
                    error_data = response.json()
                    message = error_data.get('detail', response.text)
                except Exception:
                    # Fallback to the raw response text if JSON parsing fails
                    message = response.text

                logger.error(f"API error {response.status_code}: {message}")
                raise ImagenError(f"API Error ({response.status_code}): {message}")

            # Handle successful responses
            if response.status_code == 204:  # No Content
                return {}
            else:
                return response.json()

        except httpx.RequestError as e:
            logger.error(f"Request failed: {e}")
            raise ImagenError(f"Request failed: {e}")

    async def create_project(self, name: Optional[str] = None) -> str:
        """
        Create a new project.

        Args:
            name: Optional project name

        Returns:
            Project UUID

        Raises:
            ProjectError: If project creation fails
        """
        data = {}
        if name:
            data['name'] = name

        logger.info(f"Creating project: {name or 'Unnamed'}")
        response_json = await self._make_request('POST', '/projects/', json=data)

        try:
            # Validate the response and extract the UUID
            project_response = ProjectCreationResponse.model_validate(response_json)
            project_uuid = project_response.data.project_uuid
            logger.info(f"Created project with UUID: {project_uuid}")
            return project_uuid
        except ValidationError as e:
            logger.error(f"Failed to parse project creation response: {e}")
            raise ProjectError(f"Could not parse project creation response: {e}")

    async def upload_images(self, project_uuid: str, image_paths: List[Union[str, Path]],
                          max_concurrent: int = 5, calculate_md5: bool = False,
                          progress_callback: Optional[Callable[[int, int, str], None]] = None) -> UploadSummary:
        """
        Upload images to a project.

        Args:
            project_uuid: UUID of the target project
            image_paths: List of local image file paths
            max_concurrent: Maximum concurrent uploads (default: 5)
            calculate_md5: Whether to calculate MD5 hashes (default: False)
            progress_callback: Optional progress callback function

        Returns:
            Summary of upload results

        Raises:
            UploadError: If no valid files found or upload fails
        """
        if max_concurrent < 1:
            raise ValueError("max_concurrent must be at least 1")

        logger.info(f"Starting upload of {len(image_paths)} images to project {project_uuid}")

        files_to_upload: List[FileUploadInfo] = []
        valid_paths: List[Path] = []

        for path_str in image_paths:
            path = Path(path_str)
            if path.exists() and path.is_file():
                md5_hash = await self._calculate_md5(path) if calculate_md5 else None
                files_to_upload.append(FileUploadInfo(file_name=path.name, md5=md5_hash))
                valid_paths.append(path)
            else:
                logger.warning(f"Skipping invalid path: {path}")

        if not valid_paths:
            raise UploadError("No valid local files found to upload.")

        # Get presigned URLs from the API
        upload_payload = {"files_list": [f.model_dump(exclude_none=True) for f in files_to_upload]}
        response_json = await self._make_request('POST', f'/projects/{project_uuid}/get_temporary_upload_links',
                                                 json=upload_payload)

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
                logger.debug(f"Successfully uploaded: {file_path.name}")
                return UploadResult(file=str(file_path), success=True)
            except Exception as e:
                logger.error(f"Failed to upload {file_path.name}: {e}")
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
        results: List[UploadResult] = await asyncio.gather(*tasks)

        summary = UploadSummary(
            total=len(valid_paths),
            successful=sum(1 for r in results if r.success),
            failed=sum(1 for r in results if not r.success),
            results=results
        )

        logger.info(f"Upload completed: {summary.successful}/{summary.total} successful")
        return summary

    async def start_editing(self, project_uuid: str, profile_key: int,
                            photography_type: Optional[PhotographyType] = None,
                            edit_options: Optional[EditOptions] = None) -> StatusDetails:
        """
        Start editing images in a project.

        Args:
            project_uuid: UUID of the project
            profile_key: Profile to use for editing
            photography_type: Optional photography type for optimization
            edit_options: Optional editing parameters

        Returns:
            Final status details when editing is complete

        Raises:
            ProjectError: If editing fails
        """
        edit_data = {'profile_key': profile_key}
        if photography_type:
            edit_data['photography_type'] = photography_type.value
        if edit_options:
            edit_data.update(edit_options.to_api_dict())

        logger.info(f"Starting editing for project {project_uuid} with profile {profile_key}")
        await self._make_request('POST', f'/projects/{project_uuid}/edit', json=edit_data, headers={'Content-Type': ''})
        return await self._wait_for_completion(project_uuid, 'edit')

    async def get_download_links(self, project_uuid: str) -> List[str]:
        """
        Get download links for edited images.

        Args:
            project_uuid: UUID of the project

        Returns:
            List of download URLs

        Raises:
            ProjectError: If getting links fails
        """
        logger.debug(f"Getting download links for project {project_uuid}")
        response_json = await self._make_request('GET', f'/projects/{project_uuid}/edit/get_temporary_download_links')
        try:
            # Validate the full response structure
            links_response = DownloadLinksResponse.model_validate(response_json)
            # Access the list via .data and extract just the URL strings
            links = [link.download_link for link in links_response.data.files_list]
            logger.info(f"Retrieved {len(links)} download links")
            return links
        except ValidationError as e:
            raise ProjectError(f"Could not parse download links response: {e}")

    async def export_project(self, project_uuid: str) -> StatusDetails:
        """
        Export project images.

        Args:
            project_uuid: UUID of the project

        Returns:
            Final status details when export is complete

        Raises:
            ProjectError: If export fails
        """
        logger.info(f"Starting export for project {project_uuid}")
        await self._make_request('POST', f'/projects/{project_uuid}/export')
        return await self._wait_for_completion(project_uuid, 'export')

    async def get_export_links(self, project_uuid: str) -> List[str]:
        """
        Get download links for exported images.

        Args:
            project_uuid: UUID of the project

        Returns:
            List of export download URLs

        Raises:
            ProjectError: If getting links fails
        """
        logger.debug(f"Getting export links for project {project_uuid}")
        response_json = await self._make_request('GET', f'/projects/{project_uuid}/export/get_temporary_download_links')
        try:
            # Validate the full response structure
            links_response = DownloadLinksResponse.model_validate(response_json)
            # Access the list via .data and extract just the URL strings
            links = [link.download_link for link in links_response.data.files_list]
            logger.info(f"Retrieved {len(links)} export links")
            return links
        except ValidationError as e:
            raise ProjectError(f"Could not parse export links response: {e}")

    async def download_files(self, download_links: List[str], output_dir: Union[str, Path] = "downloads",
                             max_concurrent: int = 5, progress_callback: Optional[Callable[[int, int, str], None]] = None) -> List[str]:
        """
        Download files from the provided download links.

        Args:
            download_links: List of URLs to download
            output_dir: Directory to save downloaded files (default: "downloads")
            max_concurrent: Maximum number of concurrent downloads (default: 5)
            progress_callback: Optional callback function for progress updates

        Returns:
            List of local file paths of downloaded files

        Raises:
            DownloadError: If no files could be downloaded
        """
        if max_concurrent < 1:
            raise ValueError("max_concurrent must be at least 1")

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        if not download_links:
            raise DownloadError("No download links provided.")

        logger.info(f"Starting download of {len(download_links)} files to {output_path}")
        semaphore = asyncio.Semaphore(max_concurrent)

        async def download_single_file(url: str, index: int) -> Optional[str]:
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
                        async with aiofiles.open(local_path, 'wb') as f:
                            await f.write(response.content)

                    if progress_callback:
                        progress_callback(index + 1, len(download_links), f"Downloaded {filename}")

                    logger.debug(f"Downloaded: {filename}")
                    return str(local_path)

                except Exception as e:
                    logger.error(f"Failed to download file {index + 1}: {e}")
                    if progress_callback:
                        progress_callback(index + 1, len(download_links), f"Failed to download file {index + 1}: {e}")
                    return None

        # Create download tasks
        tasks = [download_single_file(url, i) for i, url in enumerate(download_links)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter successful downloads
        successful_downloads = [path for path in results if isinstance(path, str) and path is not None]

        if not successful_downloads:
            raise DownloadError("Failed to download any files.")

        logger.info(f"Downloaded {len(successful_downloads)}/{len(download_links)} files successfully")
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
            if filename and '.' in filename and len(filename) > 1:
                return filename

        except Exception as e:
            logger.debug(f"Failed to extract filename from {url}: {e}")

        # Fallback to generated filename
        return f"imagen_edited_{index + 1:05d}.jpg"

    async def get_profiles(self) -> List[Profile]:
        """
        Get available editing profiles.

        Returns:
            List of available profiles

        Raises:
            ImagenError: If getting profiles fails
        """
        logger.debug("Getting available profiles")
        response_json = await self._make_request('GET', '/profiles')
        try:
            # Validate the full response structure
            api_data = ProfileApiData.model_validate(response_json)
            # Return the nested list of profiles
            profiles = api_data.data.profiles
            logger.info(f"Retrieved {len(profiles)} profiles")
            return profiles
        except ValidationError as e:
            raise ImagenError(f"Failed to parse profiles from API response: {e}")

    @staticmethod
    async def _calculate_md5(file_path: Path) -> str:
        """
        Calculate MD5 hash of a file.

        Args:
            file_path: Path to the file

        Returns:
            MD5 hash as hex string
        """
        hash_md5 = hashlib.md5()
        async with aiofiles.open(file_path, 'rb') as f:
            while True:
                chunk = await f.read(8192)  # Read in 8KB chunks
                if not chunk:
                    break
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

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
            async with aiofiles.open(file_path, 'rb') as f:
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
        max_wait_time = 3600  # 1 hour max wait time

        logger.info(f"⏳ Waiting for {operation} to complete... (will check status periodically)")

        while True:
            elapsed = time.time() - start_time

            # Check for timeout
            if elapsed > max_wait_time:
                raise ProjectError(f"{operation.title()} timed out after {max_wait_time} seconds")

            endpoint = f'/projects/{project_uuid}/{operation}/status'
            status_json = await self._make_request('GET', endpoint)

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
            logger.info(f"  - Status: {status_details.status}{progress_str} (elapsed: {elapsed_int}s)")

            if status_details.status == 'Completed':
                logger.info(f"✅ {operation.title()} completed successfully!")
                return status_details  # Return the inner details object

            if status_details.status == 'Failed':
                error_msg = f"{operation.title()} failed."
                if status_details.details:
                    error_msg += f" Details: {status_details.details}"
                raise ProjectError(error_msg)

            await asyncio.sleep(check_interval)
            check_interval = min(check_interval * 1.2, max_interval)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def get_profiles(api_key: str, base_url: str = "https://api-beta.imagen-ai.com/v1") -> List[Profile]:
    """
    Get available editing profiles using a standalone function.

    Args:
        api_key: Your Imagen AI API key
        base_url: API base URL (default: production URL)

    Returns:
        List of available profiles

    Raises:
        ImagenError: If getting profiles fails
    """
    async with ImagenClient(api_key, base_url) as client:
        return await client.get_profiles()


async def quick_edit(api_key: str, profile_key: int, image_paths: List[Union[str, Path]],
                     project_name: Optional[str] = None, photography_type: Optional[PhotographyType] = None,
                     export: bool = False, edit_options: Optional[EditOptions] = None,
                     download: bool = False, download_dir: Union[str, Path] = "downloads",
                     base_url: str = "https://api-beta.imagen-ai.com/v1") -> QuickEditResult:
    """
    Complete workflow: create project, upload, edit, and optionally export and download.

    Args:
        api_key: Your Imagen AI API key
        profile_key: Profile ID to use for editing
        image_paths: List of local image file paths to upload
        project_name: Optional name for the project
        photography_type: Optional photography type for optimization
        export: Whether to export the images (default: False)
        edit_options: Optional editing parameters
        download: Whether to download the edited images (default: False)
        download_dir: Directory to save downloaded files (default: "downloads")
        base_url: API base URL (default: production URL)

    Returns:
        QuickEditResult with project info, upload summary, links, and optionally local file paths

    Raises:
        UploadError: If no files were uploaded successfully
        Various other errors from individual operations
    """
    logger.info(f"Starting quick_edit workflow with {len(image_paths)} images")

    async with ImagenClient(api_key, base_url) as client:
        project_uuid = await client.create_project(project_name)
        upload_summary = await client.upload_images(project_uuid, image_paths)

        if upload_summary.successful == 0:
            raise UploadError("quick_edit failed because no files were uploaded successfully.")

        await client.start_editing(project_uuid, profile_key, photography_type, edit_options=edit_options)
        download_links = await client.get_download_links(project_uuid)

        export_links = None
        downloaded_files = None
        exported_files = None

        if export:
            await client.export_project(project_uuid)
            export_links = await client.get_export_links(project_uuid)

        if download:
            # Download edited files
            downloaded_files = await client.download_files(download_links, download_dir)

            # Download exported files if they exist
            if export_links:
                export_download_dir = Path(download_dir) / "exported"
                exported_files = await client.download_files(export_links, export_download_dir)

        result = QuickEditResult(
            project_uuid=project_uuid,
            upload_summary=upload_summary,
            download_links=download_links,
            export_links=export_links,
            downloaded_files=downloaded_files,
            exported_files=exported_files
        )

        logger.info(f"Quick edit workflow completed successfully for project {project_uuid}")
        return result


if __name__ == "__main__":
    # This file is intended to be used as a library.
    # See the 'examples.py' file for usage demonstrations.
    print("Imagen AI SDK loaded. See examples.py for usage.")