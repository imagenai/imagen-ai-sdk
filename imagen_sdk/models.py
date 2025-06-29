from typing import Any

from pydantic import BaseModel, Field


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

    def to_api_dict(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)


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
