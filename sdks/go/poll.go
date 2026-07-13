package imagen

import (
	"context"
	"fmt"
	"time"
)

// PollOptions tunes status polling. The zero value uses the defaults below.
type PollOptions struct {
	// Interval is the first wait between polls (default 5s).
	Interval time.Duration
	// MaxInterval caps the backed-off interval (default 30s).
	MaxInterval time.Duration
	// Progress, if set, is called with each non-terminal status observed.
	Progress func(StatusDetails)
}

const (
	defaultPollInterval    = 5 * time.Second
	defaultMaxPollInterval = 30 * time.Second
	pollBackoffFactor      = 1.5
)

// pollStatus repeatedly calls fetch until the status is terminal, the context is
// cancelled, or a fetch errors. Polling uses exponential backoff capped at
// MaxInterval. A terminal Failed status returns an error wrapping ErrProject.
func (c *Client) pollStatus(ctx context.Context, fetch func(context.Context) (*StatusDetails, error), opts *PollOptions) (*StatusDetails, error) {
	interval := defaultPollInterval
	maxInterval := defaultMaxPollInterval
	var progress func(StatusDetails)
	if opts != nil {
		if opts.Interval > 0 {
			interval = opts.Interval
		}
		if opts.MaxInterval > 0 {
			maxInterval = opts.MaxInterval
		}
		progress = opts.Progress
	}

	for {
		status, err := fetch(ctx)
		if err != nil {
			return nil, err
		}
		if status.Status == StatusFailed {
			return status, fmt.Errorf("%w: editing failed: %s", ErrProject, status.Details)
		}
		if status.IsTerminal() {
			return status, nil
		}
		if progress != nil {
			progress(*status)
		}

		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		case <-time.After(interval):
		}

		interval = time.Duration(float64(interval) * pollBackoffFactor)
		if interval > maxInterval {
			interval = maxInterval
		}
	}
}

// WaitForEditing polls the edit status until it reaches a terminal state.
func (c *Client) WaitForEditing(ctx context.Context, projectUUID string, opts *PollOptions) (*StatusDetails, error) {
	return c.pollStatus(ctx, func(ctx context.Context) (*StatusDetails, error) {
		return c.EditStatus(ctx, projectUUID)
	}, opts)
}

// WaitForExport polls the export status until it reaches a terminal state.
func (c *Client) WaitForExport(ctx context.Context, projectUUID string, opts *PollOptions) (*StatusDetails, error) {
	return c.pollStatus(ctx, func(ctx context.Context) (*StatusDetails, error) {
		return c.ExportStatus(ctx, projectUUID)
	}, opts)
}

// EditAndWait starts editing and blocks until it completes or fails.
func (c *Client) EditAndWait(ctx context.Context, projectUUID string, edit EditRequest, opts *PollOptions) error {
	if err := c.StartEditing(ctx, projectUUID, edit); err != nil {
		return err
	}
	_, err := c.WaitForEditing(ctx, projectUUID, opts)
	return err
}

// WaitForI2ICompletion polls the I2I project's status (Pending -> In Progress ->
// Completed/Failed) until it is terminal, then returns the result download links.
// I2I has no dedicated status endpoint; the status lives on the project object
// (GET /i2i/projects/{uuid}). A Failed status returns an error wrapping
// ErrProject. Bound the total wait with ctx.
func (c *Client) WaitForI2ICompletion(ctx context.Context, projectUUID string, opts *PollOptions) (*DownloadLinksList, error) {
	interval := defaultPollInterval
	maxInterval := defaultMaxPollInterval
	var progress func(StatusDetails)
	if opts != nil {
		if opts.Interval > 0 {
			interval = opts.Interval
		}
		if opts.MaxInterval > 0 {
			maxInterval = opts.MaxInterval
		}
		progress = opts.Progress
	}

	for {
		project, err := c.GetI2IProject(ctx, projectUUID, false)
		if err != nil {
			return nil, err
		}
		switch project.Status {
		case StatusCompleted:
			return c.GetI2IDownloadLinks(ctx, projectUUID)
		case StatusFailed:
			return nil, fmt.Errorf("%w: I2I editing failed for project %s", ErrProject, projectUUID)
		}
		if progress != nil {
			progress(StatusDetails{Status: project.Status})
		}

		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		case <-time.After(interval):
		}

		interval = time.Duration(float64(interval) * pollBackoffFactor)
		if interval > maxInterval {
			interval = maxInterval
		}
	}
}

// ExportAndWait starts an export and blocks until it completes or fails.
func (c *Client) ExportAndWait(ctx context.Context, projectUUID string, opts *PollOptions) error {
	if err := c.StartExport(ctx, projectUUID); err != nil {
		return err
	}
	_, err := c.WaitForExport(ctx, projectUUID, opts)
	return err
}
