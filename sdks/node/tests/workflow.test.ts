import * as fs from "node:fs";
import * as path from "node:path";
import * as os from "node:os";
import { ImagenClient } from "../src/client";
import { PhotographyType } from "../src/enums";

describe("Full edit workflow integration", () => {
  let client: ImagenClient;
  let tmpDir: string;
  let testFile: string;

  beforeEach(() => {
    client = new ImagenClient("test-key");
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "imagen-workflow-"));
    testFile = path.join(tmpDir, "photo.cr2");
    fs.writeFileSync(testFile, Buffer.from("fake raw content"));
  });

  afterEach(async () => {
    await client.close();
    fs.rmSync(tmpDir, { recursive: true });
  });

  it("completes the full create→upload→edit→download workflow", async () => {
    global.fetch = jest.fn()
      // createProject
      .mockResolvedValueOnce({
        status: 200, ok: true,
        json: async () => ({ data: { project_uuid: "wf-proj-001" } }),
      } as unknown as Response)
      // uploadImages — presigned URLs
      .mockResolvedValueOnce({
        status: 200, ok: true,
        json: async () => ({
          data: { files_list: [{ file_name: "photo.cr2", upload_link: "https://s3.example.com/u" }] },
        }),
      } as unknown as Response)
      // uploadImages — S3 PUT
      .mockResolvedValueOnce({ status: 200, ok: true, json: async () => ({}) } as unknown as Response)
      // startEditing — POST /edit
      .mockResolvedValueOnce({ status: 200, ok: true, json: async () => ({}) } as unknown as Response)
      // polling — Completed immediately
      .mockResolvedValueOnce({
        status: 200, ok: true,
        json: async () => ({ data: { status: "Completed", progress: 100, details: null } }),
      } as unknown as Response)
      // getDownloadLinks
      .mockResolvedValueOnce({
        status: 200, ok: true,
        json: async () => ({
          data: { files_list: [{ file_name: "photo.xmp", download_link: "https://s3.example.com/photo.xmp" }] },
        }),
      } as unknown as Response);

    const projectUuid = await client.createProject("Workflow Test");
    expect(projectUuid).toBe("wf-proj-001");

    const summary = await client.uploadImages(projectUuid, [testFile]);
    expect(summary.total).toBe(1);
    expect(summary.successful).toBe(1);

    const status = await client.startEditing(projectUuid, {
      profileKey: 5700,
      photographyType: PhotographyType.WEDDING,
      pollIntervalMs: 1,
    });
    expect(status.status).toBe("Completed");
    expect(status.progress).toBe(100);

    const links = await client.getDownloadLinks(projectUuid);
    expect(links).toHaveLength(1);
    expect(links[0]).toBe("https://s3.example.com/photo.xmp");
  });

  it("completes the full workflow including export", async () => {
    global.fetch = jest.fn()
      // createProject
      .mockResolvedValueOnce({
        status: 200, ok: true,
        json: async () => ({ data: { project_uuid: "wf-proj-002" } }),
      } as unknown as Response)
      // presigned URL
      .mockResolvedValueOnce({
        status: 200, ok: true,
        json: async () => ({
          data: { files_list: [{ file_name: "photo.cr2", upload_link: "https://s3.example.com/u" }] },
        }),
      } as unknown as Response)
      // S3 PUT
      .mockResolvedValueOnce({ status: 200, ok: true, json: async () => ({}) } as unknown as Response)
      // POST /edit
      .mockResolvedValueOnce({ status: 200, ok: true, json: async () => ({}) } as unknown as Response)
      // edit status — Completed
      .mockResolvedValueOnce({
        status: 200, ok: true,
        json: async () => ({ data: { status: "Completed", progress: 100, details: null } }),
      } as unknown as Response)
      // getDownloadLinks
      .mockResolvedValueOnce({
        status: 200, ok: true,
        json: async () => ({
          data: { files_list: [{ file_name: "photo.xmp", download_link: "https://s3.example.com/photo.xmp" }] },
        }),
      } as unknown as Response)
      // POST /export
      .mockResolvedValueOnce({ status: 200, ok: true, json: async () => ({}) } as unknown as Response)
      // export status — Completed
      .mockResolvedValueOnce({
        status: 200, ok: true,
        json: async () => ({ data: { status: "Completed", progress: 100, details: null } }),
      } as unknown as Response)
      // getExportLinks
      .mockResolvedValueOnce({
        status: 200, ok: true,
        json: async () => ({
          data: { files_list: [{ file_name: "photo.jpg", download_link: "https://s3.example.com/photo.jpg" }] },
        }),
      } as unknown as Response);

    const projectUuid = await client.createProject("Export Workflow Test");
    const summary = await client.uploadImages(projectUuid, [testFile]);
    expect(summary.successful).toBe(1);

    await client.startEditing(projectUuid, { profileKey: 5700, pollIntervalMs: 1 });
    const xmpLinks = await client.getDownloadLinks(projectUuid);
    expect(xmpLinks).toHaveLength(1);

    const exportStatus = await client.exportProject(projectUuid, { pollIntervalMs: 1 });
    expect(exportStatus.status).toBe("Completed");

    const jpgLinks = await client.getExportLinks(projectUuid);
    expect(jpgLinks).toHaveLength(1);
    expect(jpgLinks[0]).toContain("photo.jpg");
  });
});
