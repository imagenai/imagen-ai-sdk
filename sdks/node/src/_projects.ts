import { ImagenClientBase } from "./_base.js";
import { ImagenError, ProjectError } from "./errors.js";
import {
  unwrap,
  ProjectListResponseSchema,
  ProjectListItemSchema,
  SkyTemplatesResponseSchema,
  TemporaryFileUploadDataSchema,
  FileDownloadInfoSchema,
  type ProjectListResponse,
  type ProjectListItem,
  type SkyTemplate,
  type TemporaryFileUploadData,
  type FileDownloadInfo,
} from "./models.js";

export interface ListProjectsOptions {
  size?: number;
  page?: number;
  /** Filter by archived state, or null for all. Defaults to false (non-archived). */
  isArchived?: boolean | null;
  getThumbnail?: boolean;
}

/**
 * Project listing/retrieval, sky-replacement template discovery, and per-image
 * export links (Workflow E). Extends the base HTTP client.
 */
export class ProjectClient extends ImagenClientBase {
  async listProjects(options: ListProjectsOptions = {}): Promise<ProjectListResponse> {
    const { size = 20, page = 0, isArchived = false, getThumbnail = true } = options;

    const params: Record<string, string | number | boolean> = {
      size,
      page,
      client_type: "API",
      get_thumbnail: getThumbnail,
    };
    if (isArchived !== null) params["is_archived"] = isArchived;

    this.logger.debug(`Listing projects (page=${page}, size=${size})`);
    const json = await this._makeRequest("GET", "/projects", { params });
    const parsed = ProjectListResponseSchema.safeParse(unwrap(json));
    if (!parsed.success) {
      throw new ProjectError(`Could not parse project list response: ${parsed.error.message}`);
    }
    return parsed.data;
  }

  async getProject(projectUuid: string, getThumbnail = true): Promise<ProjectListItem> {
    this.logger.debug(`Getting project ${projectUuid}`);
    const json = await this._makeRequest("GET", `/projects/${projectUuid}`, {
      params: { get_thumbnail: getThumbnail },
    });
    const parsed = ProjectListItemSchema.safeParse(unwrap(json));
    if (!parsed.success) {
      throw new ProjectError(`Could not parse project response: ${parsed.error.message}`);
    }
    return parsed.data;
  }

  async getProjectUuid(projectName: string): Promise<string> {
    this.logger.debug(`Resolving UUID for project name: ${projectName}`);
    const json = await this._makeRequest("GET", `/projects/${projectName}/uuid`);
    const data = unwrap(json);

    // The response schema is unspecified server-side; accept the common shapes.
    if (typeof data === "string" && data) return data;
    if (data !== null && typeof data === "object") {
      for (const key of ["project_uuid", "uuid"]) {
        const value = (data as Record<string, unknown>)[key];
        if (typeof value === "string" && value) return value;
      }
    }
    throw new ProjectError(
      `Could not extract project UUID for name '${projectName}' from response: ${JSON.stringify(data)}`
    );
  }

  async getSkyReplacementTemplates(): Promise<SkyTemplate[]> {
    this.logger.debug("Getting sky replacement templates");
    const json = await this._makeRequest("GET", "/projects/sky_replacement/templates");
    const parsed = SkyTemplatesResponseSchema.safeParse(unwrap(json));
    if (!parsed.success) {
      throw new ImagenError(
        `Could not parse sky replacement templates response: ${parsed.error.message}`
      );
    }
    return parsed.data.templates;
  }

  async getExportUploadLink(
    projectUuid: string,
    fileName: string
  ): Promise<TemporaryFileUploadData> {
    this.logger.debug(`Getting export upload link for ${fileName} in ${projectUuid}`);
    const json = await this._makeRequest(
      "GET",
      `/projects/${projectUuid}/export/get_upload_link`,
      { params: { file_name: fileName } }
    );
    const parsed = TemporaryFileUploadDataSchema.safeParse(unwrap(json));
    if (!parsed.success) {
      throw new ProjectError(`Could not parse export upload link response: ${parsed.error.message}`);
    }
    return parsed.data;
  }

  async getExportDownloadLink(
    projectUuid: string,
    fileName: string
  ): Promise<FileDownloadInfo> {
    this.logger.debug(`Getting export download link for ${fileName} in ${projectUuid}`);
    const json = await this._makeRequest(
      "GET",
      `/projects/${projectUuid}/export/get_download_link`,
      { params: { file_name: fileName } }
    );
    const parsed = FileDownloadInfoSchema.safeParse(unwrap(json));
    if (!parsed.success) {
      throw new ProjectError(
        `Could not parse export download link response: ${parsed.error.message}`
      );
    }
    return parsed.data;
  }
}
