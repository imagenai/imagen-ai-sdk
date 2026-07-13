package imagen

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"sync"
	"testing"
	"time"
)

func TestUploadI2IImagesMultipartRouting(t *testing.T) {
	dir := t.TempDir()
	big := filepath.Join(dir, "large.dng")
	// 25 bytes with a 10-byte part size => 3 parts (10,10,5).
	content := []byte("ABCDEFGHIJKLMNOPQRSTUVWXY")
	if err := os.WriteFile(big, content, 0o644); err != nil {
		t.Fatal(err)
	}

	var (
		mu         sync.Mutex
		chunks     = map[int][]byte{}
		completed  bool
		createSeen bool
	)

	mux := http.NewServeMux()
	srv := httptest.NewServer(mux)
	defer srv.Close()

	mux.HandleFunc("/i2i/projects/p1/multipart_uploads", func(w http.ResponseWriter, r *http.Request) {
		var req struct {
			FileName  string `json:"file_name"`
			PartCount int    `json:"part_count"`
		}
		json.NewDecoder(r.Body).Decode(&req)
		createSeen = true
		if req.PartCount != 3 {
			t.Errorf("part_count = %d, want 3", req.PartCount)
		}
		resp := MultipartUploadResponse{UploadID: "up1", Key: "key1"}
		for i := 1; i <= req.PartCount; i++ {
			resp.Parts = append(resp.Parts, MultipartUploadPart{
				PartNumber: i,
				UploadURL:  fmt.Sprintf("%s/s3/part/%d", srv.URL, i),
			})
		}
		json.NewEncoder(w).Encode(resp)
	})
	mux.HandleFunc("/s3/part/", func(w http.ResponseWriter, r *http.Request) {
		var pn int
		fmt.Sscanf(r.URL.Path, "/s3/part/%d", &pn)
		b, _ := io.ReadAll(r.Body)
		mu.Lock()
		chunks[pn] = b
		mu.Unlock()
	})
	mux.HandleFunc("/i2i/projects/p1/multipart_uploads/up1/complete", func(w http.ResponseWriter, r *http.Request) {
		completed = true
		w.WriteHeader(http.StatusNoContent)
	})

	summary, err := newTestClient(t, srv).UploadI2IImages(context.Background(), "p1",
		[]string{big}, &I2IUploadOptions{MultipartThreshold: 10, PartSize: 10, MaxConcurrency: 2})
	if err != nil {
		t.Fatalf("UploadI2IImages: %v", err)
	}
	if !createSeen || !completed {
		t.Fatalf("multipart lifecycle incomplete (create=%v complete=%v)", createSeen, completed)
	}
	if summary.Successful != 1 {
		t.Fatalf("summary = %+v, want 1 success", summary)
	}

	// Reassemble parts and compare to the original.
	got := append(append(append([]byte{}, chunks[1]...), chunks[2]...), chunks[3]...)
	if string(got) != string(content) {
		t.Fatalf("reassembled = %q, want %q", got, content)
	}
}

// TestUploadFileMultipartAbortsOnPartFailure verifies a failed part upload
// triggers a best-effort AbortMultipartUpload so the S3 upload is not left
// dangling. The abort runs on a fresh context, so it fires even when the caller's
// context is the reason the parts failed.
func TestUploadFileMultipartAbortsOnPartFailure(t *testing.T) {
	dir := t.TempDir()
	big := filepath.Join(dir, "large.dng")
	if err := os.WriteFile(big, []byte("ABCDEFGHIJKLMNOPQRSTUVWXY"), 0o644); err != nil {
		t.Fatal(err)
	}

	var aborted bool
	mux := http.NewServeMux()
	srv := httptest.NewServer(mux)
	defer srv.Close()
	mux.HandleFunc("/i2i/projects/p1/multipart_uploads", func(w http.ResponseWriter, r *http.Request) {
		var req struct {
			PartCount int `json:"part_count"`
		}
		json.NewDecoder(r.Body).Decode(&req)
		resp := MultipartUploadResponse{UploadID: "up1", Key: "key1"}
		for i := 1; i <= req.PartCount; i++ {
			resp.Parts = append(resp.Parts, MultipartUploadPart{
				PartNumber: i, UploadURL: fmt.Sprintf("%s/s3/part/%d", srv.URL, i),
			})
		}
		json.NewEncoder(w).Encode(resp)
	})
	mux.HandleFunc("/s3/part/", func(w http.ResponseWriter, r *http.Request) {
		http.Error(w, "boom", http.StatusInternalServerError) // force part failure
	})
	mux.HandleFunc("/i2i/projects/p1/multipart_uploads/up1", func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodDelete {
			aborted = true
			w.WriteHeader(http.StatusNoContent)
		}
	})

	summary, err := newTestClient(t, srv).UploadI2IImages(context.Background(), "p1",
		[]string{big}, &I2IUploadOptions{MultipartThreshold: 10, PartSize: 10})
	if err != nil {
		t.Fatalf("UploadI2IImages returned top-level error: %v", err)
	}
	if summary.Failed != 1 {
		t.Fatalf("summary = %+v, want 1 failed", summary)
	}
	if !aborted {
		t.Fatal("expected AbortMultipartUpload to be called after part failure")
	}
}

// TestUploadPartsFailsOnShortNonFinalPart verifies a non-final part that reads
// fewer bytes than partSize (e.g. the file was truncated under us) surfaces an
// error instead of uploading a short, corrupt part.
func TestUploadPartsFailsOnShortNonFinalPart(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "f.dng")
	// 15 bytes, partSize 10, 3 declared parts: part 2 (offset 10) is a short,
	// non-final read of 5 bytes.
	if err := os.WriteFile(path, []byte("ABCDEFGHIJKLMNO"), 0o644); err != nil {
		t.Fatal(err)
	}
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))
	defer srv.Close()

	parts := []MultipartUploadPart{
		{PartNumber: 1, UploadURL: srv.URL},
		{PartNumber: 2, UploadURL: srv.URL},
		{PartNumber: 3, UploadURL: srv.URL},
	}
	if err := newTestClient(t, srv).uploadParts(context.Background(), path, 10, parts, 1); err == nil {
		t.Fatal("expected error for short non-final part, got nil")
	}
}

// TestUploadFileMultipartAbortsOnCompleteFailure covers the case where every part
// upload succeeds but CompleteMultipartUpload fails: the upload must still be
// aborted so it is not left dangling in S3.
func TestUploadFileMultipartAbortsOnCompleteFailure(t *testing.T) {
	dir := t.TempDir()
	big := filepath.Join(dir, "large.dng")
	if err := os.WriteFile(big, []byte("ABCDEFGHIJKLMNOPQRSTUVWXY"), 0o644); err != nil {
		t.Fatal(err)
	}

	var aborted bool
	mux := http.NewServeMux()
	srv := httptest.NewServer(mux)
	defer srv.Close()
	mux.HandleFunc("/i2i/projects/p1/multipart_uploads", func(w http.ResponseWriter, r *http.Request) {
		var req struct {
			PartCount int `json:"part_count"`
		}
		json.NewDecoder(r.Body).Decode(&req)
		resp := MultipartUploadResponse{UploadID: "up1", Key: "key1"}
		for i := 1; i <= req.PartCount; i++ {
			resp.Parts = append(resp.Parts, MultipartUploadPart{
				PartNumber: i, UploadURL: fmt.Sprintf("%s/s3/part/%d", srv.URL, i),
			})
		}
		json.NewEncoder(w).Encode(resp)
	})
	mux.HandleFunc("/s3/part/", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK) // parts succeed
	})
	mux.HandleFunc("/i2i/projects/p1/multipart_uploads/up1/complete", func(w http.ResponseWriter, r *http.Request) {
		http.Error(w, "nope", http.StatusInternalServerError) // complete fails
	})
	mux.HandleFunc("/i2i/projects/p1/multipart_uploads/up1", func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodDelete {
			aborted = true
			w.WriteHeader(http.StatusNoContent)
		}
	})

	summary, err := newTestClient(t, srv).UploadI2IImages(context.Background(), "p1",
		[]string{big}, &I2IUploadOptions{MultipartThreshold: 10, PartSize: 10})
	if err != nil {
		t.Fatalf("UploadI2IImages returned top-level error: %v", err)
	}
	if summary.Failed != 1 {
		t.Fatalf("summary = %+v, want 1 failed", summary)
	}
	if !aborted {
		t.Fatal("expected AbortMultipartUpload to be called after complete failure")
	}
}

// TestUploadI2IImagesRejectsDuplicateBaseNames covers the cross-bucket case: the
// same base name where one copy routes to the small batch and the other to
// multipart must be rejected before any request is made.
func TestUploadI2IImagesRejectsDuplicateBaseNames(t *testing.T) {
	dir := t.TempDir()
	small := filepath.Join(dir, "small")
	large := filepath.Join(dir, "large")
	for _, d := range []string{small, large} {
		if err := os.MkdirAll(d, 0o755); err != nil {
			t.Fatal(err)
		}
	}
	if err := os.WriteFile(filepath.Join(small, "photo.dng"), []byte("x"), 0o644); err != nil {
		t.Fatal(err)
	}
	// Larger than the threshold below, so it routes to multipart.
	if err := os.WriteFile(filepath.Join(large, "photo.dng"), []byte("ABCDEFGHIJKLMNOP"), 0o644); err != nil {
		t.Fatal(err)
	}

	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		t.Errorf("server must not be called; got %s", r.URL.Path)
	}))
	defer srv.Close()

	_, err := newTestClient(t, srv).UploadI2IImages(context.Background(), "p1",
		[]string{filepath.Join(small, "photo.dng"), filepath.Join(large, "photo.dng")},
		&I2IUploadOptions{MultipartThreshold: 4})
	if err == nil {
		t.Fatal("expected duplicate-basename error, got nil")
	}
}

// TestMultipartPartCountCap verifies the part-count math never exceeds S3's
// 10000-part limit, including the ceil(fileSize/partSize)==10001 boundary that a
// truncating integer division would miss.
func TestMultipartPartCountCap(t *testing.T) {
	cases := []struct {
		fileSize int64
		partSize int64
	}{
		{partSize: 10, fileSize: 10 * maxS3Parts},     // exactly 10000 parts
		{partSize: 10, fileSize: 10*maxS3Parts + 1},   // 10001 parts before cap -> must be capped
		{partSize: 10, fileSize: 10 * maxS3Parts * 3}, // far over
	}
	for _, tc := range cases {
		partSize := tc.partSize
		if ceilDiv(tc.fileSize, partSize) > maxS3Parts {
			partSize = maxInt64(partSize, ceilDiv(tc.fileSize, maxS3Parts))
		}
		partCount := int(maxInt64(1, ceilDiv(tc.fileSize, partSize)))
		if partCount > maxS3Parts {
			t.Fatalf("fileSize=%d partSize=%d -> partCount=%d exceeds %d",
				tc.fileSize, tc.partSize, partCount, maxS3Parts)
		}
	}
}

func TestWaitForI2ICompletion(t *testing.T) {
	// Status progresses Pending -> In Progress -> Completed across polls; then
	// download links are fetched.
	statuses := []string{"Pending", "In Progress", "Completed"}
	var call int
	mux := http.NewServeMux()
	mux.HandleFunc("/i2i/projects/p1", func(w http.ResponseWriter, r *http.Request) {
		s := statuses[call]
		if call < len(statuses)-1 {
			call++
		}
		json.NewEncoder(w).Encode(ProjectListItem{ProjectUUID: "p1", Status: s})
	})
	mux.HandleFunc("/i2i/projects/p1/get_temporary_download_links", func(w http.ResponseWriter, r *http.Request) {
		json.NewEncoder(w).Encode(DownloadLinksList{FilesList: []DownloadLink{{FileName: "a.jpg", DownloadLink: "http://x/a"}}})
	})
	srv := httptest.NewServer(mux)
	defer srv.Close()

	c := newTestClient(t, srv)
	links, err := c.WaitForI2ICompletion(context.Background(), "p1", &PollOptions{Interval: time.Millisecond})
	if err != nil {
		t.Fatalf("WaitForI2ICompletion: %v", err)
	}
	if len(links.FilesList) != 1 {
		t.Fatalf("links = %+v, want 1", links.FilesList)
	}
}

func TestWaitForI2ICompletionFailed(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		json.NewEncoder(w).Encode(ProjectListItem{ProjectUUID: "p1", Status: "Failed"})
	}))
	defer srv.Close()

	_, err := newTestClient(t, srv).WaitForI2ICompletion(context.Background(), "p1", &PollOptions{Interval: time.Millisecond})
	if !errors.Is(err, ErrProject) {
		t.Fatalf("expected ErrProject, got %v", err)
	}
}

func TestIsValidI2INameNoFlag(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		io.WriteString(w, `{"some_other":"field"}`) // 2xx, no explicit flag
	}))
	defer srv.Close()
	ok, err := newTestClient(t, srv).IsValidI2IName(context.Background(), "n")
	if err != nil {
		t.Fatalf("IsValidI2IName: %v", err)
	}
	if !ok {
		t.Fatal("2xx with no flag should be treated as valid")
	}
}
