"""
Imagen AI Python SDK

Streamlined SDK for the Imagen AI API workflow:
1. Create client with API key
2. Create project
3. Upload images asynchronously to presigned URLs
4. Trigger editing
5. Poll status until complete
6. Download results
7. Optional: Export and download

Quick Start:
    import asyncio
    from imagen_sdk import ImagenClient, EditOptions, PhotographyType

    async def main():
        async with ImagenClient("your_api_key") as client:
            project_uuid = await client.create_project("My Photos")
            upload_summary = await client.upload_images(project_uuid, ["photo1.jpg"])

            # Use the EditOptions model for parameters
            edit_opts = EditOptions(crop=True, straighten=True)
            await client.start_editing(
                project_uuid,
                profile_key=1,
                photography_type=PhotographyType.PORTRAITS,
                edit_options=edit_opts
            )

            # Get download links
            links = await client.get_download_links(project_uuid)

            # Download the edited files
            downloaded_files = await client.download_files(links, "my_edited_photos")
            print(f"Downloaded {len(downloaded_files)} edited images")

    asyncio.run(main())

One-Line Usage:
    from imagen_sdk import quick_edit, EditOptions, PhotographyType

    # Define options using the model
    options = EditOptions(portrait_crop=True, smooth_skin=True)

    result = await quick_edit(
        api_key="your_key",
        profile_key=1,
        image_paths=["photo1.jpg", "photo2.jpg"],
        photography_type=PhotographyType.WEDDING,
        edit_options=options,
        export=True,
        download=True,  # Automatically download edited images
        download_dir="my_results"
    )
    print(f"Project UUID: {result.project_uuid}")
    print(f"Downloaded files: {result.downloaded_files}")
    print(f"Exported files: {result.exported_files}")
"""

from .enums import CropAspectRatio, PhotographyType
from .exceptions import (
    AuthenticationError,
    DownloadError,
    ImagenError,
    ProjectError,
    UploadError,
)
from .imagen_sdk import (
    JPG_EXTENSIONS,
    RAW_EXTENSIONS,
    SUPPORTED_FILE_FORMATS,
    ImagenClient,
    check_files_match_profile_type,
    get_profile,
    get_profiles,
    quick_edit,
)
from .models import (
    DownloadLink,
    DownloadLinksList,
    DownloadLinksResponse,
    EditOptions,
    FileUploadInfo,
    PresignedUrl,
    PresignedUrlList,
    PresignedUrlResponse,
    Profile,
    ProfileApiData,
    ProfileApiResponse,
    ProjectCreationResponse,
    ProjectCreationResponseData,
    QuickEditResult,
    StatusDetails,
    StatusResponse,
    UploadResult,
    UploadSummary,
)

# Version info
__version__ = "1.0.0"
__author__ = "Shahar Polak"
__email__ = "shahar@imagen-ai.com"
__description__ = "A robust, Pydantic-powered SDK for the Imagen AI photo editing workflow"
__url__ = "https://github.com/imagenai/imagen-ai-sdk"

# Main exports for public API
__all__ = [
    "ImagenClient",
    "Profile",
    "EditOptions",
    "UploadResult",
    "UploadSummary",
    "QuickEditResult",
    "StatusDetails",
    "ProfileApiResponse",
    "ProfileApiData",
    "ProjectCreationResponseData",
    "ProjectCreationResponse",
    "FileUploadInfo",
    "PresignedUrl",
    "PresignedUrlList",
    "PresignedUrlResponse",
    "StatusResponse",
    "DownloadLink",
    "DownloadLinksList",
    "DownloadLinksResponse",
    "ImagenError",
    "AuthenticationError",
    "ProjectError",
    "UploadError",
    "DownloadError",
    "PhotographyType",
    "CropAspectRatio",
    "quick_edit",
    "get_profiles",
    "get_profile",
    "check_files_match_profile_type",
    "RAW_EXTENSIONS",
    "JPG_EXTENSIONS",
    "SUPPORTED_FILE_FORMATS",
    "__version__",
]
