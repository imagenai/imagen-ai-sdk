package imagen

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"strings"
	"time"
)

// DefaultBaseURL is the production Imagen AI API root.
const DefaultBaseURL = "https://api.imagen-ai.com/v1"

// DefaultMaxConcurrency bounds concurrent S3 uploads/downloads.
const DefaultMaxConcurrency = 10

// Logger is the minimal logging surface the client uses. The standard library's
// *log.Logger satisfies it. Logging defaults to off (see WithLogger).
type Logger interface {
	Printf(format string, v ...any)
}

type noopLogger struct{}

func (noopLogger) Printf(string, ...any) {}

// Client is a thread-safe Imagen AI API client. Create one with NewClient and
// reuse it across goroutines.
type Client struct {
	apiKey         string
	baseURL        string
	httpClient     *http.Client
	logger         Logger
	maxConcurrency int
}

// Option customizes a Client. Pass options to NewClient.
type Option func(*Client)

// WithBaseURL overrides the API root (useful for staging or a mock server).
func WithBaseURL(u string) Option {
	return func(c *Client) { c.baseURL = strings.TrimRight(u, "/") }
}

// WithHTTPClient supplies a custom *http.Client (timeouts, transport, proxy).
func WithHTTPClient(h *http.Client) Option {
	return func(c *Client) { c.httpClient = h }
}

// WithLogger enables debug logging through the given Logger.
func WithLogger(l Logger) Option {
	return func(c *Client) {
		if l != nil {
			c.logger = l
		}
	}
}

// WithMaxConcurrency caps concurrent uploads and downloads (must be >= 1).
func WithMaxConcurrency(n int) Option {
	return func(c *Client) {
		if n >= 1 {
			c.maxConcurrency = n
		}
	}
}

// NewClient creates a client for the given API key. It returns an error if the
// key is empty.
func NewClient(apiKey string, opts ...Option) (*Client, error) {
	if strings.TrimSpace(apiKey) == "" {
		return nil, fmt.Errorf("imagen: api key must not be empty")
	}
	c := &Client{
		apiKey:         strings.TrimSpace(apiKey),
		baseURL:        DefaultBaseURL,
		httpClient:     &http.Client{Timeout: 60 * time.Second},
		logger:         noopLogger{},
		maxConcurrency: DefaultMaxConcurrency,
	}
	for _, opt := range opts {
		opt(c)
	}
	return c, nil
}

// StdLogger adapts the standard library logger to the Logger interface.
func StdLogger(l *log.Logger) Logger { return l }

// apiRequest describes a single call to the Imagen API.
type apiRequest struct {
	method string
	path   string     // joined onto baseURL
	query  url.Values // optional
	body   any        // JSON-encoded when non-nil
	// contentType, when non-nil, sets the Content-Type header to *contentType
	// (an empty string sends an explicitly-empty header, required by /edit).
	// When nil, application/json is used for a non-nil body and no header
	// otherwise.
	contentType *string
}

// do executes an API request and returns the envelope-unwrapped JSON body.
func (c *Client) do(ctx context.Context, r apiRequest) (json.RawMessage, error) {
	endpoint := c.baseURL + r.path
	if len(r.query) > 0 {
		endpoint += "?" + r.query.Encode()
	}

	var bodyReader io.Reader
	if r.body != nil {
		raw, err := json.Marshal(r.body)
		if err != nil {
			return nil, fmt.Errorf("imagen: encoding request body: %w", err)
		}
		bodyReader = bytes.NewReader(raw)
	}

	req, err := http.NewRequestWithContext(ctx, r.method, endpoint, bodyReader)
	if err != nil {
		return nil, fmt.Errorf("imagen: building request: %w", err)
	}
	req.Header.Set("x-api-key", c.apiKey)
	switch {
	case r.contentType != nil:
		req.Header.Set("Content-Type", *r.contentType)
	case r.body != nil:
		req.Header.Set("Content-Type", "application/json")
	}

	c.logger.Printf("imagen: %s %s", r.method, endpoint)

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("imagen: %s %s: %w", r.method, r.path, err)
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("imagen: reading response body: %w", err)
	}

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return nil, &APIError{
			StatusCode: resp.StatusCode,
			Endpoint:   r.path,
			Message:    parseErrorMessage(respBody),
			Body:       string(respBody),
		}
	}

	return unwrapEnvelope(respBody), nil
}

// doJSON executes a request and unmarshals the unwrapped body into out.
func (c *Client) doJSON(ctx context.Context, r apiRequest, out any) error {
	raw, err := c.do(ctx, r)
	if err != nil {
		return err
	}
	if out == nil || len(raw) == 0 {
		return nil
	}
	if err := json.Unmarshal(raw, out); err != nil {
		return fmt.Errorf("imagen: decoding %s response: %w", r.path, err)
	}
	return nil
}

// unwrapEnvelope implements the response-envelope rule: if the body is an object
// whose only key is "data", the value of "data" is returned; otherwise the body
// is returned as-is.
func unwrapEnvelope(body []byte) json.RawMessage {
	trimmed := bytes.TrimSpace(body)
	if len(trimmed) == 0 || trimmed[0] != '{' {
		return trimmed
	}
	var obj map[string]json.RawMessage
	if err := json.Unmarshal(trimmed, &obj); err != nil {
		return trimmed
	}
	if len(obj) == 1 {
		if data, ok := obj["data"]; ok {
			return data
		}
	}
	return trimmed
}

// parseErrorMessage best-effort extracts a human message from an error body.
// The API uses {"error":{"message":"..."}} or {"detail":"..."}.
func parseErrorMessage(body []byte) string {
	var e struct {
		Error struct {
			Message string `json:"message"`
		} `json:"error"`
		Detail string `json:"detail"`
	}
	if err := json.Unmarshal(body, &e); err == nil {
		if e.Error.Message != "" {
			return e.Error.Message
		}
		if e.Detail != "" {
			return e.Detail
		}
	}
	return ""
}
