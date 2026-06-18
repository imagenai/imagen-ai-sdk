import * as path from "node:path";

export const RAW_EXTENSIONS = new Set([
  ".dng", ".nef", ".cr2", ".arw", ".nrw", ".crw", ".srf", ".sr2",
  ".orf", ".raw", ".rw2", ".raf", ".ptx", ".pef", ".rwl", ".srw",
  ".cr3", ".3fr", ".fff",
]);

export const JPG_EXTENSIONS = new Set([".jpg", ".jpeg"]);

export const SUPPORTED_EXTENSIONS = new Set([...RAW_EXTENSIONS, ...JPG_EXTENSIONS]);

export function isValidImageFile(filePath: string): boolean {
  const ext = path.extname(filePath).toLowerCase();
  return SUPPORTED_EXTENSIONS.has(ext);
}

export function isRawFile(filePath: string): boolean {
  return RAW_EXTENSIONS.has(path.extname(filePath).toLowerCase());
}

export function isJpgFile(filePath: string): boolean {
  return JPG_EXTENSIONS.has(path.extname(filePath).toLowerCase());
}

export function extractFilenameFromUrl(url: string, index: number): string {
  try {
    const parsed = new URL(url);
    const rawFilename = path.basename(decodeURIComponent(parsed.pathname));
    const filename = rawFilename.replace(/[/\\]/g, "");
    if (filename && filename.includes(".") && filename.length > 1) {
      return filename;
    }
  } catch {
    // invalid URL — fall through to default
  }
  return `imagen_edited_${String(index + 1).padStart(5, "0")}.jpg`;
}
