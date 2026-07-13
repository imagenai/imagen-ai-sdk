package imagen

import (
	"context"
	"fmt"
	"path/filepath"
)

// QuickEditParams configures the one-call QuickEdit workflow.
type QuickEditParams struct {
	// ProjectName is optional; empty means a server-generated name.
	ProjectName string
	// ProfileKey selects the editing profile (required).
	ProfileKey int
	// ImagePaths are the local files to edit (required).
	ImagePaths []string
	// PhotographyType tunes the AI to a shoot type (optional).
	PhotographyType PhotographyType
	// EditOptions are the editing toggles (optional).
	EditOptions EditOptions
	// Export additionally exports edited images to JPEG.
	Export bool
	// Download saves the edited XMPs to DownloadDir and, when Export is also set,
	// the exported JPEGs to ExportDownloadDir.
	Download bool
	// DownloadDir is where edited XMPs are written (required if Download).
	DownloadDir string
	// ExportDownloadDir is where exported JPEGs are written when Export and
	// Download are both set. Defaults to DownloadDir/"exported".
	ExportDownloadDir string
	// Upload and Poll tune the upload and polling phases (optional).
	Upload *UploadOptions
	Poll   *PollOptions
}

// QuickEditResult holds the artifacts produced by QuickEdit.
type QuickEditResult struct {
	ProjectUUID     string
	UploadSummary   *UploadSummary
	EditLinks       []DownloadLink
	ExportLinks     []DownloadLink
	DownloadedFiles []string // edited XMPs saved to DownloadDir
	ExportedFiles   []string // exported JPEGs saved to ExportDownloadDir (if Export)
}

// QuickEdit runs the full workflow: create project, upload images, edit and wait,
// then optionally export and download. It returns partial results alongside any
// error so callers can inspect what completed.
func (c *Client) QuickEdit(ctx context.Context, p QuickEditParams) (*QuickEditResult, error) {
	// Always return a non-nil result so callers can read it on any error, as
	// documented (validation errors included).
	result := &QuickEditResult{}

	if p.ProfileKey == 0 {
		return result, fmt.Errorf("imagen: QuickEdit requires a ProfileKey")
	}
	if len(p.ImagePaths) == 0 {
		return result, fmt.Errorf("imagen: QuickEdit requires at least one image path")
	}
	if p.Download && p.DownloadDir == "" {
		return result, fmt.Errorf("imagen: QuickEdit Download requires DownloadDir")
	}

	// Validate file types against the profile before creating any server-side
	// state, so an incompatible batch fails fast instead of after upload (parity
	// with the Python/Node quick-edit helpers).
	profile, err := c.GetProfile(ctx, p.ProfileKey)
	if err != nil {
		return result, err
	}
	if err := CheckFilesMatchProfileType(*profile, p.ImagePaths); err != nil {
		return result, err
	}

	uuid, err := c.CreateProject(ctx, p.ProjectName)
	if err != nil {
		return result, err
	}
	result.ProjectUUID = uuid

	summary, err := c.UploadImages(ctx, uuid, p.ImagePaths, p.Upload)
	if err != nil {
		return result, err
	}
	result.UploadSummary = summary
	if summary.Successful == 0 {
		return result, fmt.Errorf("imagen: QuickEdit: no images uploaded successfully")
	}

	edit := EditRequest{ProfileKey: p.ProfileKey, PhotographyType: p.PhotographyType, EditOptions: p.EditOptions}
	if err := c.EditAndWait(ctx, uuid, edit, p.Poll); err != nil {
		return result, err
	}

	editLinks, err := c.GetDownloadLinks(ctx, uuid)
	if err != nil {
		return result, err
	}
	result.EditLinks = editLinks.FilesList

	if p.Export {
		if err := c.ExportAndWait(ctx, uuid, p.Poll); err != nil {
			return result, err
		}
		exportLinks, err := c.GetExportDownloadLinks(ctx, uuid)
		if err != nil {
			return result, err
		}
		result.ExportLinks = exportLinks.FilesList
	}

	if p.Download {
		files, err := c.DownloadFiles(ctx, result.EditLinks, p.DownloadDir, nil)
		if err != nil {
			return result, err
		}
		result.DownloadedFiles = files

		if p.Export {
			exportDir := p.ExportDownloadDir
			if exportDir == "" {
				exportDir = filepath.Join(p.DownloadDir, "exported")
			}
			exported, err := c.DownloadFiles(ctx, result.ExportLinks, exportDir, nil)
			if err != nil {
				return result, err
			}
			result.ExportedFiles = exported
		}
	}

	return result, nil
}
