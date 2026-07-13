package imagen

// Profile is an editing profile (a saved look) available to the account.
type Profile struct {
	ImageType   string `json:"image_type,omitempty"` // RAW or JPG
	ProfileKey  int    `json:"profile_key"`
	ProfileName string `json:"profile_name,omitempty"`
	ProfileType string `json:"profile_type,omitempty"`
}

// SkyTemplate is a sky-replacement template; use ID for
// EditOptions.SkyReplacementTemplateID.
type SkyTemplate struct {
	ID        int  `json:"id"`
	IsDefault bool `json:"is_default,omitempty"`
}

// CreateProjectResponse carries the UUID of a newly created project.
type CreateProjectResponse struct {
	ProjectUUID string `json:"project_uuid"`
}

// ProjectListItem is one project in a listing (open shape; extra fields ignored).
// For I2I projects, Status carries the editing state (Pending, In Progress,
// Completed, Failed) that WaitForI2ICompletion polls, and NumberOfImages reports
// how many uploaded images the server has registered.
type ProjectListItem struct {
	ProjectUUID    string `json:"project_uuid,omitempty"`
	Name           string `json:"name,omitempty"`
	Status         string `json:"status,omitempty"`
	NumberOfImages int    `json:"number_of_images,omitempty"`
}

// Pagination is the paging metadata attached to a project listing.
type Pagination struct {
	Total int `json:"total,omitempty"`
	Size  int `json:"size,omitempty"`
	Page  int `json:"page,omitempty"`
}

// ProjectListResponse is a page of projects.
type ProjectListResponse struct {
	Projects   []ProjectListItem `json:"projects"`
	Pagination Pagination        `json:"pagination"`
}

// ListProjectsOptions are optional query parameters for listing projects.
// Nil fields are omitted from the request.
type ListProjectsOptions struct {
	Size         *int
	Page         *int
	ClientType   *string
	IsArchived   *bool
	GetThumbnail *bool
}

// FileUploadInfo names a file to be uploaded and, optionally, its base64 MD5.
type FileUploadInfo struct {
	FileName string `json:"file_name"`
	MD5      string `json:"md5,omitempty"`
}

// uploadLinksRequest is the body for get_temporary_upload_links.
type uploadLinksRequest struct {
	FilesList  []FileUploadInfo `json:"files_list"`
	ClientType string           `json:"client_type,omitempty"`
}

// UploadLink pairs a file name with its presigned PUT URL.
type UploadLink struct {
	FileName   string `json:"file_name"`
	UploadLink string `json:"upload_link"`
}

// UploadLinksResponse is the response from get_temporary_upload_links.
type UploadLinksResponse struct {
	FilesList []UploadLink `json:"files_list"`
}

// SingleUploadLink is a lone presigned PUT URL.
type SingleUploadLink struct {
	UploadLink string `json:"upload_link"`
}

// SingleDownloadLink is a lone presigned GET URL.
type SingleDownloadLink struct {
	DownloadLink string `json:"download_link"`
}

// DownloadLink pairs a file name with its presigned GET URL.
type DownloadLink struct {
	FileName     string `json:"file_name"`
	DownloadLink string `json:"download_link"`
}

// DownloadLinksList is the response from the various download-links endpoints.
type DownloadLinksList struct {
	FilesList []DownloadLink `json:"files_list"`
}

// MessageResponse is a simple acknowledgement message.
type MessageResponse struct {
	Message string `json:"message,omitempty"`
}

// StatusDetails is the payload of an edit/export status poll. Terminal values of
// Status are StatusCompleted and StatusFailed; any other value means keep polling.
type StatusDetails struct {
	Status   string  `json:"status"`
	Progress float64 `json:"progress,omitempty"`
	Details  string  `json:"details,omitempty"`
}

// Terminal and known status values.
const (
	StatusCompleted = "Completed"
	StatusFailed    = "Failed"
)

// IsTerminal reports whether the status will not change with further polling.
func (s StatusDetails) IsTerminal() bool {
	return s.Status == StatusCompleted || s.Status == StatusFailed
}

// AITool describes one available quick AI tool.
type AITool struct {
	EnhancementType string `json:"enhancement_type"`
	Label           string `json:"label,omitempty"`
	EnabledForBatch bool   `json:"enabled_for_batch,omitempty"`
}

// AIToolsResponse lists the AI tools available for a project (open shape).
type AIToolsResponse struct {
	Prompts []AITool `json:"prompts"`
}

// EnhanceResult is the result of an enhance or copilot call. VersionID is
// intentionally untyped (the server declares it as an open optional field).
type EnhanceResult struct {
	Status           string `json:"status,omitempty"`
	VersionID        any    `json:"version_id,omitempty"`
	EnhancedImageURL string `json:"enhanced_image_url,omitempty"`
}
