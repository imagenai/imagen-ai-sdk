import * as fs from "node:fs";
import * as path from "node:path";
import * as os from "node:os";
import { ImagenClient } from "../src/client";
import { ProjectError, DownloadError } from "../src/errors";

describe("ImagenClient.getDownloadLinks", () => {
  let client: ImagenClient;

  beforeEach(() => { client = new ImagenClient("test-key"); });
  afterEach(async () => { await client.close(); });

  it("returns list of download URL strings", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      status: 200, ok: true,
      json: async () => ({
        data: {
          files_list: [
            { file_name: "photo.xmp", download_link: "https://s3.example.com/photo.xmp" },
            { file_name: "photo2.xmp", download_link: "https://s3.example.com/photo2.xmp" },
          ],
        },
      }),
    } as unknown as Response);

    const links = await client.getDownloadLinks("proj-123");
    expect(links).toEqual([
      "https://s3.example.com/photo.xmp",
      "https://s3.example.com/photo2.xmp",
    ]);
  });

  it("returns empty array when no files", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      status: 200, ok: true,
      json: async () => ({ data: { files_list: [] } }),
    } as unknown as Response);

    const links = await client.getDownloadLinks("proj-123");
    expect(links).toHaveLength(0);
  });

  it("throws ProjectError on invalid response shape", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      status: 200, ok: true,
      json: async () => ({ wrong: "shape" }),
    } as unknown as Response);

    await expect(client.getDownloadLinks("proj-123")).rejects.toThrow(ProjectError);
  });

  it("calls GET on edit/get_temporary_download_links endpoint", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      status: 200, ok: true,
      json: async () => ({ data: { files_list: [] } }),
    } as unknown as Response);

    await client.getDownloadLinks("proj-xyz");
    const url = (global.fetch as jest.Mock).mock.calls[0][0] as string;
    expect(url).toContain("proj-xyz");
    expect(url).toContain("edit");
    expect(url).toContain("get_temporary_download_links");
    expect((global.fetch as jest.Mock).mock.calls[0][1].method).toBe("GET");
  });
});

describe("ImagenClient.getExportLinks", () => {
  let client: ImagenClient;

  beforeEach(() => { client = new ImagenClient("test-key"); });
  afterEach(async () => { await client.close(); });

  it("returns export URL strings", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      status: 200, ok: true,
      json: async () => ({
        data: {
          files_list: [
            { file_name: "photo.jpg", download_link: "https://s3.example.com/photo.jpg" },
          ],
        },
      }),
    } as unknown as Response);

    const links = await client.getExportLinks("proj-123");
    expect(links).toEqual(["https://s3.example.com/photo.jpg"]);
  });

  it("calls GET on export/get_temporary_download_links endpoint", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      status: 200, ok: true,
      json: async () => ({ data: { files_list: [] } }),
    } as unknown as Response);

    await client.getExportLinks("proj-abc");
    const url = (global.fetch as jest.Mock).mock.calls[0][0] as string;
    expect(url).toContain("proj-abc");
    expect(url).toContain("export");
    expect(url).toContain("get_temporary_download_links");
  });
});

describe("ImagenClient.downloadFiles", () => {
  let client: ImagenClient;
  let tmpDir: string;

  beforeEach(() => {
    client = new ImagenClient("test-key");
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "imagen-dl-"));
  });

  afterEach(async () => {
    await client.close();
    fs.rmSync(tmpDir, { recursive: true });
  });

  it("throws DownloadError when links list is empty", async () => {
    await expect(client.downloadFiles([], tmpDir)).rejects.toThrow(DownloadError);
  });

  it("downloads files and returns local paths", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      status: 200, ok: true,
      arrayBuffer: async () => Buffer.from("xmp content").buffer,
    } as unknown as Response);

    const links = ["https://s3.example.com/edited/photo.xmp"];
    const paths = await client.downloadFiles(links, tmpDir);
    expect(paths).toHaveLength(1);
    expect(paths[0]).toContain("photo.xmp");
    expect(fs.existsSync(paths[0]!)).toBe(true);
  });

  it("creates output directory if it does not exist", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      status: 200, ok: true,
      arrayBuffer: async () => Buffer.from("data").buffer,
    } as unknown as Response);

    const newDir = path.join(tmpDir, "nested", "output");
    await client.downloadFiles(["https://s3.example.com/photo.xmp"], newDir);
    expect(fs.existsSync(newDir)).toBe(true);
  });

  it("calls onProgress callback", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      status: 200, ok: true,
      arrayBuffer: async () => Buffer.from("data").buffer,
    } as unknown as Response);

    const calls: number[] = [];
    await client.downloadFiles(
      ["https://s3.example.com/photo.xmp"],
      tmpDir,
      { onProgress: (current) => calls.push(current) }
    );
    expect(calls.length).toBeGreaterThan(0);
  });

  it("throws DownloadError when all downloads fail", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      status: 500, ok: false,
      statusText: "Server Error",
      arrayBuffer: async () => Buffer.from("").buffer,
    } as unknown as Response);

    await expect(
      client.downloadFiles(["https://s3.example.com/photo.xmp"], tmpDir)
    ).rejects.toThrow(DownloadError);
  });

  it("throws Error when maxConcurrent < 1", async () => {
    await expect(
      client.downloadFiles(["https://s3.example.com/x.xmp"], tmpDir, { maxConcurrent: 0 })
    ).rejects.toThrow();
  });

  it("returns only successful downloads (partial success)", async () => {
    global.fetch = jest.fn()
      .mockResolvedValueOnce({
        status: 200, ok: true,
        arrayBuffer: async () => Buffer.from("ok").buffer,
      } as unknown as Response)
      .mockResolvedValueOnce({
        status: 500, ok: false,
        statusText: "Server Error",
        arrayBuffer: async () => Buffer.from("").buffer,
      } as unknown as Response);

    const paths = await client.downloadFiles(
      [
        "https://s3.example.com/success.xmp",
        "https://s3.example.com/fail.xmp",
      ],
      tmpDir
    );
    expect(paths).toHaveLength(1);
    expect(paths[0]).toContain("success.xmp");
  });
});
