package imagen

import (
	"context"
	"crypto/md5"
	"encoding/base64"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// newTestClient wires a client to a test server.
func newTestClient(t *testing.T, srv *httptest.Server) *Client {
	t.Helper()
	c, err := NewClient("test-key", WithBaseURL(srv.URL))
	if err != nil {
		t.Fatalf("NewClient: %v", err)
	}
	return c
}

func TestNewClientRejectsEmptyKey(t *testing.T) {
	if _, err := NewClient("  "); err == nil {
		t.Fatal("expected error for empty api key")
	}
}

func TestUnwrapEnvelope(t *testing.T) {
	cases := []struct {
		name string
		in   string
		want string
	}{
		{"production root", `{"project_uuid":"abc"}`, `{"project_uuid":"abc"}`},
		{"legacy data wrap", `{"data":{"project_uuid":"abc"}}`, `{"project_uuid":"abc"}`},
		{"bare list", `[1,2,3]`, `[1,2,3]`},
		{"data plus sibling not unwrapped", `{"data":{"x":1},"extra":2}`, `{"data":{"x":1},"extra":2}`},
		{"data string value", `{"data":"xyz"}`, `"xyz"`},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got := strings.TrimSpace(string(unwrapEnvelope([]byte(tc.in))))
			if got != tc.want {
				t.Fatalf("unwrapEnvelope(%s) = %s, want %s", tc.in, got, tc.want)
			}
		})
	}
}

func TestEditOptionsValidate(t *testing.T) {
	if err := (EditOptions{Crop: Bool(true), HeadshotCrop: Bool(true)}).Validate(); err == nil {
		t.Fatal("expected error for two crop modes")
	}
	if err := (EditOptions{Straighten: Bool(true), PerspectiveCorrection: Bool(true)}).Validate(); err == nil {
		t.Fatal("expected error for two straighten modes")
	}
	if err := (EditOptions{Crop: Bool(true), Straighten: Bool(true)}).Validate(); err != nil {
		t.Fatalf("valid combo rejected: %v", err)
	}
	// false-valued pointers should not count as "set".
	if err := (EditOptions{Crop: Bool(false), HeadshotCrop: Bool(true)}).Validate(); err != nil {
		t.Fatalf("false crop should not count: %v", err)
	}
}

func TestCreateProject(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("x-api-key") != "test-key" {
			t.Errorf("missing api key header")
		}
		if r.URL.Path != "/projects/" || r.Method != http.MethodPost {
			t.Errorf("unexpected request %s %s", r.Method, r.URL.Path)
		}
		var body map[string]string
		json.NewDecoder(r.Body).Decode(&body)
		if body["name"] != "My Photos" {
			t.Errorf("name not forwarded, got %v", body)
		}
		// legacy data-wrapped response
		io.WriteString(w, `{"data":{"project_uuid":"proj-123"}}`)
	}))
	defer srv.Close()

	uuid, err := newTestClient(t, srv).CreateProject(context.Background(), "My Photos")
	if err != nil {
		t.Fatalf("CreateProject: %v", err)
	}
	if uuid != "proj-123" {
		t.Fatalf("uuid = %q, want proj-123", uuid)
	}
}

func TestStartEditingSendsEmptyContentType(t *testing.T) {
	var gotCT string
	var gotCTPresent bool
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotCT = r.Header.Get("Content-Type")
		_, gotCTPresent = r.Header["Content-Type"]
		io.WriteString(w, `{"message":"ok"}`)
	}))
	defer srv.Close()

	edit := EditRequest{ProfileKey: 1, PhotographyType: PhotographyTypePortraits}
	edit.Crop = Bool(true)
	if err := newTestClient(t, srv).StartEditing(context.Background(), "p1", edit); err != nil {
		t.Fatalf("StartEditing: %v", err)
	}
	if !gotCTPresent {
		t.Fatal("Content-Type header should be present (explicitly empty)")
	}
	if gotCT != "" {
		t.Fatalf("Content-Type = %q, want empty", gotCT)
	}
}

func TestStartEditingValidatesOptions(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		t.Error("request should not be sent when options are invalid")
	}))
	defer srv.Close()

	edit := EditRequest{ProfileKey: 1}
	edit.Crop = Bool(true)
	edit.PortraitCrop = Bool(true)
	if err := newTestClient(t, srv).StartEditing(context.Background(), "p1", edit); err == nil {
		t.Fatal("expected validation error")
	}
}

func TestAPIErrorUnauthorized(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusUnauthorized)
		io.WriteString(w, `{"error":{"message":"bad key"}}`)
	}))
	defer srv.Close()

	_, err := newTestClient(t, srv).GetProfiles(context.Background())
	if err == nil {
		t.Fatal("expected error")
	}
	if !errors.Is(err, ErrUnauthorized) {
		t.Fatalf("errors.Is(ErrUnauthorized) = false for %v", err)
	}
	var apiErr *APIError
	if !errors.As(err, &apiErr) {
		t.Fatalf("errors.As(*APIError) failed for %v", err)
	}
	if apiErr.Message != "bad key" {
		t.Fatalf("message = %q, want 'bad key'", apiErr.Message)
	}
}

func TestGetProfilesBothShapes(t *testing.T) {
	for _, body := range []string{
		`[{"profile_key":1,"profile_name":"A"}]`,
		`{"data":{"profiles":[{"profile_key":1,"profile_name":"A"}]}}`,
	} {
		srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			io.WriteString(w, body)
		}))
		profiles, err := newTestClient(t, srv).GetProfiles(context.Background())
		srv.Close()
		if err != nil {
			t.Fatalf("GetProfiles(%s): %v", body, err)
		}
		if len(profiles) != 1 || profiles[0].ProfileKey != 1 {
			t.Fatalf("GetProfiles(%s) = %+v", body, profiles)
		}
	}
}

func TestGetProjectUUIDByNameShapes(t *testing.T) {
	for _, tc := range []struct{ body, want string }{
		{`"uuid-bare"`, "uuid-bare"},
		{`{"project_uuid":"uuid-a"}`, "uuid-a"},
		{`{"uuid":"uuid-b"}`, "uuid-b"},
	} {
		srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			io.WriteString(w, tc.body)
		}))
		got, err := newTestClient(t, srv).GetProjectUUIDByName(context.Background(), "name")
		srv.Close()
		if err != nil {
			t.Fatalf("GetProjectUUIDByName(%s): %v", tc.body, err)
		}
		if got != tc.want {
			t.Fatalf("GetProjectUUIDByName(%s) = %q, want %q", tc.body, got, tc.want)
		}
	}
}

func TestUploadImagesFlow(t *testing.T) {
	dir := t.TempDir()
	img := filepath.Join(dir, "photo.dng")
	skipped := filepath.Join(dir, "notes.txt") // unsupported extension, must be ignored
	if err := os.WriteFile(img, []byte("rawbytes"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(skipped, []byte("x"), 0o644); err != nil {
		t.Fatal(err)
	}

	var putBody string
	mux := http.NewServeMux()
	srv := httptest.NewServer(mux)
	defer srv.Close()

	const s3Path = "/s3/photo.dng"
	mux.HandleFunc("/projects/p1/get_temporary_upload_links", func(w http.ResponseWriter, r *http.Request) {
		var req uploadLinksRequest
		json.NewDecoder(r.Body).Decode(&req)
		if len(req.FilesList) != 1 || req.FilesList[0].FileName != "photo.dng" {
			t.Errorf("unexpected files_list: %+v", req.FilesList)
		}
		resp := UploadLinksResponse{FilesList: []UploadLink{{FileName: "photo.dng", UploadLink: srv.URL + s3Path}}}
		json.NewEncoder(w).Encode(resp)
	})
	var gotMD5 string
	mux.HandleFunc(s3Path, func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPut {
			t.Errorf("expected PUT, got %s", r.Method)
		}
		gotMD5 = r.Header.Get("Content-MD5")
		b, _ := io.ReadAll(r.Body)
		putBody = string(b)
	})

	summary, err := newTestClient(t, srv).UploadImages(
		context.Background(), "p1", []string{img, skipped}, &UploadOptions{CalculateMD5: true})
	if err != nil {
		t.Fatalf("UploadImages: %v", err)
	}
	if summary.Total != 1 || summary.Successful != 1 || summary.Failed != 0 {
		t.Fatalf("summary = %+v, want 1/1/0", summary)
	}
	if putBody != "rawbytes" {
		t.Fatalf("S3 received %q, want rawbytes", putBody)
	}
	// CalculateMD5 was set, so the S3 PUT must carry a Content-MD5 header matching
	// the file's base64 MD5 (S3 requires it to match the presigned signature).
	sum := md5.Sum([]byte("rawbytes"))
	wantMD5 := base64.StdEncoding.EncodeToString(sum[:])
	if gotMD5 != wantMD5 {
		t.Fatalf("Content-MD5 = %q, want %q", gotMD5, wantMD5)
	}
}

// TestUploadImagesRejectsDuplicateBaseNames proves the duplicate-basename guard
// fires before any upload-link request: same file name from two directories must
// error without the server being hit.
func TestUploadImagesRejectsDuplicateBaseNames(t *testing.T) {
	dir := t.TempDir()
	a := filepath.Join(dir, "a")
	b := filepath.Join(dir, "b")
	for _, d := range []string{a, b} {
		if err := os.MkdirAll(d, 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(filepath.Join(d, "photo.dng"), []byte("x"), 0o644); err != nil {
			t.Fatal(err)
		}
	}

	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		t.Errorf("server must not be called; got %s", r.URL.Path)
	}))
	defer srv.Close()

	_, err := newTestClient(t, srv).UploadImages(
		context.Background(), "p1",
		[]string{filepath.Join(a, "photo.dng"), filepath.Join(b, "photo.dng")}, nil)
	if err == nil {
		t.Fatal("expected duplicate-basename error, got nil")
	}
}

// TestDownloadFilesEmptyLinks pins parity with the Python SDK, which raises on an
// empty link list rather than silently succeeding.
func TestDownloadFilesEmptyLinks(t *testing.T) {
	c, err := NewClient("k")
	if err != nil {
		t.Fatal(err)
	}
	if _, err := c.DownloadFiles(context.Background(), nil, t.TempDir(), nil); err == nil {
		t.Fatal("expected error for empty download links, got nil")
	}
}

// TestQuickEditReturnsNonNilResultOnValidationError pins the documented contract
// that QuickEdit always returns a non-nil result, so callers can read it on error
// without a nil dereference.
func TestQuickEditReturnsNonNilResultOnValidationError(t *testing.T) {
	c, err := NewClient("k")
	if err != nil {
		t.Fatal(err)
	}
	res, err := c.QuickEdit(context.Background(), QuickEditParams{}) // missing ProfileKey
	if err == nil {
		t.Fatal("expected validation error, got nil")
	}
	if res == nil {
		t.Fatal("result must be non-nil on validation error")
	}
}

// TestQuickEditRejectsProfileTypeMismatch proves QuickEdit validates file types
// against the profile before creating any server-side state: a JPG batch against
// a RAW profile must error without the project endpoints being hit.
func TestQuickEditRejectsProfileTypeMismatch(t *testing.T) {
	dir := t.TempDir()
	jpg := filepath.Join(dir, "photo.jpg")
	if err := os.WriteFile(jpg, []byte("x"), 0o644); err != nil {
		t.Fatal(err)
	}

	mux := http.NewServeMux()
	srv := httptest.NewServer(mux)
	defer srv.Close()
	mux.HandleFunc("/profiles", func(w http.ResponseWriter, r *http.Request) {
		json.NewEncoder(w).Encode([]Profile{{ProfileKey: 7, ImageType: "RAW"}})
	})
	mux.HandleFunc("/projects/", func(w http.ResponseWriter, r *http.Request) {
		t.Errorf("project endpoints must not be called on type mismatch: %s", r.URL.Path)
	})

	_, err := newTestClient(t, srv).QuickEdit(context.Background(), QuickEditParams{
		ProfileKey: 7, ImagePaths: []string{jpg},
	})
	if err == nil {
		t.Fatal("expected profile-type mismatch error, got nil")
	}
}
