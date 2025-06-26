from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, ValidationError, Field
from .enums import PhotographyType

class Profile(BaseModel):
    image_type: str = Field(..., description="Type of images this profile handles")
    profile_key: int = Field(..., description="Unique identifier for the profile")
    profile_name: str = Field(..., description="Human-readable name of the profile")
    profile_type: str = Field(..., description="Type/tier of the profile")

class ProfileApiResponse(BaseModel):
    profiles: List[Profile]

class ProfileApiData(BaseModel):
    data: ProfileApiResponse

class ProjectCreationResponseData(BaseModel):
    project_uuid: str = Field(..., description="Unique identifier for the created project")

class ProjectCreationResponse(BaseModel):
    data: ProjectCreationResponseData

class FileUploadInfo(BaseModel):
    file_name: str = Field(..., description="Name of the file")
    md5: Optional[str] = Field(None, description="MD5 hash of the file content")

class PresignedUrl(BaseModel):
    file_name: str = Field(..., description="Name of the file")
    upload_link: str = Field(..., description="Presigned URL for upload")

class PresignedUrlList(BaseModel):
    files_list: List[PresignedUrl]

class PresignedUrlResponse(BaseModel):
    data: PresignedUrlList

class EditOptions(BaseModel):
    crop: Optional[bool] = Field(None, description="Whether to apply cropping")
    straighten: Optional[bool] = Field(None, description="Whether to straighten the image")
    hdr_merge: Optional[bool] = Field(None, description="Whether to apply HDR merge")
    portrait_crop: Optional[bool] = Field(None, description="Whether to apply portrait cropping")
    smooth_skin: Optional[bool] = Field(None, description="Whether to apply skin smoothing")

    def to_api_dict(self) -> Dict[str, Any]:
        return self.model_dump(exclude_none=True)

class StatusDetails(BaseModel):
    status: str = Field(..., description="Current status of the operation")
    progress: Optional[float] = Field(None, description="Progress percentage (0-100)")
    details: Optional[str] = Field(None, description="Additional status details")

class StatusResponse(BaseModel):
    data: StatusDetails

class DownloadLink(BaseModel):
    file_name: str = Field(..., description="Name of the file")
    download_link: str = Field(..., description="URL to download the file")

class DownloadLinksList(BaseModel):
    files_list: List[DownloadLink]

class DownloadLinksResponse(BaseModel):
    data: DownloadLinksList

class UploadResult(BaseModel):
    file: str = Field(..., description="Path of the uploaded file")
    success: bool = Field(..., description="Whether the upload was successful")
    error: Optional[str] = Field(None, description="Error message if upload failed")

class UploadSummary(BaseModel):
    total: int = Field(..., description="Total number of files attempted")
    successful: int = Field(..., description="Number of successfully uploaded files")
    failed: int = Field(..., description="Number of failed uploads")
    results: List[UploadResult] = Field(..., description="Detailed results for each file")

class QuickEditResult(BaseModel):
    project_uuid: str = Field(..., description="UUID of the created project")
    upload_summary: UploadSummary = Field(..., description="Summary of upload results")
    download_links: List[str] = Field(..., description="URLs to download edited images")
    export_links: Optional[List[str]] = Field(None, description="URLs to download exported images")
    downloaded_files: Optional[List[str]] = Field(None, description="Local paths of downloaded edited files")
    exported_files: Optional[List[str]] = Field(None, description="Local paths of downloaded exported files") 