package imagen

import (
	"bytes"
	"context"
	"crypto/md5"
	"encoding/base64"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"sort"
	"sync"
)

// UploadResult is the outcome of uploading a single file.
type UploadResult struct {
	FileName string
	Success  bool
	Err      error
}

// UploadSummary aggregates the results of an upload batch.
type UploadSummary struct {
	Total      int
	Successful int
	Failed     int
	Results    []UploadResult
}

// UploadOptions tunes UploadImages. The zero value is valid.
type UploadOptions struct {
	// CalculateMD5 computes and sends a base64 MD5 per file (integrity check).
	CalculateMD5 bool
	// MaxConcurrency overrides the client default for this call (>= 1).
	MaxConcurrency int
	// Progress, if set, is called after each file with (done, total, fileName).
	// It may be called from multiple goroutines; keep it lightweight and safe.
	Progress func(done, total int, fileName string)
}

// UploadImages requests presigned links for the given local files and uploads
// them to S3 concurrently. Paths with an unsupported extension, that cannot be
// stat'd, or that are not regular files (e.g. directories) are silently skipped
// and do not appear in the summary; if no valid files remain, an error is
// returned. Duplicate base names among the valid files are rejected up front,
// since uploads are keyed by base name. Per-file upload failures are recorded in the
// summary rather than aborting the whole batch. The Progress callback (if set) is
// invoked serially.
func (c *Client) UploadImages(ctx context.Context, projectUUID string, paths []string, opts *UploadOptions) (*UploadSummary, error) {
	if opts == nil {
		opts = &UploadOptions{}
	}
	infos, valid, err := prepareUploadInfos(paths, opts.CalculateMD5)
	if err != nil {
		return nil, err
	}
	if len(infos) == 0 {
		return nil, fmt.Errorf("imagen: no valid image files to upload")
	}
	if err := checkUniqueBaseNames(valid); err != nil {
		return nil, err
	}

	links, err := c.GetUploadLinks(ctx, projectUUID, infos)
	if err != nil {
		return nil, err
	}

	concurrency := c.maxConcurrency
	if opts.MaxConcurrency >= 1 {
		concurrency = opts.MaxConcurrency
	}
	return c.runUploads(ctx, valid, links, md5ByName(infos), concurrency, opts.Progress), nil
}

// md5ByName maps file name to base64 MD5 for the infos that carry one. When an
// upload link is presigned with a Content-MD5, S3 requires the matching header on
// the PUT, so the digest must be carried through to uploadToS3.
func md5ByName(infos []FileUploadInfo) map[string]string {
	m := make(map[string]string)
	for _, info := range infos {
		if info.MD5 != "" {
			m[info.FileName] = info.MD5
		}
	}
	return m
}

// prepareUploadInfos filters to supported, existing files and builds the upload
// info list (optionally with base64 MD5). It returns the infos and the parallel
// list of absolute paths.
func prepareUploadInfos(paths []string, calcMD5 bool) ([]FileUploadInfo, []string, error) {
	var infos []FileUploadInfo
	var valid []string
	for _, p := range paths {
		if !SupportedExtension(p) {
			continue
		}
		if fi, err := os.Stat(p); err != nil || !fi.Mode().IsRegular() {
			continue
		}
		info := FileUploadInfo{FileName: filepath.Base(p)}
		if calcMD5 {
			sum, err := fileMD5Base64(p)
			if err != nil {
				return nil, nil, fmt.Errorf("imagen: computing md5 for %s: %w", p, err)
			}
			info.MD5 = sum
		}
		infos = append(infos, info)
		valid = append(valid, p)
	}
	return infos, valid, nil
}

// runUploads uploads valid files concurrently, bounded by concurrency. md5s maps
// file name to base64 MD5 for files whose link was presigned with a Content-MD5.
func (c *Client) runUploads(ctx context.Context, paths []string, links map[string]string, md5s map[string]string, concurrency int, progress func(int, int, string)) *UploadSummary {
	total := len(paths)
	results := make([]UploadResult, total)
	sem := make(chan struct{}, concurrency)
	done := make(chan struct{})

	var completed int
	progressCh := make(chan string, total)
	go func() {
		for name := range progressCh {
			completed++
			if progress != nil {
				progress(completed, total, name)
			}
		}
		close(done)
	}()

	var wg sync.WaitGroup
	for i, p := range paths {
		name := filepath.Base(p)
		link, ok := links[name]
		if !ok {
			results[i] = UploadResult{FileName: name, Err: fmt.Errorf("imagen: no upload link returned for %s", name)}
			progressCh <- name
			continue
		}
		wg.Add(1)
		sem <- struct{}{}
		go func(i int, path, name, link string) {
			defer wg.Done()
			defer func() { <-sem }()
			if err := c.uploadToS3(ctx, path, link, md5s[name]); err != nil {
				results[i] = UploadResult{FileName: name, Err: fmt.Errorf("%w: %v", ErrUpload, err)}
			} else {
				results[i] = UploadResult{FileName: name, Success: true}
			}
			progressCh <- name
		}(i, p, name, link)
	}
	wg.Wait()
	close(progressCh)
	<-done

	return summarize(results)
}

func summarize(results []UploadResult) *UploadSummary {
	s := &UploadSummary{Total: len(results), Results: results}
	for _, r := range results {
		if r.Success {
			s.Successful++
		} else {
			s.Failed++
		}
	}
	sort.SliceStable(s.Results, func(i, j int) bool {
		return s.Results[i].FileName < s.Results[j].FileName
	})
	return s
}

// uploadToS3 streams the file's bytes to a presigned URL. The body is streamed
// (not buffered) so memory stays bounded regardless of file size or concurrency.
// When md5 is non-empty the link was presigned with a Content-MD5, so the header
// is sent to match the signature (and give S3 an integrity check).
func (c *Client) uploadToS3(ctx context.Context, path, uploadURL, md5 string) error {
	f, err := os.Open(path)
	if err != nil {
		return err
	}
	defer f.Close()
	fi, err := f.Stat()
	if err != nil {
		return err
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPut, uploadURL, f)
	if err != nil {
		return err
	}
	req.ContentLength = fi.Size()
	// GetBody lets the client re-send the body on redirect/retry.
	req.GetBody = func() (io.ReadCloser, error) { return os.Open(path) }
	if md5 != "" {
		req.Header.Set("Content-MD5", md5)
	}
	return c.sendUpload(req)
}

// putBytes PUTs an in-memory buffer to a presigned URL (used for multipart parts,
// whose chunks are already read into memory).
func (c *Client) putBytes(ctx context.Context, uploadURL string, data []byte) error {
	req, err := http.NewRequestWithContext(ctx, http.MethodPut, uploadURL, bytes.NewReader(data))
	if err != nil {
		return err
	}
	req.ContentLength = int64(len(data))
	return c.sendUpload(req)
}

// sendUpload executes an upload request and maps a non-2xx status to an error.
func (c *Client) sendUpload(req *http.Request) error {
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("S3 responded %d: %s", resp.StatusCode, string(body))
	}
	return nil
}

// fileMD5Base64 returns the base64-encoded MD5 digest of a file, streamed.
func fileMD5Base64(path string) (string, error) {
	f, err := os.Open(path)
	if err != nil {
		return "", err
	}
	defer f.Close()
	h := md5.New()
	if _, err := io.Copy(h, f); err != nil {
		return "", err
	}
	return base64.StdEncoding.EncodeToString(h.Sum(nil)), nil
}
