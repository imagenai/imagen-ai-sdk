import { I2IClient } from "./_i2i.js";
import { type ClientOptions } from "./_base.js";

// Public type surface from the base layer.
export type {
  Logger,
  ClientOptions,
  ProgressCallback,
  UploadOptions,
  EditingOptions,
  ExportOptions,
  DownloadOptions,
} from "./_base.js";

/**
 * The Imagen AI client.
 *
 * Assembled as a linear inheritance chain across files to keep each file focused
 * and under the line limit:
 *
 *   ImagenClientBase (HTTP + standard edit/export)
 *     -> ProjectClient (discovery)
 *       -> EnhancementClient (AI enhancement / copilot / finalize)
 *         -> I2IClient (image-to-image + multipart upload)
 *           -> ImagenClient
 *
 * See `_base.ts` for the rationale.
 */
export class ImagenClient extends I2IClient {
  // Re-declare the constructor so the typed signature survives the chain.
  constructor(apiKey: string, options: ClientOptions = {}) {
    super(apiKey, options);
  }
}
