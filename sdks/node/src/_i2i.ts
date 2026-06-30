import * as fs from "node:fs";
import * as fsp from "node:fs/promises";
import * as path from "node:path";
import pLimit from "p-limit";
import { EnhancementClient } from "./_enhancement.js";
import { ProjectError, UploadError, ImagenError } from "./errors.js";
import { isValidImageFile } from "./utils.js";
import {
  unwrap,
  ProjectCreatedSchema,
  ProjectListResponseSchema,
  ProjectListItemSchema,
  PresignedFilesListSchema,
  TemporaryFileUploadDataSchema,
  MultipartUploadLinksResponseSchema,
  MessageResponseSchema,
  DownloadFilesListSchema,
  SingleDownloadLinkSchema,
  type ProjectListResponse,
  type ProjectListItem,
  type TemporaryFileUploadData,
  type MultipartUploadLinksResponse,
  type MessageResponse,
  type SingleDownloadLink,
  type I2IEditOptions,
  type UploadSummary,
  type UploadResult,
} from "./models.js";
import type { ProgressCallback } from "./_base.js";

/** S3 multipart part size: 64 MB (S3 requires >= 5 MB except for the final part). */
export const DEFAULT_MULTIPART_PART_SIZE = 64 * 1024 * 1024;

export interface ListI2iProjectsOptions {
  size?: number;
  page?: number;
  /** Filter by archived state, or null for all. Defaults to false (non-archived). */
  isArchived?: boolean | null;
}

export interface UploadI2iOptions {
  maxConcurrent?: number;
  calculateMd5?: boolean;
  onProgress?: ProgressCallback;
  /** Files larger than this many bytes use multipart upload. Defaults to 64 MB. */
  multipartThreshold?: number;
}

export interface MultipartUploadOptions {
  partSize?: number;
  maxConcurrent?: number;
}

/**
 * Image-to-Image (I2I) workflow (Workflow D): project create/list/validate/get,
 * size-routed upload (single presigned PUT or S3 multipart), start editing, and
 * download links. After `startI2iEditing`, wait for completion via a `callback_url`
 * or by calling `waitForI2iCompletion` (which polls the project status).
 */
export class I2IClient extends EnhancementClient {
  // -- Project lifecycle ----------------------------------------------------

  async createI2iProject(name?: string): Promise<string> {
    const body: Record<string, string> = {};
    if (name) body["name"] = name;

    this.logger.info(`Creating I2I project: ${name ?? "Unnamed"}`);
    const json = await this._makeRequest("POST", "/i2i/projects/", { json: body });
    const parsed = ProjectCreatedSchema.safeParse(unwrap(json));
    if (!parsed.success) {
      throw new ProjectError(`Could not parse I2I project creation response: ${parsed.error.message}`);
    }
    this.logger.info(`Created I2I project with UUID: ${parsed.data.projectUuid}`);
    return parsed.data.projectUuid;
  }

  async listI2iProjects(options: ListI2iProjectsOptions = {}): Promise<ProjectListResponse> {
    const { size = 20, page = 0, isArchived = false } = options;
    const params: Record<string, string | number | boolean> = { size, page };
    if (isArchived !== null) params["is_archived"] = isArchived;

    this.logger.debug(`Listing I2I projects (page=${page}, size=${size})`);
    const json = await this._makeRequest("GET", "/i2i/projects", { params });
    const parsed = ProjectListResponseSchema.safeParse(unwrap(json));
    if (!parsed.success) {
      throw new ProjectError(`Could not parse I2I project list response: ${parsed.error.message}`);
    }
    return parsed.data;
  }

  async validateI2iProjectName(name: string): Promise<boolean> {
    this.logger.debug(`Validating I2I project name: ${name}`);
    const json = await this._makeRequest("GET", "/i2i/projects/is_valid_name", {
      params: { name },
    });
    const data = unwrap(json);
    if (typeof data === "boolean") return data;
    if (data !== null && typeof data === "object") {
      for (const key of ["is_valid", "valid"]) {
        if (key in (data as Record<string, unknown>)) {
          return Boolean((data as Record<string, unknown>)[key]);
        }
      }
    }
    // A successful (2xx) response with no explicit flag is treated as valid.
    return true;
  }

  async getI2iProject(projectUuid: string, getThumbnail = true): Promise<ProjectListItem> {
    this.logger.debug(`Getting I2I project ${projectUuid}`);
    const json = await this._makeRequest("GET", `/i2i/projects/${projectUuid}`, {
      params: { get_thumbnail: getThumbnail },
    });
    const parsed = ProjectListItemSchema.safeParse(unwrap(json));
    if (!parsed.success) {
      throw new ProjectError(`Could not parse I2I project response: ${parsed.error.message}`);
    }
    return parsed.data;
  }

  // -- Uploads --------------------------------------------------------------

  /**
   * Upload images to an I2I project, routing each file by size: files at or below
   * `multipartThreshold` go through a single batched presigned PUT; larger files use
   * S3 multipart. Multipart is only available for I2I projects, which is why
   * auto-routing lives here rather than in the base `uploadImages`.
   */
  async uploadI2iImages(
    projectUuid: string,
    imagePaths: string[],
    options: UploadI2iOptions = {}
  ): Promise<UploadSummary> {
    const {
      maxConcurrent = 5,
      calculateMd5 = false,
      onProgress,
      multipartThreshold = DEFAULT_MULTIPART_PART_SIZE,
    } = options;
    if (maxConcurrent < 1) throw new Error("maxConcurrent must be at least 1");

    const validPaths = imagePaths.filter((p) => {
      try {
        return fs.statSync(p).isFile() && isValidImageFile(p);
      } catch {
        this.logger.warn(`Skipping invalid path: ${p}`);
        return false;
      }
    });
    if (validPaths.length === 0) {
      throw new UploadError("No valid local files found to upload.");
    }

    this.logger.info(`Starting I2I upload of ${validPaths.length} images to project ${projectUuid}`);

    // Route each file by size.
    const smallPaths: string[] = [];
    const largePaths: string[] = [];
    for (const p of validPaths) {
      if (fs.statSync(p).size > multipartThreshold) largePaths.push(p);
      else smallPaths.push(p);
    }

    const results: UploadResult[] = [];

    if (smallPaths.length > 0) {
      const filesList = smallPaths.map((filePath) => {
        const entry: Record<string, string> = { file_name: path.basename(filePath) };
        if (calculateMd5) entry["md5"] = this._calculateMd5(filePath);
        return entry;
      });

      const presignedJson = await this._makeRequest(
        "POST",
        `/i2i/projects/${projectUuid}/get_temporary_upload_links`,
        { json: { files_list: filesList, client_type: "API" } }
      );
      const parsed = PresignedFilesListSchema.safeParse(unwrap(presignedJson));
      if (!parsed.success) {
        throw new UploadError(`Could not parse I2I presigned URL response: ${parsed.error.message}`);
      }
      const uploadMap = new Map(parsed.data.files_list.map((f) => [f.fileName, f.uploadLink]));

      const limit = pLimit(maxConcurrent);
      const total = smallPaths.length;
      const batch = await Promise.all(
        smallPaths.map((filePath, index) =>
          limit(async (): Promise<UploadResult> => {
            onProgress?.(index, total, filePath);
            try {
              const uploadUrl = uploadMap.get(path.basename(filePath));
              if (!uploadUrl) {
                throw new UploadError(`No upload link found for ${path.basename(filePath)}`);
              }
              await this._uploadToS3(filePath, uploadUrl);
              this.logger.debug(`Uploaded: ${path.basename(filePath)}`);
              onProgress?.(index + 1, total, filePath);
              return { file: filePath, success: true, error: null };
            } catch (err) {
              this.logger.error(`Failed to upload ${path.basename(filePath)}: ${String(err)}`);
              onProgress?.(index + 1, total, filePath);
              return { file: filePath, success: false, error: String(err) };
            }
          })
        )
      );
      results.push(...batch);
    }

    for (const filePath of largePaths) {
      this.logger.info(`Routing large file to multipart upload: ${path.basename(filePath)}`);
      try {
        await this.uploadI2iFileMultipart(projectUuid, filePath, { maxConcurrent });
        results.push({ file: filePath, success: true, error: null });
      } catch (err) {
        this.logger.error(`Multipart upload failed for ${path.basename(filePath)}: ${String(err)}`);
        results.push({ file: filePath, success: false, error: String(err) });
      }
      onProgress?.(results.length, validPaths.length, filePath);
    }

    return {
      total: results.length,
      successful: results.filter((r) => r.success).length,
      failed: results.filter((r) => !r.success).length,
      results,
    };
  }

  async getI2iUploadLink(projectUuid: string, fileName: string): Promise<TemporaryFileUploadData> {
    this.logger.debug(`Getting I2I upload link for ${fileName} in ${projectUuid}`);
    const json = await this._makeRequest("GET", `/i2i/projects/${projectUuid}/get_upload_link`, {
      params: { file_name: fileName },
    });
    const parsed = TemporaryFileUploadDataSchema.safeParse(unwrap(json));
    if (!parsed.success) {
      throw new ProjectError(`Could not parse I2I upload link response: ${parsed.error.message}`);
    }
    return parsed.data;
  }

  // -- Multipart uploads ----------------------------------------------------

  async createI2iMultipartUpload(
    projectUuid: string,
    fileName: string,
    partCount: number
  ): Promise<MultipartUploadLinksResponse> {
    this.logger.debug(`Creating multipart upload for ${fileName} (${partCount} parts) in ${projectUuid}`);
    const json = await this._makeRequest("POST", `/i2i/projects/${projectUuid}/multipart_uploads`, {
      json: { file_name: fileName, part_count: partCount },
    });
    const parsed = MultipartUploadLinksResponseSchema.safeParse(unwrap(json));
    if (!parsed.success) {
      throw new UploadError(`Could not parse multipart upload links response: ${parsed.error.message}`);
    }
    return parsed.data;
  }

  async completeI2iMultipartUpload(
    projectUuid: string,
    uploadId: string,
    fileName: string
  ): Promise<void> {
    this.logger.debug(`Completing multipart upload ${uploadId} for ${fileName} in ${projectUuid}`);
    await this._makeRequest(
      "POST",
      `/i2i/projects/${projectUuid}/multipart_uploads/${uploadId}/complete`,
      { json: { file_name: fileName } }
    );
  }

  async abortI2iMultipartUpload(projectUuid: string, uploadId: string, key: string): Promise<void> {
    this.logger.debug(`Aborting multipart upload ${uploadId} in ${projectUuid}`);
    await this._makeRequest("DELETE", `/i2i/projects/${projectUuid}/multipart_uploads/${uploadId}`, {
      json: { key },
    });
  }

  /**
   * Upload a single large file using S3 multipart: splits the file into `partSize`
   * chunks, PUTs each part concurrently, then completes. On any failure the upload
   * is aborted before the error is re-raised. Peak memory is bounded to
   * `maxConcurrent * partSize` (each chunk is read inside the concurrency limit).
   */
  async uploadI2iFileMultipart(
    projectUuid: string,
    filePath: string,
    options: MultipartUploadOptions = {}
  ): Promise<MultipartUploadLinksResponse> {
    let { partSize = DEFAULT_MULTIPART_PART_SIZE } = options;
    const { maxConcurrent = 4 } = options;
    if (maxConcurrent < 1) throw new Error("maxConcurrent must be at least 1");

    let stat: fs.Stats;
    try {
      stat = fs.statSync(filePath);
      if (!stat.isFile()) throw new Error("not a file");
    } catch {
      throw new UploadError(`File not found for multipart upload: ${filePath}`);
    }

    const fileSize = stat.size;
    const fileName = path.basename(filePath);
    // S3 allows at most 10000 parts; grow part size if needed to stay within that.
    if (fileSize) partSize = Math.max(partSize, Math.ceil(fileSize / 10000));
    const partCount = Math.max(1, Math.ceil(fileSize / partSize));
    this.logger.info(`Multipart-uploading ${fileName} (${fileSize} bytes, ${partCount} parts) to ${projectUuid}`);

    const links = await this.createI2iMultipartUpload(projectUuid, fileName, partCount);

    const limit = pLimit(maxConcurrent);
    const fh = await fsp.open(filePath, "r");
    try {
      await Promise.all(
        links.parts.map((part) =>
          limit(async () => {
            const offset = (part.partNumber - 1) * partSize;
            const length = Math.max(0, Math.min(partSize, fileSize - offset));
            const buffer = Buffer.alloc(length);
            if (length > 0) await fh.read(buffer, 0, length, offset);
            const response = await fetch(part.uploadUrl, { method: "PUT", body: buffer });
            if (!response.ok) {
              throw new UploadError(`S3 part upload failed (${response.status}): ${response.statusText}`);
            }
            this.logger.debug(`Uploaded part ${part.partNumber}/${partCount} of ${fileName}`);
          })
        )
      );
      await this.completeI2iMultipartUpload(projectUuid, links.uploadId, fileName);
    } catch (err) {
      this.logger.error(`Multipart upload of ${fileName} failed: ${String(err)}; aborting upload ${links.uploadId}`);
      try {
        await this.abortI2iMultipartUpload(projectUuid, links.uploadId, links.key);
      } catch (abortErr) {
        this.logger.error(`Failed to abort multipart upload ${links.uploadId}: ${String(abortErr)}`);
      }
      throw new UploadError(`Multipart upload of ${fileName} failed: ${String(err)}`);
    } finally {
      await fh.close();
    }

    this.logger.info(`Completed multipart upload of ${fileName}`);
    return links;
  }

  // -- Editing & downloads --------------------------------------------------

  /**
   * Trigger I2I editing. This only triggers the edit and returns immediately;
   * to wait for completion, set a `callback_url` in `editOptions` or call
   * `waitForI2iCompletion`, which polls the project status until terminal.
   */
  async startI2iEditing(
    projectUuid: string,
    editOptions?: I2IEditOptions
  ): Promise<MessageResponse> {
    this.logger.info(`Triggering I2I edit for project ${projectUuid}`);
    const json = await this._makeRequest("POST", `/i2i/projects/${projectUuid}/edit`, {
      json: editOptions ?? {},
    });
    const parsed = MessageResponseSchema.safeParse(unwrap(json));
    if (!parsed.success) {
      throw new ImagenError(`Could not parse I2I edit trigger response: ${parsed.error.message}`);
    }
    return parsed.data;
  }

  /**
   * Poll an I2I project's status until editing completes or fails.
   *
   * Unlike the classic edit flow (which has a dedicated `/edit/status` endpoint),
   * I2I exposes its status on the project object: `GET /v1/i2i/projects/{uuid}`
   * returns a `status` of Pending -> In Progress -> Completed/Failed. This polls
   * that endpoint with exponential backoff, mirroring `_waitForCompletion`.
   *
   * @returns The final `ProjectListItem` once status is `Completed`.
   * @throws ProjectError if editing fails or the wait times out.
   */
  async waitForI2iCompletion(
    projectUuid: string,
    options: { pollIntervalMs?: number; maxWaitMs?: number } = {}
  ): Promise<ProjectListItem> {
    const { pollIntervalMs = 10_000, maxWaitMs = 72_000_000 } = options;
    const MAX_INTERVAL_MS = 60_000;
    let interval = pollIntervalMs;
    const startedAt = Date.now();

    this.logger.info(`Waiting for I2I editing of ${projectUuid} to complete...`);

    // eslint-disable-next-line no-constant-condition -- poll loop; exits on terminal status or timeout
    while (true) {
      if (Date.now() - startedAt > maxWaitMs) {
        throw new ProjectError(`I2I editing timed out after ${maxWaitMs / 1000}s`);
      }

      const project = await this.getI2iProject(projectUuid, false);
      const elapsed = Math.round((Date.now() - startedAt) / 1000);
      this.logger.info(`  I2I status: ${project.status} — elapsed ${elapsed}s`);

      if (project.status === "Completed") {
        this.logger.info("I2I editing completed successfully");
        return project;
      }

      if (project.status === "Failed") {
        throw new ProjectError(`I2I editing failed for project ${projectUuid}.`);
      }

      await new Promise<void>((resolve) => setTimeout(resolve, interval));
      interval = Math.min(interval * 1.2, MAX_INTERVAL_MS);
    }
  }

  async getI2iDownloadLinks(projectUuid: string): Promise<string[]> {
    this.logger.debug(`Getting I2I download links for project ${projectUuid}`);
    const json = await this._makeRequest(
      "GET",
      `/i2i/projects/${projectUuid}/get_temporary_download_links`
    );
    const parsed = DownloadFilesListSchema.safeParse(unwrap(json));
    if (!parsed.success) {
      throw new ProjectError(`Could not parse I2I download links response: ${parsed.error.message}`);
    }
    const links = parsed.data.files_list.map((f) => f.downloadLink);
    this.logger.info(`Retrieved ${links.length} I2I download links`);
    return links;
  }

  async getI2iDownloadLink(projectUuid: string, fileName: string): Promise<SingleDownloadLink> {
    this.logger.debug(`Getting I2I download link for ${fileName} in ${projectUuid}`);
    const json = await this._makeRequest("GET", `/i2i/projects/${projectUuid}/get_download_link`, {
      params: { file_name: fileName },
    });
    const parsed = SingleDownloadLinkSchema.safeParse(unwrap(json));
    if (!parsed.success) {
      throw new ImagenError(`Could not parse I2I download link response: ${parsed.error.message}`);
    }
    return parsed.data;
  }
}
