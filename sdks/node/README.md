# Imagen AI Node.js SDK

**Professional AI photo editing automation for photographers**

Transform your post-production workflow with AI-powered batch editing. Upload hundreds of photos, apply professional edits automatically, and get download links in minutes.

---

## Quick start

### 1. Install

```bash
npm install imagen-ai-sdk
```

### 2. Get your API key

1. Sign up at [imagen-ai.com](https://imagen-ai.com)
2. Contact support at [support.imagen-ai.com](https://support.imagen-ai.com/hc) to request your API key
3. Set it as an environment variable:

```bash
# macOS / Linux
export IMAGEN_API_KEY="your_api_key_here"

# Windows Command Prompt
set IMAGEN_API_KEY=your_api_key_here

# Windows PowerShell
$env:IMAGEN_API_KEY="your_api_key_here"
```

### 3. Edit photos in one call

```typescript
import { quickEdit, EditOptions, PhotographyType } from "imagen-ai-sdk";

const result = await quickEdit(process.env.IMAGEN_API_KEY!, {
  profileKey: 5700,
  imagePaths: ["photo1.nef", "photo2.dng", "photo3.cr2"],
  photographyType: PhotographyType.WEDDING,
  editOptions: { crop: true, straighten: true },
  download: true,
  downloadDir: "./edited",
});

console.log(`Done! ${result.downloadedFiles?.length} edited photos ready`);
```

---

## Why use this SDK?

| Before | After |
|---|---|
| Edit 500 wedding photos manually | Upload → Wait a few minutes → Download |
| Hours of repetitive work | 5 lines of TypeScript |
| Inconsistent editing style | Professional AI consistency |
| Manual file management | Automatic downloads |

> **Pro tip:** First, use the Imagen app to perfect your editing style — then use the API to automate that exact workflow at scale.

---

## Understanding the workflow

### What you get back

The SDK returns **Adobe-compatible edit instructions** (XMP files) that preserve your original files and allow non-destructive editing. You can:

- Open edited files directly in Lightroom Classic, Lightroom, Photoshop, or Bridge
- Further adjust the AI-generated edits
- Export to any format you need

You can also trigger an **export** step that produces delivery-ready JPEGs.

### Profile keys: your editing style

Profile keys represent your unique editing style learned by the AI:

1. **Start with the Imagen app** to train your Personal AI Profile
2. **Perfect your style** with 3,000+ edited photos in the app
3. **Get your profile key** and use it in the API for consistent automation
4. **Scale your workflow** — apply your exact style to thousands of photos

List your profiles programmatically:

```typescript
import { getProfiles } from "imagen-ai-sdk";

const profiles = await getProfiles(process.env.IMAGEN_API_KEY!);
profiles.forEach(p =>
  console.log(`[${p.profileKey}] ${p.profileName} — ${p.imageType}`)
);
```

### File types

A single project can contain **either** RAW files **or** JPEG files — not both. Keep each file type in a separate project.

**RAW:** `.cr2`, `.cr3`, `.nef`, `.arw`, `.raf`, `.orf`, `.rw2`, `.dng`, `.raw`

**JPEG:** `.jpg`, `.jpeg`

```typescript
import { SUPPORTED_EXTENSIONS, RAW_EXTENSIONS, JPG_EXTENSIONS } from "imagen-ai-sdk";

const ext = path.extname("photo.cr2").toLowerCase();
const isSupported = SUPPORTED_EXTENSIONS.has(ext);
const isRaw = RAW_EXTENSIONS.has(ext);
```

---

## Step-by-step workflow

Use `ImagenClient` directly when you need control over individual steps.

### 1. Create a client

```typescript
import { ImagenClient } from "imagen-ai-sdk";

const client = new ImagenClient(process.env.IMAGEN_API_KEY!, {
  logger: console, // optional — pass console to see detailed logs
});
```

### 2. Create a project

```typescript
const projectUuid = await client.createProject("Sarah_Mike_Wedding_2024");
```

> **Project names must be unique.** If a name already exists you will get an error. Use timestamps or client names to keep them unique, or omit the name to get an auto-generated UUID.

### 3. Upload images

```typescript
const summary = await client.uploadImages(
  projectUuid,
  ["./photos/DSC001.CR2", "./photos/DSC002.CR2"],
  {
    maxConcurrent: 5,
    onProgress: (current, total, file) =>
      console.log(`Uploading ${current}/${total}: ${file}`),
  }
);
console.log(`${summary.successful}/${summary.total} files uploaded`);
```

### 4. Start editing

```typescript
import { PhotographyType } from "imagen-ai-sdk";

const status = await client.startEditing(projectUuid, {
  profileKey: 5700,
  photographyType: PhotographyType.WEDDING,
  editOptions: { crop: true, straighten: true },
});
// Polls automatically until editing completes or fails
```

### 5. Download XMP edit files

```typescript
const downloadLinks = await client.getDownloadLinks(projectUuid);
const files = await client.downloadFiles(downloadLinks, "./output", {
  onProgress: (current, total) => console.log(`Downloading ${current}/${total}`),
});
```

### 6. Export to JPEG (optional)

```typescript
await client.exportProject(projectUuid);
const exportLinks = await client.getExportLinks(projectUuid);
const jpegs = await client.downloadFiles(exportLinks, "./output/exported");
```

### 7. Clean up

```typescript
await client.close();

// Or use the async disposable pattern (Node 18+):
await using client = new ImagenClient(apiKey);
```

---

## Examples

### Wedding photography workflow

```typescript
import { quickEdit, PhotographyType } from "imagen-ai-sdk";

const result = await quickEdit(process.env.IMAGEN_API_KEY!, {
  profileKey: 5700,
  imagePaths: ["ceremony_01.cr2", "portraits_01.nef", "reception_01.dng"],
  projectName: "Sarah_Mike_Wedding_2024",
  photographyType: PhotographyType.WEDDING,
  editOptions: {
    crop: true,
    straighten: true,
    smooth_skin: true,
    subject_mask: true,
  },
  export: true,       // also produce delivery JPEGs
  download: true,
  downloadDir: "./wedding_edited",
  exportDownloadDir: "./wedding_jpegs",
});

console.log(`XMP files: ${result.downloadedFiles?.length}`);
console.log(`Exported JPEGs: ${result.exportedFiles?.length}`);
```

### Step-by-step with progress tracking

```typescript
import { ImagenClient, PhotographyType } from "imagen-ai-sdk";

const client = new ImagenClient(process.env.IMAGEN_API_KEY!, { logger: console });

try {
  const projectUuid = await client.createProject("Portraits_Jan2024");

  const summary = await client.uploadImages(projectUuid, imagePaths, {
    maxConcurrent: 3,
    calculateMd5: true, // integrity checking
    onProgress: (cur, total, file) =>
      console.log(`Upload ${cur}/${total}: ${path.basename(file)}`),
  });
  console.log(`Uploaded: ${summary.successful}/${summary.total}`);

  await client.startEditing(projectUuid, {
    profileKey: 5700,
    photographyType: PhotographyType.PORTRAITS,
    editOptions: { portrait_crop: true, smooth_skin: true, subject_mask: true },
  });

  const links = await client.getDownloadLinks(projectUuid);
  const files = await client.downloadFiles(links, "./output", {
    onProgress: (cur, total) => console.log(`Download ${cur}/${total}`),
  });
  console.log(`Downloaded ${files.length} files`);
} finally {
  await client.close();
}
```

### Batch processing a large collection

```typescript
import { quickEdit, RAW_EXTENSIONS, JPG_EXTENSIONS } from "imagen-ai-sdk";
import { readdirSync } from "fs";
import path from "path";

const allFiles = readdirSync("./photos").map(f => path.join("./photos", f));
const rawFiles = allFiles.filter(f => RAW_EXTENSIONS.has(path.extname(f).toLowerCase()));
const jpgFiles = allFiles.filter(f => JPG_EXTENSIONS.has(path.extname(f).toLowerCase()));

const BATCH_SIZE = 50;

for (const [label, files] of [["RAW", rawFiles], ["JPEG", jpgFiles]] as const) {
  for (let i = 0; i < files.length; i += BATCH_SIZE) {
    const batch = files.slice(i, i + BATCH_SIZE);
    const batchNum = Math.floor(i / BATCH_SIZE) + 1;
    console.log(`Processing ${label} batch ${batchNum} (${batch.length} files)...`);

    const result = await quickEdit(process.env.IMAGEN_API_KEY!, {
      profileKey: 5700,
      imagePaths: batch,
      download: true,
      downloadDir: `./edited/${label.toLowerCase()}_batch_${batchNum}`,
    });
    console.log(`Batch ${batchNum} done: ${result.downloadedFiles?.length} files`);
  }
}
```

---

## API reference

### `ImagenClient`

```typescript
new ImagenClient(apiKey: string, options?: ClientOptions)
```

| Option | Type | Default | Description |
|---|---|---|---|
| `baseUrl` | `string` | Imagen API endpoint | Override the API base URL |
| `timeout` | `number` | `300000` | Request timeout in milliseconds |
| `logger` | `Logger` | silent | Pass `console` or any `{ debug, info, warn, error }` object |

#### Methods

| Method | Returns | Description |
|---|---|---|
| `getProfiles()` | `Promise<Profile[]>` | List all profiles on your account |
| `createProject(name?)` | `Promise<string>` | Create a project, returns its UUID |
| `uploadImages(projectUuid, paths, options?)` | `Promise<UploadSummary>` | Upload image files to a project |
| `startEditing(projectUuid, options)` | `Promise<StatusDetails>` | Start editing and poll until complete |
| `exportProject(projectUuid, options?)` | `Promise<StatusDetails>` | Export to JPEG and poll until complete |
| `getDownloadLinks(projectUuid)` | `Promise<string[]>` | Presigned URLs for XMP edit files |
| `getExportLinks(projectUuid)` | `Promise<string[]>` | Presigned URLs for exported JPEGs |
| `downloadFiles(links, outputDir, options?)` | `Promise<string[]>` | Download files, returns local paths |
| `close()` | `Promise<void>` | Release the client |

### `quickEdit(apiKey, options)`

Runs the full workflow in one call.

| Option | Type | Default | Description |
|---|---|---|---|
| `profileKey` | `number` | required | Profile to apply |
| `imagePaths` | `string[]` | required | Local paths of images to edit |
| `projectName` | `string` | auto UUID | Optional project name (must be unique) |
| `photographyType` | `PhotographyType` | — | Hint that improves edit quality |
| `editOptions` | `EditOptions` | — | Fine-grained editing features |
| `export` | `boolean` | `false` | Export to JPEG after editing |
| `download` | `boolean` | `false` | Download files locally |
| `downloadDir` | `string` | `"downloads"` | Directory for XMP files |
| `exportDownloadDir` | `string` | `downloadDir/exported` | Directory for exported JPEGs |
| `uploadOptions` | `UploadOptions` | — | Forwarded to `uploadImages` |
| `downloadOptions` | `DownloadOptions` | — | Forwarded to `downloadFiles` |
| `pollIntervalMs` | `number` | `10000` | Initial polling interval in ms |
| `signal` | `AbortSignal` | — | Cancellation signal |

### Standalone helpers

```typescript
import { getProfiles, getProfile, checkFilesMatchProfileType } from "imagen-ai-sdk";

// List all profiles
const profiles = await getProfiles(apiKey);

// Get one profile by key
const profile = await getProfile(apiKey, 5700);

// Validate files before uploading (throws UploadError on mismatch)
checkFilesMatchProfileType(imagePaths, profile);
```

---

## Editing options

Pass `editOptions` to `startEditing` or `quickEdit`:

```typescript
await client.startEditing(projectUuid, {
  profileKey: 5700,
  editOptions: {
    crop: true,
    straighten: true,
    smoothSkin: true,
  },
});
```

| Option | Type | Description |
|---|---|---|
| `crop` | `boolean` | General auto-crop |
| `portrait_crop` | `boolean` | Portrait-specific crop |
| `headshot_crop` | `boolean` | Headshot-optimized crop |
| `straighten` | `boolean` | Auto-straighten horizons |
| `perspective_correction` | `boolean` | Perspective distortion fix |
| `smooth_skin` | `boolean` | Skin smoothing |
| `subject_mask` | `boolean` | Subject isolation |
| `sky_replacement` | `boolean` | Sky replacement |
| `sky_replacement_template_id` | `number` | Sky template to use |
| `window_pull` | `boolean` | Window exposure balance (real estate) |
| `hdr_merge` | `boolean` | HDR bracket processing |
| `crop_aspect_ratio` | `string` | Aspect ratio when cropping (use `CropAspectRatio` enum) |

**Mutual exclusivity rules** — these combinations will throw an error:

| Rule | Invalid combination |
|---|---|
| Only one crop type | `crop` + `portrait_crop`, `crop` + `headshot_crop`, `portrait_crop` + `headshot_crop` |
| Only one straightening method | `straighten` + `perspective_correction` |

Available crop ratios:

```typescript
import { CropAspectRatio } from "imagen-ai-sdk";

CropAspectRatio.RATIO_2X3  // "2X3"
CropAspectRatio.RATIO_4X5  // "4X5"
CropAspectRatio.RATIO_5X7  // "5X7"
```

---

## Photography types

Providing a photography type improves edit accuracy:

```typescript
import { PhotographyType } from "imagen-ai-sdk";

PhotographyType.WEDDING
PhotographyType.PORTRAITS
PhotographyType.REAL_ESTATE
PhotographyType.FAMILY_NEWBORN
PhotographyType.EVENTS
PhotographyType.LANDSCAPE_NATURE
PhotographyType.SPORTS
PhotographyType.BOUDOIR
PhotographyType.OTHER
PhotographyType.NO_TYPE
```

---

## Upload and download options

### `UploadOptions`

| Option | Type | Default | Description |
|---|---|---|---|
| `maxConcurrent` | `number` | `5` | Parallel uploads |
| `calculateMd5` | `boolean` | `false` | Send MD5 checksums for integrity checking |
| `onProgress` | `(current, total, file) => void` | — | Progress callback |
| `signal` | `AbortSignal` | — | Cancellation signal |

### `DownloadOptions`

| Option | Type | Default | Description |
|---|---|---|---|
| `maxConcurrent` | `number` | `5` | Parallel downloads |
| `onProgress` | `(current, total, file) => void` | — | Progress callback |
| `signal` | `AbortSignal` | — | Cancellation signal |

---

## Error handling

All errors extend `ImagenError`:

```typescript
import {
  ImagenError,
  AuthenticationError,
  ProjectError,
  UploadError,
  DownloadError,
} from "imagen-ai-sdk";

try {
  await quickEdit(apiKey, { profileKey: 5700, imagePaths });
} catch (err) {
  if (err instanceof AuthenticationError) {
    console.error("Invalid API key — check your credentials");
  } else if (err instanceof UploadError) {
    console.error("Upload failed:", err.message);
    // Common causes: mixed file types, invalid paths, network issues
  } else if (err instanceof ProjectError) {
    console.error("Project operation failed:", err.message);
    // Common causes: duplicate project name, editing failures
  } else if (err instanceof DownloadError) {
    console.error("Download failed:", err.message);
  } else if (err instanceof ImagenError) {
    console.error("SDK error:", err.message);
  }
}
```

---

## Troubleshooting

### Authentication error

```
AuthenticationError: Invalid API key or unauthorized.
```

1. Verify your API key is correct
2. Confirm support has activated your key
3. Check the environment variable is set: `echo $IMAGEN_API_KEY`

### Duplicate project name

```
ProjectError: API Error (400): Project with name 'Wedding Photos' already exists
```

Use unique names — include timestamps, client names, or session details:

```typescript
// Good
await client.createProject("Sarah_Mike_Wedding_2024_01_15");

// Good — auto-generated UUID, always unique
await client.createProject();

// Risky — generic names may already exist
await client.createProject("Wedding Photos");
```

### Mixed file types

```
UploadError: RAW profile cannot be used with JPG files: photo.jpg
```

A single project must contain only RAW **or** only JPEG files. Use `checkFilesMatchProfileType` to catch this before uploading:

```typescript
import { getProfile, checkFilesMatchProfileType } from "imagen-ai-sdk";

const profile = await getProfile(apiKey, 5700);
checkFilesMatchProfileType(imagePaths, profile); // throws early if incompatible
```

### No valid files found

```
UploadError: No valid local files found to upload.
```

1. Check that file paths exist and are correct
2. Verify the extensions are in the supported list (`SUPPORTED_EXTENSIONS`)
3. Make sure you are not mixing RAW and JPEG in one project

### Upload or download failures

```
UploadError: S3 upload failed (503)
```

1. Check your internet connection
2. Reduce `maxConcurrent` for slower connections
3. Enable `calculateMd5: true` to detect corrupted uploads
4. Retry with a smaller batch

### Module not found

```
Error [ERR_MODULE_NOT_FOUND]: Cannot find package 'imagen-ai-sdk'
```

```bash
npm install imagen-ai-sdk
```

Make sure your project has `"type": "module"` in `package.json`, or use the `.mjs` extension for your script.

---

## Cancellation

Pass an `AbortSignal` to cancel any long-running operation:

```typescript
const controller = new AbortController();
setTimeout(() => controller.abort(), 60_000); // cancel after 60 s

await client.startEditing(projectUuid, {
  profileKey: 5700,
  signal: controller.signal,
});
```

---

## Requirements

- Node.js 18 or later
- An Imagen AI API key

---

## Support & resources

- **SDK issues:** Open a GitHub issue with your SDK version, Node.js version, full error message, and a minimal reproduction
- **API & account questions:** [support.imagen-ai.com](https://support.imagen-ai.com/hc)
- **Main website:** [imagen-ai.com](https://imagen-ai.com)
- **Community:** [Imagen AI Facebook Group](https://www.facebook.com/share/g/16fydbDZ3s/)

---

## License

MIT

---

**Ready to automate your photo editing?**

```bash
npm install imagen-ai-sdk
```

**[Get started today →](https://imagen-ai.com)**
