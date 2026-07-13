package imagen

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
)

// GetProfiles lists the editing profiles available to the account.
func (c *Client) GetProfiles(ctx context.Context) ([]Profile, error) {
	raw, err := c.do(ctx, apiRequest{method: http.MethodGet, path: "/profiles"})
	if err != nil {
		return nil, err
	}
	return decodeProfiles(raw)
}

// decodeProfiles tolerates both the bare-list production shape and the legacy
// {profiles:[...]} shape (the top-level {data:...} wrapper is already stripped).
func decodeProfiles(raw json.RawMessage) ([]Profile, error) {
	var list []Profile
	if err := json.Unmarshal(raw, &list); err == nil {
		return list, nil
	}
	var wrapped struct {
		Profiles []Profile `json:"profiles"`
	}
	if err := json.Unmarshal(raw, &wrapped); err != nil {
		return nil, fmt.Errorf("imagen: decoding profiles response: %w", err)
	}
	return wrapped.Profiles, nil
}

// GetProfile returns the single profile matching profileKey, or an error if none
// matches.
func (c *Client) GetProfile(ctx context.Context, profileKey int) (*Profile, error) {
	profiles, err := c.GetProfiles(ctx)
	if err != nil {
		return nil, err
	}
	for i := range profiles {
		if profiles[i].ProfileKey == profileKey {
			return &profiles[i], nil
		}
	}
	return nil, fmt.Errorf("imagen: no profile with key %d", profileKey)
}

// GetSkyReplacementTemplates lists sky-replacement templates. Use a template's
// ID for EditOptions.SkyReplacementTemplateID.
func (c *Client) GetSkyReplacementTemplates(ctx context.Context) ([]SkyTemplate, error) {
	raw, err := c.do(ctx, apiRequest{method: http.MethodGet, path: "/projects/sky_replacement/templates"})
	if err != nil {
		return nil, err
	}
	// PROD returns {"templates":[...]}; the spec documents a bare list. Tolerate both.
	var list []SkyTemplate
	if err := json.Unmarshal(raw, &list); err == nil {
		return list, nil
	}
	var wrapped struct {
		Templates []SkyTemplate `json:"templates"`
	}
	if err := json.Unmarshal(raw, &wrapped); err != nil {
		return nil, fmt.Errorf("imagen: decoding sky templates response: %w", err)
	}
	return wrapped.Templates, nil
}

// GetAITools lists the available quick AI tools for a project. source selects
// whether the project is a regular or I2I project.
func (c *Client) GetAITools(ctx context.Context, projectUUID string, source ProjectSource) (*AIToolsResponse, error) {
	q := url.Values{}
	q.Set("project_source", string(source))
	var out AIToolsResponse
	err := c.doJSON(ctx, apiRequest{
		method: http.MethodGet,
		path:   fmt.Sprintf("/projects/%s/ai-tools", url.PathEscape(projectUUID)),
		query:  q,
	}, &out)
	if err != nil {
		return nil, err
	}
	return &out, nil
}
