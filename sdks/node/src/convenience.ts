import { ImagenClient, type UploadOptions, type DownloadOptions, type EditingOptions } from "./client.js";
import { UploadError } from "./errors.js";
import { PhotographyType } from "./enums.js";
import type { Profile, QuickEditResult, UploadSummary, EditOptions } from "./models.js";
import { isRawFile, isJpgFile } from "./utils.js";

export function checkFilesMatchProfileType(filePaths: string[], profile: Profile): void {
  const typeLabel = profile.imageType.toUpperCase();

  if (typeLabel !== "RAW" && typeLabel !== "JPG") {
    throw new UploadError(`Unsupported profile image type: ${profile.imageType}`);
  }

  const rawFiles: string[] = [];
  const jpgFiles: string[] = [];
  const invalidFiles: string[] = [];

  for (const p of filePaths) {
    if (isRawFile(p)) rawFiles.push(p);
    else if (isJpgFile(p)) jpgFiles.push(p);
    else invalidFiles.push(p);
  }

  if (typeLabel === "RAW") {
    if (jpgFiles.length > 0) {
      throw new UploadError(
        `RAW profile cannot be used with JPG files: ${jpgFiles.join(", ")}`
      );
    }
    if (invalidFiles.length > 0) {
      throw new UploadError(
        `RAW profile cannot be used with unsupported files: ${invalidFiles.join(", ")}`
      );
    }
  } else {
    if (rawFiles.length > 0) {
      throw new UploadError(
        `JPG profile cannot be used with RAW files: ${rawFiles.join(", ")}`
      );
    }
    if (invalidFiles.length > 0) {
      throw new UploadError(
        `JPG profile cannot be used with unsupported files: ${invalidFiles.join(", ")}`
      );
    }
  }
}

export async function getProfiles(apiKey: string, baseUrl?: string): Promise<Profile[]> {
  const client = new ImagenClient(apiKey, { ...(baseUrl !== undefined ? { baseUrl } : {}) });
  try {
    return await client.getProfiles();
  } finally {
    await client.close();
  }
}

export async function getProfile(
  apiKey: string,
  profileKey: number,
  baseUrl?: string
): Promise<Profile> {
  const profiles = await getProfiles(apiKey, baseUrl);
  const found = profiles.find((p) => p.profileKey === profileKey);
  if (!found) {
    throw new UploadError(`Profile with key ${profileKey} not found.`);
  }
  return found;
}

export interface QuickEditOptions {
  profileKey: number;
  imagePaths: string[];
  projectName?: string;
  photographyType?: PhotographyType;
  editOptions?: EditOptions;
  export?: boolean;
  download?: boolean;
  downloadDir?: string;
  exportDownloadDir?: string;
  baseUrl?: string;
  signal?: AbortSignal;
  uploadOptions?: Omit<UploadOptions, "signal">;
  downloadOptions?: Omit<DownloadOptions, "signal">;
  pollIntervalMs?: number;
}

export async function quickEdit(
  apiKey: string,
  options: QuickEditOptions
): Promise<QuickEditResult> {
  const {
    profileKey,
    imagePaths,
    projectName,
    photographyType,
    editOptions,
    export: doExport = false,
    download = false,
    downloadDir = "downloads",
    exportDownloadDir,
    baseUrl,
    signal,
    uploadOptions = {},
    downloadOptions = {},
    pollIntervalMs,
  } = options;

  const client = new ImagenClient(apiKey, { ...(baseUrl !== undefined ? { baseUrl } : {}) });
  try {
    const profiles = await client.getProfiles();
    const profile = profiles.find((p) => p.profileKey === profileKey);
    if (!profile) throw new UploadError(`Profile with key ${profileKey} not found.`);
    checkFilesMatchProfileType(imagePaths, profile);

    const projectUuid = await client.createProject(projectName);

    const uploadSummary: UploadSummary = await client.uploadImages(projectUuid, imagePaths, {
      ...uploadOptions,
      ...(signal ? { signal } : {}),
    });

    if (uploadSummary.successful === 0) {
      throw new UploadError("quickEdit failed: no files uploaded successfully.");
    }

    const editingOpts: EditingOptions = {
      profileKey,
      ...(photographyType ? { photographyType } : {}),
      ...(editOptions ? { editOptions } : {}),
      ...(signal ? { signal } : {}),
      ...(pollIntervalMs !== undefined ? { pollIntervalMs } : {}),
    };

    await client.startEditing(projectUuid, editingOpts);
    const downloadLinks = await client.getDownloadLinks(projectUuid);

    let exportLinks: string[] | null = null;
    let downloadedFiles: string[] | null = null;
    let exportedFiles: string[] | null = null;

    if (doExport) {
      await client.exportProject(projectUuid, {
        ...(signal ? { signal } : {}),
        ...(pollIntervalMs !== undefined ? { pollIntervalMs } : {}),
      });
      exportLinks = await client.getExportLinks(projectUuid);
    }

    if (download) {
      downloadedFiles = await client.downloadFiles(downloadLinks, downloadDir, {
        ...downloadOptions,
        ...(signal ? { signal } : {}),
      });
      if (exportLinks) {
        const exportDir = exportDownloadDir ?? `${downloadDir}/exported`;
        exportedFiles = await client.downloadFiles(exportLinks, exportDir, {
          ...downloadOptions,
          ...(signal ? { signal } : {}),
        });
      }
    }

    return {
      projectUuid,
      uploadSummary,
      downloadLinks,
      exportLinks,
      downloadedFiles,
      exportedFiles,
    };
  } finally {
    await client.close();
  }
}
