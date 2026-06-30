import * as fs from "node:fs";
import * as path from "node:path";
import * as os from "node:os";
import { ImagenClient } from "../src/client";
import { UploadError } from "../src/errors";

describe("ImagenClient.uploadImages", () => {
  let client: ImagenClient;
  let tmpDir: string;
  let testFile: string;
  let testFile2: string;

  beforeEach(() => {
    client = new ImagenClient("test-key");
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "imagen-upload-test-"));
    testFile = path.join(tmpDir, "photo.cr2");
    testFile2 = path.join(tmpDir, "photo2.nef");
    fs.writeFileSync(testFile, Buffer.from("fake raw content"));
    fs.writeFileSync(testFile2, Buffer.from("fake raw content 2"));
  });

  afterEach(async () => {
    await client.close();
    fs.rmSync(tmpDir, { recursive: true });
  });

  it("throws UploadError when no valid files provided", async () => {
    await expect(
      client.uploadImages("proj-123", ["/nonexistent/photo.cr2"])
    ).rejects.toThrow(UploadError);
  });

  it("throws UploadError when files have unsupported extension", async () => {
    const txtFile = path.join(tmpDir, "file.txt");
    fs.writeFileSync(txtFile, "text");
    await expect(
      client.uploadImages("proj-123", [txtFile])
    ).rejects.toThrow(UploadError);
  });

  it("throws Error when maxConcurrent < 1", async () => {
    await expect(
      client.uploadImages("proj-123", [testFile], { maxConcurrent: 0 })
    ).rejects.toThrow();
  });

  it("uploads successfully and returns UploadSummary", async () => {
    global.fetch = jest.fn()
      .mockResolvedValueOnce({
        status: 200,
        ok: true,
        json: async () => ({
          data: {
            files_list: [
              { file_name: "photo.cr2", upload_link: "https://s3.example.com/upload/photo.cr2" },
            ],
          },
        }),
      } as unknown as Response)
      .mockResolvedValueOnce({
        status: 200,
        ok: true,
        json: async () => ({}),
      } as unknown as Response);

    const summary = await client.uploadImages("proj-123", [testFile]);
    expect(summary.total).toBe(1);
    expect(summary.successful).toBe(1);
    expect(summary.failed).toBe(0);
    expect(summary.results[0]?.success).toBe(true);
    expect(summary.results[0]?.error).toBeNull();
  });

  it("records failure in summary when S3 upload fails", async () => {
    global.fetch = jest.fn()
      .mockResolvedValueOnce({
        status: 200,
        ok: true,
        json: async () => ({
          data: {
            files_list: [
              { file_name: "photo.cr2", upload_link: "https://s3.example.com/upload" },
            ],
          },
        }),
      } as unknown as Response)
      .mockResolvedValueOnce({
        status: 500,
        ok: false,
        statusText: "Server Error",
        json: async () => ({}),
      } as unknown as Response);

    const summary = await client.uploadImages("proj-123", [testFile]);
    expect(summary.total).toBe(1);
    expect(summary.failed).toBe(1);
    expect(summary.successful).toBe(0);
    expect(summary.results[0]?.success).toBe(false);
    expect(summary.results[0]?.error).toBeTruthy();
  });

  it("uploads multiple files and tracks each result", async () => {
    global.fetch = jest.fn()
      .mockResolvedValueOnce({
        status: 200,
        ok: true,
        json: async () => ({
          data: {
            files_list: [
              { file_name: "photo.cr2", upload_link: "https://s3.example.com/1" },
              { file_name: "photo2.nef", upload_link: "https://s3.example.com/2" },
            ],
          },
        }),
      } as unknown as Response)
      .mockResolvedValueOnce({ status: 200, ok: true, json: async () => ({}) } as unknown as Response)
      .mockResolvedValueOnce({ status: 200, ok: true, json: async () => ({}) } as unknown as Response);

    const summary = await client.uploadImages("proj-123", [testFile, testFile2]);
    expect(summary.total).toBe(2);
    expect(summary.successful).toBe(2);
    expect(summary.results).toHaveLength(2);
  });

  it("calls onProgress callback for each file", async () => {
    global.fetch = jest.fn()
      .mockResolvedValueOnce({
        status: 200,
        ok: true,
        json: async () => ({
          data: {
            files_list: [{ file_name: "photo.cr2", upload_link: "https://s3.example.com/u" }],
          },
        }),
      } as unknown as Response)
      .mockResolvedValueOnce({ status: 200, ok: true, json: async () => ({}) } as unknown as Response);

    const calls: Array<{ current: number; total: number }> = [];
    await client.uploadImages("proj-123", [testFile], {
      onProgress: (current, total) => calls.push({ current, total }),
    });
    expect(calls.length).toBeGreaterThan(0);
    expect(calls[calls.length - 1]?.total).toBe(1);
  });

  it("calls POST to get_temporary_upload_links endpoint", async () => {
    global.fetch = jest.fn()
      .mockResolvedValueOnce({
        status: 200,
        ok: true,
        json: async () => ({
          data: {
            files_list: [{ file_name: "photo.cr2", upload_link: "https://s3.example.com/u" }],
          },
        }),
      } as unknown as Response)
      .mockResolvedValueOnce({ status: 200, ok: true, json: async () => ({}) } as unknown as Response);

    await client.uploadImages("proj-123", [testFile]);

    const firstCallUrl = (global.fetch as jest.Mock).mock.calls[0][0] as string;
    expect(firstCallUrl).toContain("get_temporary_upload_links");
  });

  it("uses PUT method for S3 upload", async () => {
    global.fetch = jest.fn()
      .mockResolvedValueOnce({
        status: 200,
        ok: true,
        json: async () => ({
          data: {
            files_list: [{ file_name: "photo.cr2", upload_link: "https://s3.example.com/u" }],
          },
        }),
      } as unknown as Response)
      .mockResolvedValueOnce({ status: 200, ok: true, json: async () => ({}) } as unknown as Response);

    await client.uploadImages("proj-123", [testFile]);

    const s3CallMethod = (global.fetch as jest.Mock).mock.calls[1][1].method;
    expect(s3CallMethod).toBe("PUT");
  });

  it("calculates md5 and includes it when calculateMd5=true", async () => {
    global.fetch = jest.fn()
      .mockResolvedValueOnce({
        status: 200,
        ok: true,
        json: async () => ({
          data: {
            files_list: [{ file_name: "photo.cr2", upload_link: "https://s3.example.com/u" }],
          },
        }),
      } as unknown as Response)
      .mockResolvedValueOnce({ status: 200, ok: true, json: async () => ({}) } as unknown as Response);

    const summary = await client.uploadImages("proj-123", [testFile], { calculateMd5: true });
    expect(summary.successful).toBe(1);

    const presignedBody = JSON.parse((global.fetch as jest.Mock).mock.calls[0][1].body);
    expect(presignedBody.files_list[0]).toHaveProperty("md5");
  });

  it("skips invalid (non-existent) paths with a warning", async () => {
    global.fetch = jest.fn()
      .mockResolvedValueOnce({
        status: 200,
        ok: true,
        json: async () => ({
          data: {
            files_list: [{ file_name: "photo.cr2", upload_link: "https://s3.example.com/u" }],
          },
        }),
      } as unknown as Response)
      .mockResolvedValueOnce({ status: 200, ok: true, json: async () => ({}) } as unknown as Response);

    const warns: string[] = [];
    const logger = {
      debug: () => {},
      info: () => {},
      warn: (msg: string) => warns.push(msg),
      error: () => {},
    };
    const c = new (client.constructor as typeof ImagenClient)("test-key", { logger });
    const summary = await c.uploadImages("proj-123", ["/totally/nonexistent/photo.cr2", testFile]);
    expect(summary.total).toBe(1);
    expect(warns.some((w) => w.includes("nonexistent"))).toBe(true);
    await c.close();
  });
});
