import { ProjectClient } from "./_projects.js";
import { ImagenError } from "./errors.js";
import { ProjectSource } from "./enums.js";
import {
  unwrap,
  AIToolsResponseSchema,
  EnhanceResultSchema,
  DownloadFilesListSchema,
  type AIToolsResponse,
  type EnhanceResult,
} from "./models.js";

export interface EnhanceImageOptions {
  parentVersionId?: number;
  projectSource?: ProjectSource;
}

export interface CopilotOptions {
  parentVersionId?: number;
  projectSource?: ProjectSource;
}

/**
 * AI enhancement / copilot / finalize operations (Workflow C).
 *
 * The whole enhancement pipeline requires an EXPORTED project and operates on
 * exported (JPEG) filenames, not the uploaded RAW names.
 */
export class EnhancementClient extends ProjectClient {
  /**
   * List the AI enhancement (quick) tools available for a project. Use a tool's
   * `enhancementType` as the `toolId` for `enhanceImage`. Requires an exported
   * project (otherwise the API responds 400 "Project has not been exported yet.").
   */
  async getAiTools(
    projectUuid: string,
    projectSource: ProjectSource = ProjectSource.REGULAR
  ): Promise<AIToolsResponse> {
    this.logger.debug(`Listing AI tools for project ${projectUuid} (source=${projectSource})`);
    const json = await this._makeRequest("GET", `/projects/${projectUuid}/ai-tools`, {
      params: { project_source: projectSource },
    });
    const parsed = AIToolsResponseSchema.safeParse(unwrap(json));
    if (!parsed.success) {
      throw new ImagenError(`Could not parse AI tools response: ${parsed.error.message}`);
    }
    return parsed.data;
  }

  /** Apply an AI quick tool to an already-edited (exported) image. */
  async enhanceImage(
    projectUuid: string,
    filename: string,
    toolId: string,
    options: EnhanceImageOptions = {}
  ): Promise<EnhanceResult> {
    const { parentVersionId, projectSource = ProjectSource.REGULAR } = options;
    const body: Record<string, unknown> = { tool_id: toolId, project_source: projectSource };
    if (parentVersionId !== undefined) body["parent_version_id"] = parentVersionId;

    this.logger.info(`Enhancing ${filename} in project ${projectUuid} with tool ${toolId}`);
    const json = await this._makeRequest(
      "POST",
      `/projects/${projectUuid}/images/${filename}/enhance`,
      { json: body }
    );
    const parsed = EnhanceResultSchema.safeParse(unwrap(json));
    if (!parsed.success) {
      throw new ImagenError(`Could not parse enhance image response: ${parsed.error.message}`);
    }
    return parsed.data;
  }

  /** Apply a natural-language editing instruction via the AI copilot. */
  async applyCopilot(
    projectUuid: string,
    filename: string,
    instruction: string,
    options: CopilotOptions = {}
  ): Promise<EnhanceResult> {
    if (instruction.length < 1 || instruction.length > 255) {
      throw new ImagenError("Copilot instruction must be between 1 and 255 characters.");
    }
    const { parentVersionId, projectSource = ProjectSource.REGULAR } = options;
    const body: Record<string, unknown> = { instruction, project_source: projectSource };
    if (parentVersionId !== undefined) body["parent_version_id"] = parentVersionId;

    this.logger.info(`Applying copilot instruction to ${filename} in project ${projectUuid}`);
    const json = await this._makeRequest(
      "POST",
      `/projects/${projectUuid}/images/${filename}/copilot`,
      { json: body }
    );
    const parsed = EnhanceResultSchema.safeParse(unwrap(json));
    if (!parsed.success) {
      throw new ImagenError(`Could not parse copilot response: ${parsed.error.message}`);
    }
    return parsed.data;
  }

  /** Reset the copilot conversation history for an image. */
  async resetCopilot(
    projectUuid: string,
    filename: string,
    projectSource: ProjectSource = ProjectSource.REGULAR
  ): Promise<void> {
    this.logger.info(`Resetting copilot history for ${filename} in project ${projectUuid}`);
    await this._makeRequest("DELETE", `/projects/${projectUuid}/images/${filename}/copilot`, {
      json: { project_source: projectSource },
    });
  }

  /**
   * Generate final download URLs for all images, upscaling enhanced ones.
   * Requires an exported project. Returns the final per-file download links.
   */
  async finalizeProject(
    projectUuid: string,
    projectSource: ProjectSource = ProjectSource.REGULAR
  ): Promise<string[]> {
    this.logger.info(`Finalizing project ${projectUuid} (source=${projectSource})`);
    const json = await this._makeRequest("POST", `/projects/${projectUuid}/finalize`, {
      json: { project_source: projectSource },
    });
    const parsed = DownloadFilesListSchema.safeParse(unwrap(json));
    if (!parsed.success) {
      throw new ImagenError(`Could not parse finalize project response: ${parsed.error.message}`);
    }
    return parsed.data.files_list.map((f) => f.downloadLink);
  }
}
