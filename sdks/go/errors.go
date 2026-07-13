package imagen

import (
	"errors"
	"fmt"
)

// Sentinel errors for use with errors.Is. APIError wraps the matching sentinel
// based on the HTTP status code, and the upload/download helpers wrap the
// category sentinels so callers can branch on failure kind.
var (
	// ErrUnauthorized is wrapped by an APIError with status 401.
	ErrUnauthorized = errors.New("imagen: unauthorized")
	// ErrBadRequest is wrapped by an APIError with status 400.
	ErrBadRequest = errors.New("imagen: bad request")
	// ErrUpload marks a failure while uploading bytes to storage.
	ErrUpload = errors.New("imagen: upload failed")
	// ErrDownload marks a failure while downloading bytes from storage.
	ErrDownload = errors.New("imagen: download failed")
	// ErrProject marks a project-level operation failure (e.g. editing failed).
	ErrProject = errors.New("imagen: project error")
)

// APIError is returned for any non-2xx HTTP response from the Imagen API. It
// carries the parsed error message when the server provides one, plus the raw
// body for debugging. Use errors.As to inspect it and errors.Is against the
// sentinels above to branch on status.
type APIError struct {
	StatusCode int
	Endpoint   string
	Message    string
	Body       string
}

func (e *APIError) Error() string {
	msg := e.Message
	if msg == "" {
		msg = e.Body
	}
	return fmt.Sprintf("imagen: API error %d on %s: %s", e.StatusCode, e.Endpoint, msg)
}

// Unwrap maps well-known status codes to sentinel errors so callers can write
// errors.Is(err, imagen.ErrUnauthorized).
func (e *APIError) Unwrap() error {
	switch e.StatusCode {
	case 401:
		return ErrUnauthorized
	case 400:
		return ErrBadRequest
	}
	return nil
}
