package imagen

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"strconv"
	"sync"
	"time"
)

// I2IDefaultPartSize is the S3 multipart part size (and the default threshold
// above which a file is uploaded via multipart). S3 requires parts >= 5 MB
// except the final part.
const I2IDefaultPartSize = 64 << 20 // 64 MB

// maxS3Parts is S3's hard limit on parts per multipart upload.
const maxS3Parts = 10000

// CreateI2IProject creates an image-to-image project and returns its UUID.
func (c *Client) CreateI2IProject(ctx context.Context, name string) (string, error) {
	return c.createProject(ctx, "/i2i/projects/", name)
}

// ListI2IProjects returns a page of I2I projects. Only Size, Page and IsArchived
// are honoured for I2I.
func (c *Client) ListI2IProjects(ctx context.Context, opts *ListProjectsOptions) (*ProjectListResponse, error) {
	q := url.Values{}
	if opts != nil {
		if opts.Size != nil {
			q.Set("size", strconv.Itoa(*opts.Size))
		}
		if opts.Page != nil {
			q.Set("page", strconv.Itoa(*opts.Page))
		}
		if opts.IsArchived != nil {
			q.Set("is_archived", strconv.FormatBool(*opts.IsArchived))
		}
	}
	var out ProjectListResponse
	if err := c.doJSON(ctx, apiRequest{method: http.MethodGet, path: "/i2i/projects", query: q}, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// IsValidI2IName reports whether an I2I project name is available. A 2xx response
// with no explicit flag is treated as valid.
func (c *Client) IsValidI2IName(ctx context.Context, name string) (bool, error) {
	q := url.Values{}
	q.Set("name", name)
	raw, err := c.do(ctx, apiRequest{method: http.MethodGet, path: "/i2i/projects/is_valid_name", query: q})
	if err != nil {
		return false, err
	}
	var asBool bool
	if err := json.Unmarshal(raw, &asBool); err == nil {
		return asBool, nil
	}
	var obj struct {
		IsValid *bool `json:"is_valid"`
		Valid   *bool `json:"valid"`
	}
	if err := json.Unmarshal(raw, &obj); err == nil {
		if obj.IsValid != nil {
			return *obj.IsValid, nil
		}
		if obj.Valid != nil {
			return *obj.Valid, nil
		}
	}
	// 2xx with no explicit flag: treat as valid.
	return true, nil
}

// GetI2IProject fetches a single I2I project by UUID.
func (c *Client) GetI2IProject(ctx context.Context, projectUUID string, getThumbnail bool) (*ProjectListItem, error) {
	q := url.Values{}
	if getThumbnail {
		q.Set("get_thumbnail", "true")
	}
	var out ProjectListItem
	err := c.doJSON(ctx, apiRequest{
		method: http.MethodGet,
		path:   "/i2i/projects/" + url.PathEscape(projectUUID),
		query:  q,
	}, &out)
	if err != nil {
		return nil, err
	}
	return &out, nil
}

// GetI2IUploadLinks requests batched presigned PUT URLs for small files and
// returns a map of file name to upload URL.
func (c *Client) GetI2IUploadLinks(ctx context.Context, projectUUID string, files []FileUploadInfo) (map[string]string, error) {
	var out UploadLinksResponse
	err := c.doJSON(ctx, apiRequest{
		method: http.MethodPost,
		path:   fmt.Sprintf("/i2i/projects/%s/get_temporary_upload_links", url.PathEscape(projectUUID)),
		body:   uploadLinksRequest{FilesList: files, ClientType: "API"},
	}, &out)
	if err != nil {
		return nil, err
	}
	return uploadLinkMap(out), nil
}

// GetI2IUploadLink returns a single presigned PUT URL (advanced use).
func (c *Client) GetI2IUploadLink(ctx context.Context, projectUUID, fileName string) (string, error) {
	return c.singleLink(ctx, fmt.Sprintf("/i2i/projects/%s/get_upload_link", url.PathEscape(projectUUID)), fileName, true)
}

// CreateMultipartUpload starts an S3 multipart upload and returns per-part
// presigned URLs. partCount must be between 1 and 10000.
func (c *Client) CreateMultipartUpload(ctx context.Context, projectUUID, fileName string, partCount int) (*MultipartUploadResponse, error) {
	var out MultipartUploadResponse
	err := c.doJSON(ctx, apiRequest{
		method: http.MethodPost,
		path:   fmt.Sprintf("/i2i/projects/%s/multipart_uploads", url.PathEscape(projectUUID)),
		body:   map[string]any{"file_name": fileName, "part_count": partCount},
	}, &out)
	if err != nil {
		return nil, err
	}
	return &out, nil
}

// CompleteMultipartUpload finalizes a multipart upload.
func (c *Client) CompleteMultipartUpload(ctx context.Context, projectUUID, uploadID, fileName string) error {
	_, err := c.do(ctx, apiRequest{
		method: http.MethodPost,
		path:   fmt.Sprintf("/i2i/projects/%s/multipart_uploads/%s/complete", url.PathEscape(projectUUID), url.PathEscape(uploadID)),
		body:   map[string]string{"file_name": fileName},
	})
	return err
}

// AbortMultipartUpload cancels a multipart upload identified by its storage key.
func (c *Client) AbortMultipartUpload(ctx context.Context, projectUUID, uploadID, key string) error {
	_, err := c.do(ctx, apiRequest{
		method: http.MethodDelete,
		path:   fmt.Sprintf("/i2i/projects/%s/multipart_uploads/%s", url.PathEscape(projectUUID), url.PathEscape(uploadID)),
		body:   map[string]string{"key": key},
	})
	return err
}

// StartI2IEditing triggers I2I editing and returns immediately. Detect completion
// via the callback_url webhook or WaitForI2ICompletion (which polls the project's
// status field). opts may be nil.
func (c *Client) StartI2IEditing(ctx context.Context, projectUUID string, opts *I2IEditOptions) error {
	var body any
	if opts != nil {
		body = opts
	}
	_, err := c.do(ctx, apiRequest{
		method: http.MethodPost,
		path:   fmt.Sprintf("/i2i/projects/%s/edit", url.PathEscape(projectUUID)),
		body:   body,
	})
	return err
}

// GetI2IDownloadLinks returns all I2I result download links.
func (c *Client) GetI2IDownloadLinks(ctx context.Context, projectUUID string) (*DownloadLinksList, error) {
	return c.downloadLinks(ctx, fmt.Sprintf("/i2i/projects/%s/get_temporary_download_links", url.PathEscape(projectUUID)))
}

// GetI2IDownloadLink returns a single I2I result download link.
func (c *Client) GetI2IDownloadLink(ctx context.Context, projectUUID, fileName string) (string, error) {
	return c.singleLink(ctx, fmt.Sprintf("/i2i/projects/%s/get_download_link", url.PathEscape(projectUUID)), fileName, false)
}

// I2IUploadOptions tunes UploadI2IImages. The zero value uses the defaults.
type I2IUploadOptions struct {
	// CalculateMD5 computes and sends a base64 MD5 for the small-file batch.
	CalculateMD5 bool
	// MultipartThreshold is the size in bytes above which a file uses multipart
	// upload (default I2IDefaultPartSize, 64 MB).
	MultipartThreshold int64
	// PartSize is the bytes per multipart part (default I2IDefaultPartSize).
	PartSize int64
	// MaxConcurrency overrides the client default for both small-file uploads
	// and multipart part uploads (>= 1).
	MaxConcurrency int
	// Progress, if set, is called after each small file with (done, total, name).
	Progress func(done, total int, fileName string)
}

// UploadI2IImages uploads files to an I2I project, routing each by size: files at
// or below the threshold are batched into single PUTs, larger files use S3
// multipart upload. Files with an unsupported extension or that cannot be stat'd
// are silently skipped and do not appear in the summary (matching UploadImages);
// if no valid files remain, an error is returned.
func (c *Client) UploadI2IImages(ctx context.Context, projectUUID string, paths []string, opts *I2IUploadOptions) (*UploadSummary, error) {
	if opts == nil {
		opts = &I2IUploadOptions{}
	}
	threshold := opts.MultipartThreshold
	if threshold <= 0 {
		threshold = I2IDefaultPartSize
	}
	partSize := opts.PartSize
	if partSize <= 0 {
		partSize = I2IDefaultPartSize
	}
	concurrency := c.maxConcurrency
	if opts.MaxConcurrency >= 1 {
		concurrency = opts.MaxConcurrency
	}

	small, large, err := c.routeBySize(paths, threshold)
	if err != nil {
		return nil, err
	}
	if len(small) == 0 && len(large) == 0 {
		return nil, fmt.Errorf("imagen: no valid image files to upload")
	}
	if err := checkUniqueBaseNames(append(append([]string{}, small...), large...)); err != nil {
		return nil, err
	}

	var results []UploadResult

	if len(small) > 0 {
		infos, valid, err := prepareUploadInfos(small, opts.CalculateMD5)
		if err != nil {
			return nil, err
		}
		links, err := c.GetI2IUploadLinks(ctx, projectUUID, infos)
		if err != nil {
			return nil, err
		}
		results = append(results, c.runUploads(ctx, valid, links, md5ByName(infos), concurrency, opts.Progress).Results...)
	}

	for _, path := range large {
		name := baseName(path)
		if err := c.uploadFileMultipart(ctx, projectUUID, path, partSize, concurrency); err != nil {
			results = append(results, UploadResult{FileName: name, Err: fmt.Errorf("%w: %v", ErrUpload, err)})
		} else {
			results = append(results, UploadResult{FileName: name, Success: true})
		}
	}

	return summarize(results), nil
}

// routeBySize splits supported, existing files into small (<= threshold) and
// large (> threshold) buckets.
func (c *Client) routeBySize(paths []string, threshold int64) (small, large []string, err error) {
	for _, p := range paths {
		if !SupportedExtension(p) {
			continue
		}
		fi, statErr := os.Stat(p)
		if statErr != nil || !fi.Mode().IsRegular() {
			continue
		}
		if fi.Size() > threshold {
			large = append(large, p)
		} else {
			small = append(small, p)
		}
	}
	return small, large, nil
}

// uploadFileMultipart uploads one large file via S3 multipart upload, aborting
// the upload on failure.
func (c *Client) uploadFileMultipart(ctx context.Context, projectUUID, path string, partSize int64, concurrency int) error {
	fi, err := os.Stat(path)
	if err != nil {
		return err
	}
	fileSize := fi.Size()

	// S3 allows at most 10000 parts; grow partSize to stay within that. Use ceil
	// division so a file needing exactly 10001 parts is caught (integer
	// fileSize/partSize would round down and miss it).
	if ceilDiv(fileSize, partSize) > maxS3Parts {
		partSize = maxInt64(partSize, ceilDiv(fileSize, maxS3Parts))
	}
	partCount := int(maxInt64(1, ceilDiv(fileSize, partSize)))

	links, err := c.CreateMultipartUpload(ctx, projectUUID, baseName(path), partCount)
	if err != nil {
		return err
	}

	if err := c.uploadParts(ctx, path, partSize, links.Parts, concurrency); err != nil {
		c.abortMultipartBestEffort(projectUUID, links.UploadID, links.Key)
		return err
	}

	// Completing can also fail after every part succeeded; abort so a failed
	// complete does not leave the multipart upload dangling in S3.
	if err := c.CompleteMultipartUpload(ctx, projectUUID, links.UploadID, baseName(path)); err != nil {
		c.abortMultipartBestEffort(projectUUID, links.UploadID, links.Key)
		return err
	}
	return nil
}

// abortMultipartBestEffort tears down a multipart upload on a fresh context, so a
// canceled or expired caller context (often the very reason the upload failed)
// still lets the abort reach S3. Errors are ignored: the caller's original error
// is what matters.
func (c *Client) abortMultipartBestEffort(projectUUID, uploadID, key string) {
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	_ = c.AbortMultipartUpload(ctx, projectUUID, uploadID, key)
}

// uploadParts uploads each part concurrently. Chunks are read inside the
// semaphore so peak memory is bounded to concurrency * partSize.
func (c *Client) uploadParts(ctx context.Context, path string, partSize int64, parts []MultipartUploadPart, concurrency int) error {
	f, err := os.Open(path)
	if err != nil {
		return err
	}
	defer f.Close()

	sem := make(chan struct{}, concurrency)
	var wg sync.WaitGroup
	errs := make([]error, len(parts))

	for i, part := range parts {
		wg.Add(1)
		sem <- struct{}{}
		go func(i int, part MultipartUploadPart) {
			defer wg.Done()
			defer func() { <-sem }()
			offset := int64(part.PartNumber-1) * partSize
			chunk := make([]byte, partSize)
			n, rerr := f.ReadAt(chunk, offset)
			// ReadAt fills the buffer for a full part (nil error); only the final
			// part is short and returns io.EOF. A short read on any other part means
			// the file changed under us (e.g. truncation), so fail rather than
			// upload a corrupt, short part that would complete with bad data.
			isLast := part.PartNumber == len(parts)
			if rerr != nil && !(isLast && errors.Is(rerr, io.EOF) && n > 0) {
				errs[i] = fmt.Errorf("reading part %d: %w", part.PartNumber, rerr)
				return
			}
			if err := c.putBytes(ctx, part.UploadURL, chunk[:n]); err != nil {
				errs[i] = fmt.Errorf("uploading part %d: %w", part.PartNumber, err)
			}
		}(i, part)
	}
	wg.Wait()

	for _, e := range errs {
		if e != nil {
			return e
		}
	}
	return nil
}
