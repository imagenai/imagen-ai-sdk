from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .enums import DNGCompression, ProjectSource


class Profile(BaseModel):
    image_type: str = Field(..., description="Type of images this profile handles")
    profile_key: int = Field(..., description="Unique identifier for the profile")
    profile_name: str = Field(..., description="Human-readable name of the profile")
    profile_type: str = Field(..., description="Type/tier of the profile")


class ProfileApiResponse(BaseModel):
    profiles: list[Profile]


class ProfileApiData(BaseModel):
    data: ProfileApiResponse


class ProjectCreationResponseData(BaseModel):
    project_uuid: str = Field(..., description="Unique identifier for the created project")


class ProjectCreationResponse(BaseModel):
    data: ProjectCreationResponseData


class FileUploadInfo(BaseModel):
    file_name: str = Field(..., description="Name of the file")
    md5: str | None = Field(None, description="MD5 hash of the file content")


class PresignedUrl(BaseModel):
    file_name: str = Field(..., description="Name of the file")
    upload_link: str = Field(..., description="Presigned URL for upload")


class PresignedUrlList(BaseModel):
    files_list: list[PresignedUrl]


class PresignedUrlResponse(BaseModel):
    data: PresignedUrlList


class EditOptions(BaseModel):
    crop: bool | None = Field(None, description="Whether to apply cropping")
    straighten: bool | None = Field(None, description="Whether to straighten the image")
    hdr_merge: bool | None = Field(None, description="Whether to apply HDR merge")
    portrait_crop: bool | None = Field(None, description="Whether to apply portrait cropping")
    smooth_skin: bool | None = Field(None, description="Whether to apply skin smoothing")
    subject_mask: bool | None = Field(None, description="Whether to apply subject masking")

    headshot_crop: bool | None = Field(None, description="Whether to apply headshot cropping")
    perspective_correction: bool | None = Field(None, description="Whether to correct perspective")

    sky_replacement: bool | None = Field(None, description="Whether to apply sky replacement")
    sky_replacement_template_id: int | None = Field(None, description="Sky replacement template ID")
    window_pull: bool | None = Field(None, description="Whether to apply window pull")
    crop_aspect_ratio: str | None = Field(None, description="Custom aspect ratio for cropping")

    callback_url: str | None = Field(None, description="Optional webhook URL called when editing completes")
    hdr_output_compression: DNGCompression | None = Field(
        None, description="Compression mode for HDR-merged DNG output (LOSSY or LOSSLESS)"
    )

    @model_validator(mode="after")
    def check_mutual_exclusivity(self):
        # Enforce: crop, headshot_crop, portrait_crop are mutually exclusive
        crop_tools = [self.crop, self.headshot_crop, self.portrait_crop]
        crop_tools_set = [tool for tool in crop_tools if tool is True]
        if len(crop_tools_set) > 1:
            raise ValueError("Only one of crop, headshot_crop, or portrait_crop can be set to True.")

        # Enforce: straighten and perspective_correction are mutually exclusive
        if self.straighten is True and self.perspective_correction is True:
            raise ValueError("Only one of straighten or perspective_correction can be set to True.")

        return self

    def to_api_dict(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True, mode="json")


class StatusDetails(BaseModel):
    status: str = Field(..., description="Current status of the operation")
    progress: float | None = Field(None, description="Progress percentage (0-100)")
    details: str | None = Field(None, description="Additional status details")


class StatusResponse(BaseModel):
    data: StatusDetails


class DownloadLink(BaseModel):
    file_name: str = Field(..., description="Name of the file")
    download_link: str = Field(..., description="URL to download the file")


class DownloadLinksList(BaseModel):
    files_list: list[DownloadLink]


class DownloadLinksResponse(BaseModel):
    data: DownloadLinksList


class UploadResult(BaseModel):
    file: str = Field(..., description="Path of the uploaded file")
    success: bool = Field(..., description="Whether the upload was successful")
    error: str | None = Field(None, description="Error message if upload failed")


class UploadSummary(BaseModel):
    total: int = Field(..., description="Total number of files attempted")
    successful: int = Field(..., description="Number of successfully uploaded files")
    failed: int = Field(..., description="Number of failed uploads")
    results: list[UploadResult] = Field(..., description="Detailed results for each file")


class QuickEditResult(BaseModel):
    project_uuid: str = Field(..., description="UUID of the created project")
    upload_summary: UploadSummary = Field(..., description="Summary of upload results")
    download_links: list[str] = Field(..., description="URLs to download edited images")
    export_links: list[str] | None = Field(None, description="URLs to download exported images")
    downloaded_files: list[str] | None = Field(None, description="Local paths of downloaded edited files")
    exported_files: list[str] | None = Field(None, description="Local paths of downloaded exported files")


# =============================================================================
# SKY REPLACEMENT TEMPLATES
# =============================================================================


class SkyTemplate(BaseModel):
    id: int = Field(..., description="Sky replacement template ID")
    is_default: bool = Field(..., description="Whether this is the default sky template")


class SkyTemplatesResponse(BaseModel):
    templates: list[SkyTemplate] = Field(..., description="Available sky replacement templates")


# =============================================================================
# PROJECT LISTING / RETRIEVAL
# =============================================================================


class PaginationInfo(BaseModel):
    total: int = Field(..., description="Total number of matching projects")
    size: int = Field(..., description="Page size")
    page: int = Field(..., description="Current page index (0-based)")


class ProjectListItem(BaseModel):
    project_id: int | None = Field(None, description="Numeric project ID")
    project_uuid: str = Field(..., description="Project UUID")
    name: str | None = Field(None, description="Project name")
    status: str = Field(..., description="Project status")
    created_at: str = Field(..., description="Creation timestamp")
    number_of_images: int = Field(..., description="Number of images in the project")
    profile: str | None = Field(None, description="Profile associated with the project")
    ai_tools: list[str] | None = Field(None, description="AI tools applied/available for the project")
    customer_reference_id: int = Field(..., description="Customer reference ID")
    thumbnail_src: str | None = Field(None, description="Thumbnail image URL")
    export_status: str | None = Field(None, description="Export status, if any")


class ProjectListResponse(BaseModel):
    projects: list[ProjectListItem] = Field(..., description="Projects on this page")
    pagination: PaginationInfo = Field(..., description="Pagination metadata")


# =============================================================================
# PER-IMAGE EXPORT LINKS
# =============================================================================


class TemporaryFileUploadData(BaseModel):
    file_name: str = Field(..., description="Name of the file")
    upload_link: str = Field(..., description="Presigned URL for upload")


class FileDownloadInfo(BaseModel):
    file_name: str = Field(..., description="Name of the file")
    download_link: str = Field(..., description="URL to download the file")


# =============================================================================
# AI ENHANCEMENT / COPILOT / FINALIZE REQUESTS
# =============================================================================


class AITool(BaseModel):
    """A single AI enhancement (quick) tool available for a project.

    The ``enhancement_type`` value is what you pass as ``tool_id`` to ``enhance_image``.
    Extra fields returned by the API are preserved.
    """

    model_config = ConfigDict(extra="allow")

    enhancement_type: str = Field(..., description="Tool identifier; use as enhance_image's tool_id")
    label: str | None = Field(None, description="Human-readable tool name")
    enabled_for_batch: bool | None = Field(None, description="Whether the tool can run across a batch")


class AIToolsResponse(BaseModel):
    """Response describing the AI enhancement tools available for a project."""

    model_config = ConfigDict(extra="allow")

    prompts: list[AITool] = Field(default_factory=list, description="Available AI enhancement tools")


class EnhanceResult(BaseModel):
    """Result of an AI enhancement (``enhance_image``) or copilot (``apply_copilot``) operation.

    Mirrors the server's ``AIEnhancementResponse``. ``version_id`` is intentionally
    untyped (``Any``) because the API declares it as an optional, open-typed field.
    Unrecognized fields are preserved.
    """

    model_config = ConfigDict(extra="allow")

    status: str = Field(..., description="Operation status, e.g. 'SUCCESS'")
    version_id: Any = Field(None, description="Version ID of the produced image, if any")
    enhanced_image_url: str = Field(..., description="URL of the enhanced image")


class EnhanceImageRequest(BaseModel):
    tool_id: str = Field(..., min_length=1, description="Identifier of the AI quick tool to apply")
    parent_version_id: int | None = Field(None, description="Version ID to base this enhancement on")
    project_source: ProjectSource = Field(ProjectSource.REGULAR, description="Project source (REGULAR or I2I)")

    def to_api_dict(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True, mode="json")


class CopilotRequest(BaseModel):
    instruction: str = Field(..., min_length=1, max_length=255, description="Natural language editing instruction")
    parent_version_id: int | None = Field(None, description="Version ID to base this instruction on")
    project_source: ProjectSource = Field(ProjectSource.REGULAR, description="Project source (REGULAR or I2I)")

    def to_api_dict(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True, mode="json")


class ResetCopilotRequest(BaseModel):
    project_source: ProjectSource = Field(ProjectSource.REGULAR, description="Project source (REGULAR or I2I)")

    def to_api_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class FinalizeProjectRequest(BaseModel):
    project_source: ProjectSource = Field(ProjectSource.REGULAR, description="Project source (REGULAR or I2I)")

    def to_api_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


# =============================================================================
# I2I (IMAGE-TO-IMAGE) EDIT + MULTIPART UPLOADS
# =============================================================================


class I2IEditOptions(BaseModel):
    hdr_merge: bool | None = Field(None, description="Whether to apply HDR merge")
    sky_replacement: bool | None = Field(None, description="Whether to apply sky replacement")
    sky_replacement_template_id: int | None = Field(None, description="Sky replacement template ID")
    perspective_correction: bool | None = Field(None, description="Whether to correct perspective")
    callback_url: str | None = Field(None, description="Optional webhook URL called when editing completes")

    def to_api_dict(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True, mode="json")


class CreateMultipartUploadLinksRequest(BaseModel):
    file_name: str = Field(..., min_length=1, description="Name of the file to upload")
    part_count: int = Field(..., ge=1, le=10000, description="Number of parts the file is split into")

    def to_api_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class MultipartUploadPartUrl(BaseModel):
    part_number: int = Field(..., description="1-based part number")
    upload_url: str = Field(..., description="Presigned URL for this part")


class MultipartUploadLinksResponse(BaseModel):
    upload_id: str = Field(..., description="Multipart upload ID")
    key: str = Field(..., description="Storage key for the upload")
    parts: list[MultipartUploadPartUrl] = Field(..., description="Presigned URLs for each part")


class CompleteMultipartUploadRequest(BaseModel):
    file_name: str = Field(..., min_length=1, description="Name of the uploaded file")

    def to_api_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class MessageResponse(BaseModel):
    """A simple ``{"message": ...}`` response (e.g. from ``start_i2i_editing``)."""

    model_config = ConfigDict(extra="allow")

    message: str = Field(..., description="Human-readable status message")


class SingleDownloadLink(BaseModel):
    """A single download link, as returned by ``get_i2i_download_link``."""

    model_config = ConfigDict(extra="allow")

    download_link: str = Field(..., description="Temporary URL to download the file")


class CreateFilesUploadLinksRequest(BaseModel):
    files_list: list[FileUploadInfo] = Field(..., description="Files to obtain upload links for")
    client_type: str = Field("API", description="Client type for the upload request")

    def to_api_dict(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True, mode="json")
