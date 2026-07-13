package imagen

import (
	"context"
	"fmt"
	"net/http"
	"net/url"
)

// EnhanceImage applies a quick AI tool to one image and returns the result.
func (c *Client) EnhanceImage(ctx context.Context, projectUUID, fileName string, req EnhanceRequest) (*EnhanceResult, error) {
	var out EnhanceResult
	err := c.doJSON(ctx, apiRequest{
		method: http.MethodPost,
		path:   fmt.Sprintf("/projects/%s/images/%s/enhance", url.PathEscape(projectUUID), url.PathEscape(fileName)),
		body:   req,
	}, &out)
	if err != nil {
		return nil, err
	}
	return &out, nil
}

// Copilot applies a natural-language instruction to one image.
func (c *Client) Copilot(ctx context.Context, projectUUID, fileName string, req CopilotRequest) (*EnhanceResult, error) {
	var out EnhanceResult
	err := c.doJSON(ctx, apiRequest{
		method: http.MethodPost,
		path:   fmt.Sprintf("/projects/%s/images/%s/copilot", url.PathEscape(projectUUID), url.PathEscape(fileName)),
		body:   req,
	}, &out)
	if err != nil {
		return nil, err
	}
	return &out, nil
}

// ResetCopilot clears the copilot conversation history for one image.
func (c *Client) ResetCopilot(ctx context.Context, projectUUID, fileName string, source ProjectSource) error {
	_, err := c.do(ctx, apiRequest{
		method: http.MethodDelete,
		path:   fmt.Sprintf("/projects/%s/images/%s/copilot", url.PathEscape(projectUUID), url.PathEscape(fileName)),
		body:   map[string]ProjectSource{"project_source": source},
	})
	return err
}

// Finalize generates final download URLs and upscales enhanced images. It
// returns the resulting download links.
func (c *Client) Finalize(ctx context.Context, projectUUID string, source ProjectSource) (*DownloadLinksList, error) {
	var out DownloadLinksList
	err := c.doJSON(ctx, apiRequest{
		method: http.MethodPost,
		path:   fmt.Sprintf("/projects/%s/finalize", url.PathEscape(projectUUID)),
		body:   map[string]ProjectSource{"project_source": source},
	}, &out)
	if err != nil {
		return nil, err
	}
	return &out, nil
}
