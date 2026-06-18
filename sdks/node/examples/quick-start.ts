/**
 * Quick-start example for the Imagen AI Node.js SDK.
 *
 * Run with: IMAGEN_API_KEY=your_key npx ts-node examples/quick-start.ts
 */
import { ImagenClient, PhotographyType } from "../src/index";

async function main() {
  const API_KEY = process.env["IMAGEN_API_KEY"];
  if (!API_KEY) {
    throw new Error("Set the IMAGEN_API_KEY environment variable before running.");
  }

  const client = new ImagenClient(API_KEY, {
    logger: console,
  });

  try {
    // 1. List available profiles
    const profiles = await client.getProfiles();
    console.log(
      "Available profiles:",
      profiles.map((p) => `${p.profileName} (key: ${p.profileKey}, type: ${p.imageType})`)
    );

    if (profiles.length === 0) {
      console.log("No profiles found. Create a profile in the Imagen AI app first.");
      return;
    }

    const profile = profiles[0]!;

    // 2. Run the full workflow
    const projectUuid = await client.createProject("Quick Start Project");
    console.log(`Created project: ${projectUuid}`);

    const summary = await client.uploadImages(projectUuid, ["./sample.cr2"], {
      onProgress: (current, total, file) =>
        console.log(`Uploading ${current}/${total}: ${file}`),
    });
    console.log(`Uploaded: ${summary.successful}/${summary.total} files`);

    const status = await client.startEditing(projectUuid, {
      profileKey: profile.profileKey,
      photographyType: PhotographyType.WEDDING,
    });
    console.log(`Editing status: ${status.status}`);

    const downloadLinks = await client.getDownloadLinks(projectUuid);
    const files = await client.downloadFiles(downloadLinks, "./output", {
      onProgress: (current, total) =>
        console.log(`Downloading ${current}/${total}`),
    });
    console.log(`Downloaded ${files.length} files to ./output`);
  } finally {
    await client.close();
  }
}

main().catch((err) => {
  console.error("Error:", err);
  process.exit(1);
});
