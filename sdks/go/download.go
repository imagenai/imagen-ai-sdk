package imagen

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"sync"
)

// DownloadOptions tunes DownloadFiles. The zero value is valid.
type DownloadOptions struct {
	// MaxConcurrency overrides the client default for this call (>= 1).
	MaxConcurrency int
	// Progress, if set, is called after each file with (done, total, fileName).
	// It is invoked serially (never from two goroutines at once).
	Progress func(done, total int, fileName string)
}

// DownloadFiles downloads each link into dir, creating dir if needed, and returns
// the paths written. It downloads concurrently; the first error is returned
// after all in-flight downloads settle, alongside any files that did succeed.
func (c *Client) DownloadFiles(ctx context.Context, links []DownloadLink, dir string, opts *DownloadOptions) ([]string, error) {
	if opts == nil {
		opts = &DownloadOptions{}
	}
	if len(links) == 0 {
		return nil, fmt.Errorf("imagen: no download links provided")
	}
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return nil, fmt.Errorf("imagen: creating download dir: %w", err)
	}

	concurrency := c.maxConcurrency
	if opts.MaxConcurrency >= 1 {
		concurrency = opts.MaxConcurrency
	}

	total := len(links)
	paths := make([]string, total)
	errs := make([]error, total)
	sem := make(chan struct{}, concurrency)
	var wg sync.WaitGroup
	var mu sync.Mutex
	var completed int

	for i, link := range links {
		wg.Add(1)
		sem <- struct{}{}
		go func(i int, link DownloadLink) {
			defer wg.Done()
			defer func() { <-sem }()
			dest := filepath.Join(dir, filepath.Base(link.FileName))
			if err := c.downloadOne(ctx, link.DownloadLink, dest); err != nil {
				errs[i] = fmt.Errorf("%w: %s: %v", ErrDownload, link.FileName, err)
			} else {
				paths[i] = dest
			}
			// Hold the lock across the callback so progress is reported serially
			// and in monotonic order, matching UploadImages.
			mu.Lock()
			completed++
			if opts.Progress != nil {
				opts.Progress(completed, total, link.FileName)
			}
			mu.Unlock()
		}(i, link)
	}
	wg.Wait()

	var written []string
	for _, p := range paths {
		if p != "" {
			written = append(written, p)
		}
	}
	for _, e := range errs {
		if e != nil {
			return written, e
		}
	}
	return written, nil
}

// downloadOne GETs a URL and writes the body to dest.
func (c *Client) downloadOne(ctx context.Context, downloadURL, dest string) error {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, downloadURL, nil)
	if err != nil {
		return err
	}
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("storage responded %d: %s", resp.StatusCode, string(body))
	}

	// Write to a temp file and rename on success so a failed copy never leaves a
	// truncated file at dest, and Close errors (which can surface deferred write
	// failures) are not swallowed.
	tmp, err := os.CreateTemp(filepath.Dir(dest), ".imagen-*.part")
	if err != nil {
		return err
	}
	tmpName := tmp.Name()
	if _, err := io.Copy(tmp, resp.Body); err != nil {
		tmp.Close()
		os.Remove(tmpName)
		return err
	}
	if err := tmp.Close(); err != nil {
		os.Remove(tmpName)
		return err
	}
	if err := os.Rename(tmpName, dest); err != nil {
		os.Remove(tmpName)
		return err
	}
	return nil
}
