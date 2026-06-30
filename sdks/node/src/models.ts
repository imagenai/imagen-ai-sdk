import { z } from "zod";
import { DNGCompression } from "./enums.js";

/**
 * Strip a sole `{ data: ... }` envelope.
 *
 * Production (https://api.imagen-ai.com/v1) returns payloads at the root, while
 * legacy/beta wrapped the body in a single top-level `data` key. Unwrapping here
 * lets the inner schemas validate both shapes. Mirrors the Python SDK's `_unwrap`.
 */
export function unwrap(payload: unknown): unknown {
  if (
    payload !== null &&
    typeof payload === "object" &&
    !Array.isArray(payload) &&
    Object.keys(payload as object).length === 1 &&
    "data" in (payload as object)
  ) {
    return (payload as { data: unknown }).data;
  }
  return payload;
}

export const ProfileSchema = z
  .object({
    image_type: z.string(),
    profile_key: z.number().int(),
    profile_name: z.string(),
    profile_type: z.string(),
  })
  .transform((d) => ({
    imageType: d.image_type,
    profileKey: d.profile_key,
    profileName: d.profile_name,
    profileType: d.profile_type,
  }));

export type Profile = z.infer<typeof ProfileSchema>;

export const ProfileApiResponseSchema = z.object({
  profiles: z.array(ProfileSchema),
});

export const ProfileApiDataSchema = z.object({
  data: ProfileApiResponseSchema,
});

// Inner shape (post-unwrap). The `*ResponseSchema` wrappers below remain for
// callers that validate the full beta envelope directly.
export const ProjectCreatedSchema = z
  .object({ project_uuid: z.string() })
  .transform((d) => ({ projectUuid: d.project_uuid }));

export const ProjectCreationResponseSchema = z.object({
  data: ProjectCreatedSchema,
});

export const FileUploadInfoSchema = z.object({
  fileName: z.string(),
  md5: z.string().nullable().optional(),
});

export type FileUploadInfo = z.infer<typeof FileUploadInfoSchema>;

export const PresignedUrlSchema = z
  .object({
    file_name: z.string(),
    upload_link: z.string().url(),
  })
  .transform((d) => ({ fileName: d.file_name, uploadLink: d.upload_link }));

export const PresignedFilesListSchema = z.object({
  files_list: z.array(PresignedUrlSchema),
});

export const PresignedUrlResponseSchema = z.object({
  data: PresignedFilesListSchema,
});

export const StatusDetailsSchema = z
  .object({
    status: z.string(),
    progress: z.number().nullable().optional().default(null),
    details: z.string().nullable().optional().default(null),
  })
  .transform((d) => ({
    status: d.status,
    progress: d.progress ?? null,
    details: d.details ?? null,
  }));

export type StatusDetails = z.infer<typeof StatusDetailsSchema>;

export const StatusResponseSchema = z.object({
  data: StatusDetailsSchema,
});

export const DownloadLinkSchema = z
  .object({
    file_name: z.string(),
    download_link: z.string(),
  })
  .transform((d) => ({ fileName: d.file_name, downloadLink: d.download_link }));

export const DownloadFilesListSchema = z.object({
  files_list: z.array(DownloadLinkSchema),
});

export const DownloadLinksResponseSchema = z.object({
  data: DownloadFilesListSchema,
});

export const EditOptionsSchema = z
  .object({
    crop: z.boolean().optional(),
    straighten: z.boolean().optional(),
    hdr_merge: z.boolean().optional(),
    portrait_crop: z.boolean().optional(),
    smooth_skin: z.boolean().optional(),
    subject_mask: z.boolean().optional(),
    headshot_crop: z.boolean().optional(),
    perspective_correction: z.boolean().optional(),
    sky_replacement: z.boolean().optional(),
    sky_replacement_template_id: z.number().int().optional(),
    window_pull: z.boolean().optional(),
    crop_aspect_ratio: z.string().optional(),
    callback_url: z.string().optional(),
    hdr_output_compression: z.nativeEnum(DNGCompression).optional(),
  })
  .refine(
    (d) => [d.crop, d.headshot_crop, d.portrait_crop].filter(Boolean).length <= 1,
    { message: "Only one of crop, headshot_crop, or portrait_crop can be true" }
  )
  .refine(
    (d) => !(d.straighten && d.perspective_correction),
    { message: "Only one of straighten or perspective_correction can be true" }
  );

export type EditOptions = z.infer<typeof EditOptionsSchema>;

export interface UploadResult {
  file: string;
  success: boolean;
  error: string | null;
}

export interface UploadSummary {
  total: number;
  successful: number;
  failed: number;
  results: UploadResult[];
}

export interface QuickEditResult {
  projectUuid: string;
  uploadSummary: UploadSummary;
  downloadLinks: string[];
  exportLinks: string[] | null;
  downloadedFiles: string[] | null;
  exportedFiles: string[] | null;
}

// =============================================================================
// SKY REPLACEMENT TEMPLATES (Workflow E discovery)
// =============================================================================

export const SkyTemplateSchema = z
  .object({
    id: z.number().int(),
    is_default: z.boolean(),
  })
  .transform((d) => ({ id: d.id, isDefault: d.is_default }));

export type SkyTemplate = z.infer<typeof SkyTemplateSchema>;

// Inner shape (post-unwrap).
export const SkyTemplatesResponseSchema = z.object({
  templates: z.array(SkyTemplateSchema),
});

// =============================================================================
// PROJECT LISTING / RETRIEVAL (Workflow E discovery)
// =============================================================================

export const PaginationInfoSchema = z.object({
  total: z.number().int(),
  size: z.number().int(),
  page: z.number().int(),
});

export type PaginationInfo = z.infer<typeof PaginationInfoSchema>;

export const ProjectListItemSchema = z
  .object({
    project_id: z.number().int().nullable().optional(),
    project_uuid: z.string(),
    name: z.string().nullable().optional(),
    status: z.string(),
    created_at: z.string(),
    number_of_images: z.number().int(),
    profile: z.string().nullable().optional(),
    ai_tools: z.array(z.string()).nullable().optional(),
    customer_reference_id: z.number().int(),
    thumbnail_src: z.string().nullable().optional(),
    export_status: z.string().nullable().optional(),
  })
  .transform((d) => ({
    projectId: d.project_id ?? null,
    projectUuid: d.project_uuid,
    name: d.name ?? null,
    status: d.status,
    createdAt: d.created_at,
    numberOfImages: d.number_of_images,
    profile: d.profile ?? null,
    aiTools: d.ai_tools ?? null,
    customerReferenceId: d.customer_reference_id,
    thumbnailSrc: d.thumbnail_src ?? null,
    exportStatus: d.export_status ?? null,
  }));

export type ProjectListItem = z.infer<typeof ProjectListItemSchema>;

// Inner shape (post-unwrap).
export const ProjectListResponseSchema = z.object({
  projects: z.array(ProjectListItemSchema),
  pagination: PaginationInfoSchema,
});

export type ProjectListResponse = z.infer<typeof ProjectListResponseSchema>;

// =============================================================================
// PER-IMAGE EXPORT LINKS (Workflow E discovery)
// =============================================================================

export const TemporaryFileUploadDataSchema = z
  .object({
    file_name: z.string(),
    upload_link: z.string(),
  })
  .transform((d) => ({ fileName: d.file_name, uploadLink: d.upload_link }));

export type TemporaryFileUploadData = z.infer<typeof TemporaryFileUploadDataSchema>;

export const FileDownloadInfoSchema = z
  .object({
    file_name: z.string(),
    download_link: z.string(),
  })
  .transform((d) => ({ fileName: d.file_name, downloadLink: d.download_link }));

export type FileDownloadInfo = z.infer<typeof FileDownloadInfoSchema>;

// =============================================================================
// AI ENHANCEMENT / COPILOT (Workflow C)
// =============================================================================

// `passthrough` preserves provider-added fields (Python uses extra="allow").
export const AIToolSchema = z
  .object({
    enhancement_type: z.string(),
    label: z.string().nullable().optional(),
    enabled_for_batch: z.boolean().nullable().optional(),
  })
  .passthrough()
  .transform(({ enhancement_type, label, enabled_for_batch, ...rest }) => ({
    enhancementType: enhancement_type,
    label: label ?? null,
    enabledForBatch: enabled_for_batch ?? null,
    ...rest,
  }));

export type AITool = z.infer<typeof AIToolSchema>;

// Inner shape (post-unwrap).
export const AIToolsResponseSchema = z
  .object({ prompts: z.array(AIToolSchema).default([]) })
  .passthrough();

export type AIToolsResponse = z.infer<typeof AIToolsResponseSchema>;

// Inner shape (post-unwrap). `version_id` is open-typed server-side.
export const EnhanceResultSchema = z
  .object({
    status: z.string(),
    version_id: z.any(),
    enhanced_image_url: z.string(),
  })
  .passthrough()
  .transform(({ status, version_id, enhanced_image_url, ...rest }) => ({
    status,
    versionId: version_id ?? null,
    enhancedImageUrl: enhanced_image_url,
    ...rest,
  }));

export type EnhanceResult = z.infer<typeof EnhanceResultSchema>;

// =============================================================================
// I2I (IMAGE-TO-IMAGE) EDIT + MULTIPART UPLOADS (Workflow D)
// =============================================================================

// Request body — snake_case keys spread directly into the request (like EditOptions).
export const I2IEditOptionsSchema = z.object({
  hdr_merge: z.boolean().optional(),
  sky_replacement: z.boolean().optional(),
  sky_replacement_template_id: z.number().int().optional(),
  perspective_correction: z.boolean().optional(),
  callback_url: z.string().optional(),
});

export type I2IEditOptions = z.infer<typeof I2IEditOptionsSchema>;

export const MultipartUploadPartUrlSchema = z
  .object({
    part_number: z.number().int(),
    upload_url: z.string(),
  })
  .transform((d) => ({ partNumber: d.part_number, uploadUrl: d.upload_url }));

export type MultipartUploadPartUrl = z.infer<typeof MultipartUploadPartUrlSchema>;

// Inner shape (post-unwrap).
export const MultipartUploadLinksResponseSchema = z
  .object({
    upload_id: z.string(),
    key: z.string(),
    parts: z.array(MultipartUploadPartUrlSchema),
  })
  .transform((d) => ({ uploadId: d.upload_id, key: d.key, parts: d.parts }));

export type MultipartUploadLinksResponse = z.infer<typeof MultipartUploadLinksResponseSchema>;

// Inner shape (post-unwrap). `passthrough` preserves provider-added fields.
export const MessageResponseSchema = z.object({ message: z.string() }).passthrough();

export type MessageResponse = z.infer<typeof MessageResponseSchema>;

// Inner shape (post-unwrap).
export const SingleDownloadLinkSchema = z
  .object({ download_link: z.string() })
  .passthrough()
  .transform(({ download_link, ...rest }) => ({ downloadLink: download_link, ...rest }));

export type SingleDownloadLink = z.infer<typeof SingleDownloadLinkSchema>;
