package imagen

import "fmt"

// EditOptions are the optional toggles for a regular editing job. All fields are
// pointers so an unset option is omitted from the request rather than sent as a
// zero value. Use the Bool/Int/String helpers to set them.
//
// Mutual-exclusivity rules (validated client-side by Validate):
//   - at most one crop mode: Crop, HeadshotCrop, PortraitCrop
//   - at most one straightening mode: Straighten, PerspectiveCorrection
type EditOptions struct {
	Crop                     *bool            `json:"crop,omitempty"`
	Straighten               *bool            `json:"straighten,omitempty"`
	HDRMerge                 *bool            `json:"hdr_merge,omitempty"`
	PortraitCrop             *bool            `json:"portrait_crop,omitempty"`
	SmoothSkin               *bool            `json:"smooth_skin,omitempty"`
	SubjectMask              *bool            `json:"subject_mask,omitempty"`
	HeadshotCrop             *bool            `json:"headshot_crop,omitempty"`
	PerspectiveCorrection    *bool            `json:"perspective_correction,omitempty"`
	SkyReplacement           *bool            `json:"sky_replacement,omitempty"`
	SkyReplacementTemplateID *int             `json:"sky_replacement_template_id,omitempty"`
	WindowPull               *bool            `json:"window_pull,omitempty"`
	CropAspectRatio          *CropAspectRatio `json:"crop_aspect_ratio,omitempty"`
	CallbackURL              *string          `json:"callback_url,omitempty"`
	HDROutputCompression     *DNGCompression  `json:"hdr_output_compression,omitempty"`
}

func isTrue(p *bool) bool { return p != nil && *p }

// Validate enforces the crop/straighten mutual-exclusivity rules. It is called
// automatically by StartEditing, but is exported so callers can check early.
func (o EditOptions) Validate() error {
	cropModes := 0
	for _, p := range []*bool{o.Crop, o.HeadshotCrop, o.PortraitCrop} {
		if isTrue(p) {
			cropModes++
		}
	}
	if cropModes > 1 {
		return fmt.Errorf("imagen: at most one crop mode may be set (crop, headshot_crop, portrait_crop)")
	}

	straightenModes := 0
	for _, p := range []*bool{o.Straighten, o.PerspectiveCorrection} {
		if isTrue(p) {
			straightenModes++
		}
	}
	if straightenModes > 1 {
		return fmt.Errorf("imagen: at most one straightening mode may be set (straighten, perspective_correction)")
	}
	return nil
}

// EditRequest is the body for starting a regular editing job. ProfileKey is
// required; the embedded EditOptions fields flatten into the same JSON object.
type EditRequest struct {
	ProfileKey      int             `json:"profile_key"`
	PhotographyType PhotographyType `json:"photography_type,omitempty"`
	EditOptions
}

// I2IEditOptions are the optional toggles for an image-to-image editing job.
type I2IEditOptions struct {
	HDRMerge                 *bool   `json:"hdr_merge,omitempty"`
	SkyReplacement           *bool   `json:"sky_replacement,omitempty"`
	SkyReplacementTemplateID *int    `json:"sky_replacement_template_id,omitempty"`
	PerspectiveCorrection    *bool   `json:"perspective_correction,omitempty"`
	CallbackURL              *string `json:"callback_url,omitempty"`
}

// EnhanceRequest applies a quick AI tool to one image. ToolID is a tool's
// enhancement_type from GetAITools. Leave ParentVersionID nil to start from the
// base edited image.
type EnhanceRequest struct {
	ToolID          string        `json:"tool_id"`
	ParentVersionID any           `json:"parent_version_id,omitempty"`
	ProjectSource   ProjectSource `json:"project_source"`
}

// CopilotRequest applies a natural-language instruction (1..255 chars) to one
// image. Leave ParentVersionID nil to start from the base edited image.
type CopilotRequest struct {
	Instruction     string        `json:"instruction"`
	ParentVersionID any           `json:"parent_version_id,omitempty"`
	ProjectSource   ProjectSource `json:"project_source"`
}

// MultipartUploadPart is one presigned part URL of a multipart upload.
type MultipartUploadPart struct {
	PartNumber int    `json:"part_number"`
	UploadURL  string `json:"upload_url"`
}

// MultipartUploadResponse is the handle and per-part URLs for an S3 multipart
// upload created via CreateMultipartUpload.
type MultipartUploadResponse struct {
	UploadID string                `json:"upload_id"`
	Key      string                `json:"key"`
	Parts    []MultipartUploadPart `json:"parts"`
}
