import { z } from "zod";

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

export const ProjectCreationResponseSchema = z.object({
  data: z
    .object({ project_uuid: z.string() })
    .transform((d) => ({ projectUuid: d.project_uuid })),
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

export const PresignedUrlResponseSchema = z.object({
  data: z.object({
    files_list: z.array(PresignedUrlSchema),
  }),
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

export const DownloadLinksResponseSchema = z.object({
  data: z.object({
    files_list: z.array(DownloadLinkSchema),
  }),
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
