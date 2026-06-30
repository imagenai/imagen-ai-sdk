/**
 * Live smoke-test for the Imagen AI SDK against the real API.
 *
 * Usage:
 *   IMAGEN_API_KEY=<key> PROFILE_KEY=<key> ./node_modules/.bin/ts-node-esm --project tsconfig.json examples/test-sdk.ts
 *
 * PROFILE_KEY defaults to the first RAW profile returned by the API.
 * Place RAW files (DNG, ARW, etc.) in examples/sample_photos/ before running.
 */

import * as path from "node:path";
import * as fs from "node:fs";
import { fileURLToPath } from "node:url";
import { ImagenClient, quickEdit, PhotographyType } from "../src/index.js";
import { isValidImageFile, isRawFile } from "../src/utils.js";

const API_KEY = process.env["IMAGEN_API_KEY"];
if (!API_KEY) throw new Error("IMAGEN_API_KEY env var is required");

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SAMPLES_DIR = path.join(__dirname, "sample_photos");
const OUTPUT_DIR = path.join(SAMPLES_DIR, "test_output");

async function main() {
  const client = new ImagenClient(API_KEY!, { logger: console });

  try {
    console.log("\n--- Fetching profiles ---");
    const profiles = await client.getProfiles();
    console.log("Available profiles:");
    for (const p of profiles) {
      console.log(`  [${p.profileKey}] ${p.profileName} | type: ${p.imageType}`);
    }

    const profileKeyEnv = process.env["PROFILE_KEY"];
    const profile = profileKeyEnv
      ? profiles.find((p) => p.profileKey === Number(profileKeyEnv))
      : profiles.find((p) => p.imageType.toUpperCase() === "RAW");

    if (!profile) {
      console.error(
        profileKeyEnv
          ? `Profile key ${profileKeyEnv} not found.`
          : "No RAW profile found."
      );
      process.exit(1);
    }
    console.log(`\nUsing profile: [${profile.profileKey}] ${profile.profileName}`);

    const isRaw = profile.imageType.toUpperCase() === "RAW";
    const imagePaths = fs
      .readdirSync(SAMPLES_DIR)
      .map((f) => path.join(SAMPLES_DIR, f))
      .filter((f) => isValidImageFile(f) && (isRaw ? isRawFile(f) : !isRawFile(f)));

    if (imagePaths.length === 0) {
      console.error(`No ${isRaw ? "RAW" : "JPG"} files found in ${SAMPLES_DIR}`);
      process.exit(1);
    }
    console.log(`\nFiles to process (${imagePaths.length}):`);
    imagePaths.forEach((f) => console.log(" ", path.basename(f)));

    console.log("\n--- Running quickEdit ---");
    const result = await quickEdit(API_KEY!, {
      profileKey: profile.profileKey,
      imagePaths,
      projectName: "SDK Test Run",
      photographyType: PhotographyType.OTHER,
      export: true,
      download: true,
      downloadDir: OUTPUT_DIR,
      exportDownloadDir: path.join(OUTPUT_DIR, "exported"),
      uploadOptions: {
        onProgress: (cur, total, file) =>
          console.log(`  Uploading [${cur}/${total}]: ${path.basename(file)}`),
      },
      downloadOptions: {
        onProgress: (cur, total) => console.log(`  Downloading [${cur}/${total}]`),
      },
    });

    console.log("\n--- Result ---");
    console.log(`Project UUID : ${result.projectUuid}`);
    console.log(`Upload       : ${result.uploadSummary.successful}/${result.uploadSummary.total} succeeded`);
    console.log(`DNG edits    : ${result.downloadedFiles?.length ?? 0} downloaded`);
    console.log(`JPG exports  : ${result.exportedFiles?.length ?? 0} downloaded`);
    console.log(`Output dir   : ${OUTPUT_DIR}`);
  } finally {
    await client.close();
  }
}

main().catch((err) => {
  console.error("\nFailed:", err);
  process.exit(1);
});
