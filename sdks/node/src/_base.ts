import * as fs from "node:fs";
import * as fsp from "node:fs/promises";
import * as path from "node:path";
import * as crypto from "node:crypto";
import pLimit from "p-limit";
import { AuthenticationError, ImagenError, UploadError, DownloadError } from "./errors.js";
import { ProjectError } from "./errors.js";
import {
  unwrap,
  ProjectCreatedSchema,
  ProfileApiResponseSchema,
  PresignedFilesListSchema,
  StatusDetailsSchema,
  DownloadFilesListSchema,
  type Profile,
  type UploadSummary,
  type UploadResult,
  type StatusDetails,
  type EditOptions,
} from "./models.js";
import { PhotographyType } from "./enums.js";
import { isValidImageFile, extractFilenameFromUrl } from "./utils.js";

export interface Logger {
  debug(msg: string): void;
  info(msg: string): void;
  warn(msg: string): void;
  error(msg: string): void;
}

export interface ClientOptions {
  baseUrl?: string;
  logger?: Logger;
  timeout?: number;
}

export type ProgressCallback = (current: number, total: number, file: string) => void;

export interface UploadOptions {
  maxConcurrent?: number;
  calculateMd5?: boolean;
  signal?: AbortSignal;
  onProgress?: ProgressCallback;
}

export interface EditingOptions {
  profileKey: number;
  photographyType?: PhotographyType;
  editOptions?: EditOptions;
  signal?: AbortSignal;
  pollIntervalMs?: number;
}

export interface ExportOptions {
  signal?: AbortSignal;
  pollIntervalMs?: number;
}

export interface DownloadOptions {
  maxConcurrent?: number;
  signal?: AbortSignal;
  onProgress?: ProgressCallback;
}

const DEFAULT_BASE_URL = "https://api.imagen-ai.com/v1";
const DEFAULT_TIMEOUT_MS = 300_000;

const noopLogger: Logger = {
  debug: () => {},
  info: () => {},
  warn: () => {},
  error: () => {},
};

// ponytail: the public `ImagenClient` is assembled as a linear inheritance chain
// across files (base -> projects -> enhancement -> i2i) to keep each file under
// the 800-line limit and mirror the Python SDK's mixin layering. This base holds
// the shared HTTP plumbing + standard edit/export workflow; feature groups extend
// it. Plain inheritance (not functional mixins) keeps the typed constructor and
// protected-member access working with zero machinery.
export class ImagenClientBase {
  private readonly apiKey: string;
  private readonly baseUrl: string;
  private readonly timeoutMs: number;
  protected readonly logger: Logger;

  constructor(apiKey: string, options: ClientOptions = {}) {
    if (!apiKey || !apiKey.trim()) {
      throw new Error("API key cannot be empty");
    }
    this.apiKey = apiKey.trim();
    this.baseUrl = (options.baseUrl ?? DEFAULT_BASE_URL).replace(/\/$/, "");
    this.timeoutMs = options.timeout ?? DEFAULT_TIMEOUT_MS;
    this.logger = options.logger ?? noopLogger;
    this.logger.debug(`ImagenClient initialised — baseUrl: ${this.baseUrl}`);
  }

  async close(): Promise<void> {
    this.logger.debug("ImagenClient closed");
  }

  async [Symbol.asyncDispose](): Promise<void> {
    await this.close();
  }

  async createProject(name?: string): Promise<string> {
    const body: Record<string, string> = {};
    if (name) body["name"] = name;

    this.logger.info(`Creating project: ${name ?? "unnamed"}`);
    const json = await this._makeRequest("POST", "/projects/", { json: body });

    const parsed = ProjectCreatedSchema.safeParse(unwrap(json));
    if (!parsed.success) {
      throw new ProjectError(
        `Could not parse project creation response: ${parsed.error.message}`
      );
    }
    const uuid = parsed.data.projectUuid;
    this.logger.info(`Project created: ${uuid}`);
    return uuid;
  }

  async getProfiles(): Promise<Profile[]> {
    this.logger.debug("Fetching profiles");
    const json = await this._makeRequest("GET", "/profiles");

    const parsed = ProfileApiResponseSchema.safeParse(unwrap(json));
    if (!parsed.success) {
      throw new ImagenError(`Failed to parse profiles: ${parsed.error.message}`);
    }
    const profiles = parsed.data.profiles;
    this.logger.info(`Retrieved ${profiles.length} profiles`);
    return profiles;
  }

  async uploadImages(
    projectUuid: string,
    imagePaths: string[],
    options: UploadOptions = {}
  ): Promise<UploadSummary> {
    const { maxConcurrent = 5, calculateMd5 = false, signal, onProgress } = options;
    if (maxConcurrent < 1) throw new Error("maxConcurrent must be at least 1");

    const validPaths = imagePaths.filter((p) => {
      try {
        const stat = fs.statSync(p);
        return stat.isFile() && isValidImageFile(p);
      } catch {
        this.logger.warn(`Skipping invalid path: ${p}`);
        return false;
      }
    });

    if (validPaths.length === 0) {
      throw new UploadError("No valid local files found to upload.");
    }

    this.logger.info(`Uploading ${validPaths.length} files to project ${projectUuid}`);

    const filesList = await Promise.all(
      validPaths.map(async (filePath) => {
        const entry: Record<string, string> = { file_name: path.basename(filePath) };
        if (calculateMd5) {
          entry["md5"] = this._calculateMd5(filePath);
        }
        return entry;
      })
    );

    const presignedJson = await this._makeRequest(
      "POST",
      `/projects/${projectUuid}/get_temporary_upload_links`,
      { json: { files_list: filesList }, ...(signal ? { signal } : {}) }
    );

    const parsed = PresignedFilesListSchema.safeParse(unwrap(presignedJson));
    if (!parsed.success) {
      throw new UploadError(
        `Could not parse presigned URL response: ${parsed.error.message}`
      );
    }

    const uploadMap = new Map(
      parsed.data.files_list.map((f) => [f.fileName, f.uploadLink])
    );

    const limit = pLimit(maxConcurrent);
    const total = validPaths.length;

    const results: UploadResult[] = await Promise.all(
      validPaths.map((filePath, index) =>
        limit(async (): Promise<UploadResult> => {
          if (signal?.aborted) {
            return { file: filePath, success: false, error: "Aborted" };
          }
          onProgress?.(index, total, filePath);
          try {
            const uploadUrl = uploadMap.get(path.basename(filePath));
            if (!uploadUrl) {
              throw new UploadError(`No upload link found for ${path.basename(filePath)}`);
            }
            await this._uploadToS3(filePath, uploadUrl, signal);
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

    const summary: UploadSummary = {
      total,
      successful: results.filter((r) => r.success).length,
      failed: results.filter((r) => !r.success).length,
      results,
    };

    this.logger.info(`Upload complete: ${summary.successful}/${summary.total} successful`);
    return summary;
  }

  async startEditing(projectUuid: string, options: EditingOptions): Promise<StatusDetails> {
    const { profileKey, photographyType, editOptions, signal, pollIntervalMs } = options;

    const body: Record<string, unknown> = {
      profile_key: profileKey,
      ...(photographyType ? { photography_type: photographyType } : {}),
      ...(editOptions ?? {}),
    };

    this.logger.info(
      `Starting editing for project ${projectUuid} with profile ${profileKey}`
    );

    // The Imagen API's edit endpoint does not expect Content-Type header
    await this._makeRequest("POST", `/projects/${projectUuid}/edit`, {
      json: body,
      ...(signal ? { signal } : {}),
      headers: { "Content-Type": "" },
    });

    return this._waitForCompletion(projectUuid, "edit", {
      ...(signal ? { signal } : {}),
      ...(pollIntervalMs !== undefined ? { pollIntervalMs } : {}),
    });
  }

  async exportProject(projectUuid: string, options: ExportOptions = {}): Promise<StatusDetails> {
    const { signal, pollIntervalMs } = options;
    this.logger.info(`Starting export for project ${projectUuid}`);
    await this._makeRequest("POST", `/projects/${projectUuid}/export`, {
      ...(signal ? { signal } : {}),
    });
    return this._waitForCompletion(projectUuid, "export", {
      ...(signal ? { signal } : {}),
      ...(pollIntervalMs !== undefined ? { pollIntervalMs } : {}),
    });
  }

  async getDownloadLinks(projectUuid: string): Promise<string[]> {
    this.logger.debug(`Getting download links for project ${projectUuid}`);
    const json = await this._makeRequest(
      "GET",
      `/projects/${projectUuid}/edit/get_temporary_download_links`
    );
    const parsed = DownloadFilesListSchema.safeParse(unwrap(json));
    if (!parsed.success) {
      throw new ProjectError(`Could not parse download links: ${parsed.error.message}`);
    }
    const links = parsed.data.files_list.map((f) => f.downloadLink);
    this.logger.info(`Retrieved ${links.length} download links`);
    return links;
  }

  async getExportLinks(projectUuid: string): Promise<string[]> {
    this.logger.debug(`Getting export links for project ${projectUuid}`);
    const json = await this._makeRequest(
      "GET",
      `/projects/${projectUuid}/export/get_temporary_download_links`
    );
    const parsed = DownloadFilesListSchema.safeParse(unwrap(json));
    if (!parsed.success) {
      throw new ProjectError(`Could not parse export links: ${parsed.error.message}`);
    }
    const links = parsed.data.files_list.map((f) => f.downloadLink);
    this.logger.info(`Retrieved ${links.length} export links`);
    return links;
  }

  async downloadFiles(
    downloadLinks: string[],
    outputDir: string,
    options: DownloadOptions = {}
  ): Promise<string[]> {
    const { maxConcurrent = 5, signal, onProgress } = options;
    if (maxConcurrent < 1) throw new Error("maxConcurrent must be at least 1");
    if (downloadLinks.length === 0) throw new DownloadError("No download links provided.");

    await fsp.mkdir(outputDir, { recursive: true });
    this.logger.info(`Downloading ${downloadLinks.length} files to ${outputDir}`);

    const limit = pLimit(maxConcurrent);
    const total = downloadLinks.length;

    const results = await Promise.all(
      downloadLinks.map((url, index) =>
        limit(async (): Promise<string | null> => {
          if (signal?.aborted) return null;
          onProgress?.(index, total, `Starting download ${index + 1}`);
          try {
            const filename = extractFilenameFromUrl(url, index);
            const localPath = path.join(outputDir, filename);

            const fetchOptions: RequestInit = { ...(signal ? { signal } : {}) };
            const response = await fetch(url, fetchOptions);
            if (!response.ok) {
              throw new DownloadError(`HTTP ${response.status}: ${response.statusText}`);
            }
            const buffer = await response.arrayBuffer();
            await fsp.writeFile(localPath, Buffer.from(buffer));

            this.logger.debug(`Downloaded: ${filename}`);
            onProgress?.(index + 1, total, filename);
            return localPath;
          } catch (err) {
            this.logger.error(`Failed to download file ${index + 1}: ${String(err)}`);
            onProgress?.(index + 1, total, `Failed: ${String(err)}`);
            return null;
          }
        })
      )
    );

    const successful = results.filter((p): p is string => p !== null);
    if (successful.length === 0) throw new DownloadError("Failed to download any files.");

    this.logger.info(`Downloaded ${successful.length}/${total} files`);
    return successful;
  }

  private async _waitForCompletion(
    projectUuid: string,
    operation: "edit" | "export",
    options: { signal?: AbortSignal; pollIntervalMs?: number }
  ): Promise<StatusDetails> {
    const { signal, pollIntervalMs = 10_000 } = options;
    const MAX_WAIT_MS = 72_000_000; // 20 hours
    const MAX_INTERVAL_MS = 60_000;
    let interval = pollIntervalMs;
    const startedAt = Date.now();

    this.logger.info(`Waiting for ${operation} to complete...`);

    // eslint-disable-next-line no-constant-condition -- poll loop; exits on terminal status, timeout, or abort
    while (true) {
      if (signal?.aborted) throw new ProjectError(`${operation} aborted`);

      if (Date.now() - startedAt > MAX_WAIT_MS) {
        throw new ProjectError(
          `${operation} timed out after ${MAX_WAIT_MS / 1000}s`
        );
      }

      const json = await this._makeRequest(
        "GET",
        `/projects/${projectUuid}/${operation}/status`,
        { ...(signal ? { signal } : {}) }
      );

      const parsed = StatusDetailsSchema.safeParse(unwrap(json));
      if (!parsed.success) {
        throw new ProjectError(
          `Could not parse ${operation} status: ${parsed.error.message}`
        );
      }

      const details = parsed.data;
      const elapsed = Math.round((Date.now() - startedAt) / 1000);
      const progressStr = details.progress !== null ? ` (${details.progress}%)` : "";
      this.logger.info(
        `  ${operation} status: ${details.status}${progressStr} — elapsed ${elapsed}s`
      );

      if (details.status === "Completed") {
        this.logger.info(`${operation} completed successfully`);
        return details;
      }

      if (details.status === "Failed") {
        const msg = details.details ? ` Details: ${details.details}` : "";
        throw new ProjectError(`${operation} failed.${msg}`);
      }

      // Warn on unexpected status values so a server-side bug produces a visible log
      // rather than a silent 20-hour hang
      const KNOWN_STATUSES = new Set(["Completed", "Failed", "Processing", "Queued", "Pending"]);
      if (!KNOWN_STATUSES.has(details.status)) {
        this.logger.warn(
          `Unexpected ${operation} status: "${details.status}" — continuing to poll`
        );
      }

      await new Promise<void>((resolve, reject) => {
        const t = setTimeout(resolve, interval);
        if (signal) {
          signal.addEventListener(
            "abort",
            () => {
              clearTimeout(t);
              reject(new ProjectError(`${operation} aborted`));
            },
            { once: true }
          );
        }
      });

      interval = Math.min(interval * 1.2, MAX_INTERVAL_MS);
    }
  }

  protected _uploadToS3(filePath: string, uploadUrl: string, signal?: AbortSignal): Promise<void> {
    const content = fs.readFileSync(filePath);
    return fetch(uploadUrl, {
      method: "PUT",
      body: content,
      ...(signal ? { signal } : {}),
    }).then((response) => {
      if (!response.ok) {
        throw new UploadError(`S3 upload failed (${response.status}): ${response.statusText}`);
      }
    });
  }

  protected _calculateMd5(filePath: string): string {
    const content = fs.readFileSync(filePath);
    return crypto.createHash("md5").update(content).digest("base64");
  }

  /**
   * Extract a human-readable error message from an error response.
   *
   * The production API returns errors as `{"error": {"message": ...}}`; other
   * responses may use `{"detail": ...}`. Prefer `error.message`, fall back to a
   * string `error`, then `detail`, then the status text. Mirrors the Python
   * SDK's `_extract_error_message` so both SDKs surface the same detail.
   */
  protected async _extractErrorMessage(response: Response): Promise<string> {
    let body: unknown;
    try {
      body = await response.json();
    } catch {
      return response.statusText;
    }
    if (body !== null && typeof body === "object") {
      const data = body as Record<string, unknown>;
      const error = data["error"];
      if (error !== null && typeof error === "object") {
        const msg = (error as Record<string, unknown>)["message"];
        if (typeof msg === "string" && msg) return msg;
      }
      if (typeof error === "string" && error) return error;
      if (typeof data["detail"] === "string" && data["detail"]) return data["detail"];
    }
    return response.statusText;
  }

  protected async _makeRequest(
    method: string,
    endpoint: string,
    options: {
      json?: unknown;
      params?: Record<string, string | number | boolean>;
      signal?: AbortSignal;
      headers?: Record<string, string>;
    } = {}
  ): Promise<unknown> {
    let url = `${this.baseUrl}/${endpoint.replace(/^\//, "")}`;
    if (options.params && Object.keys(options.params).length > 0) {
      const qs = new URLSearchParams();
      for (const [k, v] of Object.entries(options.params)) qs.append(k, String(v));
      url += `?${qs.toString()}`;
    }
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeoutMs);

    // AbortSignal.any() is Node 20.3+ only — propagate manually for Node 18 compatibility
    let abortListener: (() => void) | null = null;
    if (options.signal) {
      if (options.signal.aborted) {
        clearTimeout(timeoutId);
        throw new ImagenError("Request aborted");
      }
      abortListener = () => controller.abort(options.signal!.reason);
      options.signal.addEventListener("abort", abortListener, { once: true });
    }

    try {
      const headers: Record<string, string> = {
        "x-api-key": this.apiKey,
        "User-Agent": "Imagen-Node-SDK/1.1.0",
        ...options.headers,
      };

      if (options.json !== undefined && !("Content-Type" in headers)) {
        headers["Content-Type"] = "application/json";
      }

      this.logger.debug(`${method} ${url}`);

      const fetchOptions: RequestInit = {
        method,
        headers,
        signal: controller.signal,
      };
      if (options.json !== undefined) {
        fetchOptions.body = JSON.stringify(options.json);
      }

      const response = await fetch(url, fetchOptions);

      this.logger.debug(`Response: ${response.status}`);

      if (response.status === 401) {
        throw new AuthenticationError("Invalid API key or unauthorized.");
      }

      if (!response.ok) {
        throw new ImagenError(
          `API Error (${response.status}): ${await this._extractErrorMessage(response)}`
        );
      }

      if (response.status === 204) return {};
      return await response.json();
    } catch (err) {
      if (err instanceof ImagenError) throw err;
      throw new ImagenError(`Request failed: ${String(err)}`);
    } finally {
      clearTimeout(timeoutId);
      if (abortListener && options.signal) {
        options.signal.removeEventListener("abort", abortListener);
      }
    }
  }
}
