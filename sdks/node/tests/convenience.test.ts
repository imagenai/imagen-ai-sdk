import * as fs from "node:fs";
import * as path from "node:path";
import * as os from "node:os";
import { getProfiles, getProfile, checkFilesMatchProfileType, quickEdit } from "../src/convenience";
import { UploadError } from "../src/errors";
import type { Profile } from "../src/models";
import { PhotographyType } from "../src/enums";

const makeProfile = (overrides: Partial<Profile> = {}): Profile => ({
  imageType: "RAW",
  profileKey: 5700,
  profileName: "Test Profile",
  profileType: "premium",
  ...overrides,
});

describe("checkFilesMatchProfileType", () => {
  it("passes when all files match RAW profile", () => {
    expect(() =>
      checkFilesMatchProfileType(["a.cr2", "b.nef", "c.arw"], makeProfile({ imageType: "RAW" }))
    ).not.toThrow();
  });

  it("passes when all files match JPG profile", () => {
    expect(() =>
      checkFilesMatchProfileType(["a.jpg", "b.jpeg"], makeProfile({ imageType: "JPG" }))
    ).not.toThrow();
  });

  it("throws UploadError when RAW profile receives JPG files", () => {
    expect(() =>
      checkFilesMatchProfileType(["a.jpg"], makeProfile({ imageType: "RAW" }))
    ).toThrow(UploadError);
  });

  it("throws UploadError when JPG profile receives RAW files", () => {
    expect(() =>
      checkFilesMatchProfileType(["a.cr2"], makeProfile({ imageType: "JPG" }))
    ).toThrow(UploadError);
  });

  it("throws UploadError on unsupported file types with RAW profile", () => {
    expect(() =>
      checkFilesMatchProfileType(["a.png"], makeProfile({ imageType: "RAW" }))
    ).toThrow(UploadError);
  });

  it("throws UploadError on unsupported file types with JPG profile", () => {
    expect(() =>
      checkFilesMatchProfileType(["a.txt"], makeProfile({ imageType: "JPG" }))
    ).toThrow(UploadError);
  });

  it("throws UploadError on unknown profile image type", () => {
    expect(() =>
      checkFilesMatchProfileType(["a.cr2"], makeProfile({ imageType: "HEIC" }))
    ).toThrow(UploadError);
  });

  it("error message includes the offending file list", () => {
    try {
      checkFilesMatchProfileType(["a.jpg", "b.jpg"], makeProfile({ imageType: "RAW" }));
    } catch (e) {
      expect(String(e)).toContain("a.jpg");
    }
  });
});

describe("getProfile", () => {
  it("throws UploadError when profile key not found", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      status: 200, ok: true,
      json: async () => ({ data: { profiles: [] } }),
    } as unknown as Response);

    await expect(getProfile("api-key", 9999)).rejects.toThrow(UploadError);
  });

  it("returns matching profile by key", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      status: 200, ok: true,
      json: async () => ({
        data: {
          profiles: [
            { image_type: "RAW", profile_key: 5700, profile_name: "Wedding", profile_type: "premium" },
            { image_type: "JPG", profile_key: 1234, profile_name: "Portraits", profile_type: "standard" },
          ],
        },
      }),
    } as unknown as Response);

    const profile = await getProfile("api-key", 5700);
    expect(profile.profileKey).toBe(5700);
    expect(profile.profileName).toBe("Wedding");
  });

  it("throws UploadError when key does not match any profile", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      status: 200, ok: true,
      json: async () => ({
        data: {
          profiles: [
            { image_type: "RAW", profile_key: 5700, profile_name: "Wedding", profile_type: "premium" },
          ],
        },
      }),
    } as unknown as Response);

    await expect(getProfile("api-key", 9999)).rejects.toThrow(UploadError);
  });
});

describe("getProfiles (standalone)", () => {
  it("returns all profiles", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      status: 200, ok: true,
      json: async () => ({
        data: {
          profiles: [
            { image_type: "RAW", profile_key: 5700, profile_name: "Wedding", profile_type: "premium" },
          ],
        },
      }),
    } as unknown as Response);

    const profiles = await getProfiles("api-key");
    expect(profiles).toHaveLength(1);
    expect(profiles[0]?.profileKey).toBe(5700);
  });
});

// ---------------------------------------------------------------------------
// quickEdit helpers
// ---------------------------------------------------------------------------

const PROFILE_RESPONSE = {
  status: 200, ok: true,
  json: async () => ({
    data: {
      profiles: [
        { image_type: "RAW", profile_key: 5700, profile_name: "Wedding", profile_type: "premium" },
      ],
    },
  }),
} as unknown as Response;

const PROJECT_RESPONSE = {
  status: 200, ok: true,
  json: async () => ({ data: { project_uuid: "qe-proj-001" } }),
} as unknown as Response;

const presignedResponse = (fileName: string) => ({
  status: 200, ok: true,
  json: async () => ({
    data: { files_list: [{ file_name: fileName, upload_link: "https://s3.example.com/u" }] },
  }),
} as unknown as Response);

const S3_OK = { status: 200, ok: true, json: async () => ({}) } as unknown as Response;
const EDIT_POST_OK = { status: 200, ok: true, json: async () => ({}) } as unknown as Response;
const EDIT_STATUS_DONE = {
  status: 200, ok: true,
  json: async () => ({ data: { status: "Completed", progress: 100, details: null } }),
} as unknown as Response;
const DOWNLOAD_LINKS_RESPONSE = {
  status: 200, ok: true,
  json: async () => ({
    data: { files_list: [{ file_name: "photo.xmp", download_link: "https://s3.example.com/photo.xmp" }] },
  }),
} as unknown as Response;
const EXPORT_POST_OK = { status: 200, ok: true, json: async () => ({}) } as unknown as Response;
const EXPORT_STATUS_DONE = {
  status: 200, ok: true,
  json: async () => ({ data: { status: "Completed", progress: 100, details: null } }),
} as unknown as Response;
const EXPORT_LINKS_RESPONSE = {
  status: 200, ok: true,
  json: async () => ({
    data: { files_list: [{ file_name: "photo.jpg", download_link: "https://s3.example.com/photo.jpg" }] },
  }),
} as unknown as Response;

describe("quickEdit", () => {
  let tmpDir: string;
  let testFile: string;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "imagen-qe-"));
    testFile = path.join(tmpDir, "photo.cr2");
    fs.writeFileSync(testFile, Buffer.from("fake raw content"));
  });

  afterEach(() => {
    fs.rmSync(tmpDir, { recursive: true });
  });

  it("runs full edit workflow without download or export", async () => {
    global.fetch = jest.fn()
      .mockResolvedValueOnce(PROFILE_RESPONSE)
      .mockResolvedValueOnce(PROJECT_RESPONSE)
      .mockResolvedValueOnce(presignedResponse("photo.cr2"))
      .mockResolvedValueOnce(S3_OK)
      .mockResolvedValueOnce(EDIT_POST_OK)
      .mockResolvedValueOnce(EDIT_STATUS_DONE)
      .mockResolvedValueOnce(DOWNLOAD_LINKS_RESPONSE);

    const result = await quickEdit("api-key", {
      profileKey: 5700,
      imagePaths: [testFile],
      projectName: "Test",
      photographyType: PhotographyType.WEDDING,
      pollIntervalMs: 1,
    });

    expect(result.projectUuid).toBe("qe-proj-001");
    expect(result.uploadSummary.successful).toBe(1);
    expect(result.downloadLinks).toHaveLength(1);
    expect(result.exportLinks).toBeNull();
    expect(result.downloadedFiles).toBeNull();
    expect(result.exportedFiles).toBeNull();
  });

  it("runs full workflow with export=true", async () => {
    global.fetch = jest.fn()
      .mockResolvedValueOnce(PROFILE_RESPONSE)
      .mockResolvedValueOnce(PROJECT_RESPONSE)
      .mockResolvedValueOnce(presignedResponse("photo.cr2"))
      .mockResolvedValueOnce(S3_OK)
      .mockResolvedValueOnce(EDIT_POST_OK)
      .mockResolvedValueOnce(EDIT_STATUS_DONE)
      .mockResolvedValueOnce(DOWNLOAD_LINKS_RESPONSE)
      .mockResolvedValueOnce(EXPORT_POST_OK)
      .mockResolvedValueOnce(EXPORT_STATUS_DONE)
      .mockResolvedValueOnce(EXPORT_LINKS_RESPONSE);

    const result = await quickEdit("api-key", {
      profileKey: 5700,
      imagePaths: [testFile],
      export: true,
      pollIntervalMs: 1,
    });

    expect(result.exportLinks).toHaveLength(1);
    expect(result.exportLinks![0]).toContain("photo.jpg");
    expect(result.downloadedFiles).toBeNull();
    expect(result.exportedFiles).toBeNull();
  });

  it("downloads XMP files when download=true", async () => {
    global.fetch = jest.fn()
      .mockResolvedValueOnce(PROFILE_RESPONSE)
      .mockResolvedValueOnce(PROJECT_RESPONSE)
      .mockResolvedValueOnce(presignedResponse("photo.cr2"))
      .mockResolvedValueOnce(S3_OK)
      .mockResolvedValueOnce(EDIT_POST_OK)
      .mockResolvedValueOnce(EDIT_STATUS_DONE)
      .mockResolvedValueOnce(DOWNLOAD_LINKS_RESPONSE)
      // downloadFiles fetch
      .mockResolvedValueOnce({
        status: 200, ok: true,
        arrayBuffer: async () => Buffer.from("xmp content").buffer,
      } as unknown as Response);

    const downloadDir = path.join(tmpDir, "out");
    const result = await quickEdit("api-key", {
      profileKey: 5700,
      imagePaths: [testFile],
      download: true,
      downloadDir,
      pollIntervalMs: 1,
    });

    expect(result.downloadedFiles).toHaveLength(1);
    expect(result.exportedFiles).toBeNull();
  });

  it("downloads XMP and export JPGs when download=true and export=true", async () => {
    global.fetch = jest.fn()
      .mockResolvedValueOnce(PROFILE_RESPONSE)
      .mockResolvedValueOnce(PROJECT_RESPONSE)
      .mockResolvedValueOnce(presignedResponse("photo.cr2"))
      .mockResolvedValueOnce(S3_OK)
      .mockResolvedValueOnce(EDIT_POST_OK)
      .mockResolvedValueOnce(EDIT_STATUS_DONE)
      .mockResolvedValueOnce(DOWNLOAD_LINKS_RESPONSE)
      .mockResolvedValueOnce(EXPORT_POST_OK)
      .mockResolvedValueOnce(EXPORT_STATUS_DONE)
      .mockResolvedValueOnce(EXPORT_LINKS_RESPONSE)
      // download XMP
      .mockResolvedValueOnce({
        status: 200, ok: true,
        arrayBuffer: async () => Buffer.from("xmp content").buffer,
      } as unknown as Response)
      // download JPG
      .mockResolvedValueOnce({
        status: 200, ok: true,
        arrayBuffer: async () => Buffer.from("jpg content").buffer,
      } as unknown as Response);

    const downloadDir = path.join(tmpDir, "out");
    const result = await quickEdit("api-key", {
      profileKey: 5700,
      imagePaths: [testFile],
      export: true,
      download: true,
      downloadDir,
      pollIntervalMs: 1,
    });

    expect(result.downloadedFiles).toHaveLength(1);
    expect(result.exportedFiles).toHaveLength(1);
  });

  it("uses exportDownloadDir when provided", async () => {
    global.fetch = jest.fn()
      .mockResolvedValueOnce(PROFILE_RESPONSE)
      .mockResolvedValueOnce(PROJECT_RESPONSE)
      .mockResolvedValueOnce(presignedResponse("photo.cr2"))
      .mockResolvedValueOnce(S3_OK)
      .mockResolvedValueOnce(EDIT_POST_OK)
      .mockResolvedValueOnce(EDIT_STATUS_DONE)
      .mockResolvedValueOnce(DOWNLOAD_LINKS_RESPONSE)
      .mockResolvedValueOnce(EXPORT_POST_OK)
      .mockResolvedValueOnce(EXPORT_STATUS_DONE)
      .mockResolvedValueOnce(EXPORT_LINKS_RESPONSE)
      .mockResolvedValueOnce({
        status: 200, ok: true,
        arrayBuffer: async () => Buffer.from("xmp").buffer,
      } as unknown as Response)
      .mockResolvedValueOnce({
        status: 200, ok: true,
        arrayBuffer: async () => Buffer.from("jpg").buffer,
      } as unknown as Response);

    const downloadDir = path.join(tmpDir, "xmp-out");
    const exportDownloadDir = path.join(tmpDir, "jpg-out");
    const result = await quickEdit("api-key", {
      profileKey: 5700,
      imagePaths: [testFile],
      export: true,
      download: true,
      downloadDir,
      exportDownloadDir,
      pollIntervalMs: 1,
    });

    expect(result.exportedFiles![0]).toContain("jpg-out");
  });

  it("throws UploadError when profile is not found", async () => {
    global.fetch = jest.fn().mockResolvedValueOnce({
      status: 200, ok: true,
      json: async () => ({ data: { profiles: [] } }),
    } as unknown as Response);

    await expect(
      quickEdit("api-key", { profileKey: 9999, imagePaths: [testFile], pollIntervalMs: 1 })
    ).rejects.toThrow(UploadError);
  });

  it("throws UploadError when no files upload successfully", async () => {
    global.fetch = jest.fn()
      .mockResolvedValueOnce(PROFILE_RESPONSE)
      .mockResolvedValueOnce(PROJECT_RESPONSE)
      .mockResolvedValueOnce(presignedResponse("photo.cr2"))
      // S3 fails
      .mockResolvedValueOnce({ status: 500, ok: false, statusText: "Server Error", json: async () => ({}) } as unknown as Response);

    await expect(
      quickEdit("api-key", { profileKey: 5700, imagePaths: [testFile], pollIntervalMs: 1 })
    ).rejects.toThrow(UploadError);
  });

  it("passes editOptions to startEditing when provided", async () => {
    global.fetch = jest.fn()
      .mockResolvedValueOnce(PROFILE_RESPONSE)
      .mockResolvedValueOnce(PROJECT_RESPONSE)
      .mockResolvedValueOnce(presignedResponse("photo.cr2"))
      .mockResolvedValueOnce(S3_OK)
      .mockResolvedValueOnce(EDIT_POST_OK)
      .mockResolvedValueOnce(EDIT_STATUS_DONE)
      .mockResolvedValueOnce(DOWNLOAD_LINKS_RESPONSE);

    const result = await quickEdit("api-key", {
      profileKey: 5700,
      imagePaths: [testFile],
      editOptions: { crop: true },
      pollIntervalMs: 1,
    });

    expect(result.projectUuid).toBe("qe-proj-001");
  });

  it("accepts baseUrl option", async () => {
    global.fetch = jest.fn()
      .mockResolvedValueOnce(PROFILE_RESPONSE)
      .mockResolvedValueOnce(PROJECT_RESPONSE)
      .mockResolvedValueOnce(presignedResponse("photo.cr2"))
      .mockResolvedValueOnce(S3_OK)
      .mockResolvedValueOnce(EDIT_POST_OK)
      .mockResolvedValueOnce(EDIT_STATUS_DONE)
      .mockResolvedValueOnce(DOWNLOAD_LINKS_RESPONSE);

    const result = await quickEdit("api-key", {
      profileKey: 5700,
      imagePaths: [testFile],
      baseUrl: "https://custom.api.example.com/v1",
      pollIntervalMs: 1,
    });

    expect(result.projectUuid).toBe("qe-proj-001");
    const firstUrl = (global.fetch as jest.Mock).mock.calls[0][0] as string;
    expect(firstUrl).toContain("custom.api.example.com");
  });
});
