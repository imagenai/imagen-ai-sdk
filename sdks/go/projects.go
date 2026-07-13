package imagen

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
	"strconv"
)

// CreateProject creates a regular project and returns its UUID. name may be
// empty for a server-generated name; if set it must be unique per account.
func (c *Client) CreateProject(ctx context.Context, name string) (string, error) {
	return c.createProject(ctx, "/projects/", name)
}

func (c *Client) createProject(ctx context.Context, path, name string) (string, error) {
	var body any
	if name != "" {
		body = map[string]string{"name": name}
	}
	var out CreateProjectResponse
	if err := c.doJSON(ctx, apiRequest{method: http.MethodPost, path: path, body: body}, &out); err != nil {
		return "", err
	}
	if out.ProjectUUID == "" {
		return "", fmt.Errorf("imagen: create project response missing project_uuid")
	}
	return out.ProjectUUID, nil
}

// ListProjects returns a page of regular projects. Pass nil for defaults.
func (c *Client) ListProjects(ctx context.Context, opts *ListProjectsOptions) (*ProjectListResponse, error) {
	var out ProjectListResponse
	err := c.doJSON(ctx, apiRequest{
		method: http.MethodGet,
		path:   "/projects",
		query:  listProjectsQuery(opts),
	}, &out)
	if err != nil {
		return nil, err
	}
	return &out, nil
}

func listProjectsQuery(opts *ListProjectsOptions) url.Values {
	q := url.Values{}
	if opts == nil {
		return q
	}
	if opts.Size != nil {
		q.Set("size", strconv.Itoa(*opts.Size))
	}
	if opts.Page != nil {
		q.Set("page", strconv.Itoa(*opts.Page))
	}
	if opts.ClientType != nil {
		q.Set("client_type", *opts.ClientType)
	}
	if opts.IsArchived != nil {
		q.Set("is_archived", strconv.FormatBool(*opts.IsArchived))
	}
	if opts.GetThumbnail != nil {
		q.Set("get_thumbnail", strconv.FormatBool(*opts.GetThumbnail))
	}
	return q
}

// GetProject fetches a single project by UUID.
func (c *Client) GetProject(ctx context.Context, projectUUID string, getThumbnail bool) (*ProjectListItem, error) {
	q := url.Values{}
	if getThumbnail {
		q.Set("get_thumbnail", "true")
	}
	var out ProjectListItem
	err := c.doJSON(ctx, apiRequest{
		method: http.MethodGet,
		path:   "/projects/" + url.PathEscape(projectUUID),
		query:  q,
	}, &out)
	if err != nil {
		return nil, err
	}
	return &out, nil
}

// GetProjectUUIDByName resolves a project name to its UUID. It tolerates a bare
// string, {project_uuid}, or {uuid} response shape.
func (c *Client) GetProjectUUIDByName(ctx context.Context, name string) (string, error) {
	raw, err := c.do(ctx, apiRequest{
		method: http.MethodGet,
		path:   fmt.Sprintf("/projects/%s/uuid", url.PathEscape(name)),
	})
	if err != nil {
		return "", err
	}
	var asString string
	if err := json.Unmarshal(raw, &asString); err == nil && asString != "" {
		return asString, nil
	}
	var obj struct {
		ProjectUUID string `json:"project_uuid"`
		UUID        string `json:"uuid"`
	}
	if err := json.Unmarshal(raw, &obj); err != nil {
		return "", fmt.Errorf("imagen: decoding uuid response: %w", err)
	}
	if obj.ProjectUUID != "" {
		return obj.ProjectUUID, nil
	}
	if obj.UUID != "" {
		return obj.UUID, nil
	}
	return "", fmt.Errorf("imagen: uuid response for %q contained no uuid", name)
}

// GetUploadLinks requests presigned PUT URLs for the given files and returns a
// map of file name to upload URL.
func (c *Client) GetUploadLinks(ctx context.Context, projectUUID string, files []FileUploadInfo) (map[string]string, error) {
	var out UploadLinksResponse
	err := c.doJSON(ctx, apiRequest{
		method: http.MethodPost,
		path:   fmt.Sprintf("/projects/%s/get_temporary_upload_links", url.PathEscape(projectUUID)),
		body:   uploadLinksRequest{FilesList: files},
	}, &out)
	if err != nil {
		return nil, err
	}
	return uploadLinkMap(out), nil
}

func uploadLinkMap(out UploadLinksResponse) map[string]string {
	m := make(map[string]string, len(out.FilesList))
	for _, l := range out.FilesList {
		m[l.FileName] = l.UploadLink
	}
	return m
}

// StartEditing triggers a regular editing job. It validates edit.EditOptions and
// sends the mandatory explicitly-empty Content-Type header the /edit endpoint
// requires.
func (c *Client) StartEditing(ctx context.Context, projectUUID string, edit EditRequest) error {
	if err := edit.EditOptions.Validate(); err != nil {
		return err
	}
	empty := ""
	_, err := c.do(ctx, apiRequest{
		method:      http.MethodPost,
		path:        fmt.Sprintf("/projects/%s/edit", url.PathEscape(projectUUID)),
		body:        edit,
		contentType: &empty,
	})
	return err
}

// EditStatus polls the editing status for a project.
func (c *Client) EditStatus(ctx context.Context, projectUUID string) (*StatusDetails, error) {
	return c.status(ctx, fmt.Sprintf("/projects/%s/edit/status", url.PathEscape(projectUUID)))
}

// GetDownloadLinks returns the XMP download links produced by editing.
func (c *Client) GetDownloadLinks(ctx context.Context, projectUUID string) (*DownloadLinksList, error) {
	return c.downloadLinks(ctx, fmt.Sprintf("/projects/%s/edit/get_temporary_download_links", url.PathEscape(projectUUID)))
}

// StartExport starts exporting edited images to JPEG.
func (c *Client) StartExport(ctx context.Context, projectUUID string) error {
	_, err := c.do(ctx, apiRequest{
		method: http.MethodPost,
		path:   fmt.Sprintf("/projects/%s/export", url.PathEscape(projectUUID)),
	})
	return err
}

// ExportStatus polls the export status for a project.
func (c *Client) ExportStatus(ctx context.Context, projectUUID string) (*StatusDetails, error) {
	return c.status(ctx, fmt.Sprintf("/projects/%s/export/status", url.PathEscape(projectUUID)))
}

// GetExportDownloadLinks returns the JPEG export download links.
func (c *Client) GetExportDownloadLinks(ctx context.Context, projectUUID string) (*DownloadLinksList, error) {
	return c.downloadLinks(ctx, fmt.Sprintf("/projects/%s/export/get_temporary_download_links", url.PathEscape(projectUUID)))
}

// GetExportUploadLink returns a per-image presigned PUT URL for export.
func (c *Client) GetExportUploadLink(ctx context.Context, projectUUID, fileName string) (string, error) {
	return c.singleLink(ctx, fmt.Sprintf("/projects/%s/export/get_upload_link", url.PathEscape(projectUUID)), fileName, true)
}

// GetExportDownloadLink returns a per-image presigned GET URL for export.
func (c *Client) GetExportDownloadLink(ctx context.Context, projectUUID, fileName string) (string, error) {
	return c.singleLink(ctx, fmt.Sprintf("/projects/%s/export/get_download_link", url.PathEscape(projectUUID)), fileName, false)
}

// status is the shared status-poll decoder.
func (c *Client) status(ctx context.Context, path string) (*StatusDetails, error) {
	var out StatusDetails
	if err := c.doJSON(ctx, apiRequest{method: http.MethodGet, path: path}, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// downloadLinks is the shared download-links decoder.
func (c *Client) downloadLinks(ctx context.Context, path string) (*DownloadLinksList, error) {
	var out DownloadLinksList
	if err := c.doJSON(ctx, apiRequest{method: http.MethodGet, path: path}, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// singleLink fetches a single upload or download link keyed by file_name.
func (c *Client) singleLink(ctx context.Context, path, fileName string, upload bool) (string, error) {
	q := url.Values{}
	q.Set("file_name", fileName)
	if upload {
		var out SingleUploadLink
		if err := c.doJSON(ctx, apiRequest{method: http.MethodGet, path: path, query: q}, &out); err != nil {
			return "", err
		}
		return out.UploadLink, nil
	}
	var out SingleDownloadLink
	if err := c.doJSON(ctx, apiRequest{method: http.MethodGet, path: path, query: q}, &out); err != nil {
		return "", err
	}
	return out.DownloadLink, nil
}
