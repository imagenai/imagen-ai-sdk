import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { ImagenClient } from "../src/client";
import { ProjectError, ImagenError, UploadError } from "../src/errors";

function mockJson(body: unknown, status = 200) {
  global.fetch = jest.fn().mockResolvedValue({
    status,
    ok: status < 400,
    statusText: status < 400 ? "OK" : "ERR",
    json: async () => body,
  } as unknown as Response);
}

function lastCall() {
  return (global.fetch as jest.Mock).mock.calls[0];
}

function tmpFile(name: string, bytes: number): string {
  const p = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "i2i-")), name);
  fs.writeFileSync(p, Buffer.alloc(bytes, 1));
  return p;
}

describe("ImagenClient I2I (Workflow D)", () => {
  let client: ImagenClient;
  beforeEach(() => (client = new ImagenClient("test-key")));
  afterEach(async () => await client.close());

  describe("project lifecycle", () => {
    it("createI2iProject returns uuid and hits /i2i/projects/", async () => {
      mockJson({ data: { project_uuid: "i2i-1" } });
      const uuid = await client.createI2iProject("My I2I");
      const [url, init] = lastCall();
      expect(url).toContain("/i2i/projects/");
      expect(init.method).toBe("POST");
      expect(JSON.parse(init.body)).toEqual({ name: "My I2I" });
      expect(uuid).toBe("i2i-1");
    });

    it("createI2iProject sends empty body when unnamed", async () => {
      mockJson({ data: { project_uuid: "i2i-2" } });
      await client.createI2iProject();
      expect(JSON.parse(lastCall()[1].body)).toEqual({});
    });

    it("listI2iProjects parses + sends params, omits is_archived when null", async () => {
      mockJson({ data: { projects: [], pagination: { total: 0, size: 5, page: 1 } } });
      const res = await client.listI2iProjects({ size: 5, page: 1, isArchived: null });
      const [url] = lastCall();
      expect(url).toContain("/i2i/projects");
      expect(url).toContain("size=5");
      expect(url).toContain("page=1");
      expect(url).not.toContain("is_archived");
      expect(res.pagination.size).toBe(5);
    });

    it("listI2iProjects throws ProjectError on bad shape", async () => {
      mockJson({ data: { nope: true } });
      await expect(client.listI2iProjects()).rejects.toThrow(ProjectError);
    });

    it("validateI2iProjectName handles bool response", async () => {
      mockJson({ data: false });
      expect(await client.validateI2iProjectName("taken")).toBe(false);
    });

    it("validateI2iProjectName handles {is_valid} object", async () => {
      mockJson({ data: { is_valid: true } });
      expect(await client.validateI2iProjectName("free")).toBe(true);
    });

    it("validateI2iProjectName treats flagless 2xx as valid", async () => {
      mockJson({ data: { something: "else" } });
      expect(await client.validateI2iProjectName("x")).toBe(true);
    });

    it("getI2iProject returns transformed item", async () => {
      mockJson({
        data: {
          project_uuid: "i2i-9",
          status: "Completed",
          created_at: "2026-06-01T00:00:00Z",
          number_of_images: 2,
          customer_reference_id: 1,
        },
      });
      const p = await client.getI2iProject("i2i-9");
      expect(p.projectUuid).toBe("i2i-9");
      expect(p.numberOfImages).toBe(2);
    });
  });

  describe("upload links + downloads", () => {
    it("getI2iUploadLink transforms response", async () => {
      mockJson({ data: { file_name: "a.jpg", upload_link: "https://s3/up" } });
      const r = await client.getI2iUploadLink("i2i-1", "a.jpg");
      expect(r.uploadLink).toBe("https://s3/up");
    });

    it("getI2iDownloadLinks maps to URL array", async () => {
      mockJson({
        data: { files_list: [{ file_name: "a.jpg", download_link: "https://s3/a" }] },
      });
      const links = await client.getI2iDownloadLinks("i2i-1");
      expect(links).toEqual(["https://s3/a"]);
      expect(lastCall()[0]).toContain("/i2i/projects/i2i-1/get_temporary_download_links");
    });

    it("getI2iDownloadLinks works against prod root-shape", async () => {
      mockJson({ files_list: [{ file_name: "a.jpg", download_link: "https://s3/a" }] });
      expect(await client.getI2iDownloadLinks("i2i-1")).toEqual(["https://s3/a"]);
    });

    it("getI2iDownloadLink returns single link (camelCase + passthrough)", async () => {
      mockJson({ data: { download_link: "https://s3/one", expires_in: 60 } });
      const r = await client.getI2iDownloadLink("i2i-1", "a.jpg");
      expect(r.downloadLink).toBe("https://s3/one");
      expect((r as Record<string, unknown>)["expires_in"]).toBe(60);
    });

    it("getI2iDownloadLink throws ImagenError on bad shape", async () => {
      mockJson({ data: { nope: true } });
      await expect(client.getI2iDownloadLink("i2i-1", "a.jpg")).rejects.toThrow(ImagenError);
    });
  });

  describe("startI2iEditing", () => {
    it("posts edit options and parses MessageResponse", async () => {
      mockJson({ data: { message: "sent for I2I editing" } });
      const res = await client.startI2iEditing("i2i-1", { perspective_correction: true });
      const [url, init] = lastCall();
      expect(url).toContain("/i2i/projects/i2i-1/edit");
      expect(init.method).toBe("POST");
      expect(JSON.parse(init.body)).toEqual({ perspective_correction: true });
      expect(res.message).toBe("sent for I2I editing");
    });

    it("posts empty body when no options", async () => {
      mockJson({ data: { message: "ok" } });
      await client.startI2iEditing("i2i-1");
      expect(JSON.parse(lastCall()[1].body)).toEqual({});
    });

    it("throws ImagenError on bad shape", async () => {
      mockJson({ data: { nope: true } });
      await expect(client.startI2iEditing("i2i-1")).rejects.toThrow(ImagenError);
    });
  });

  describe("waitForI2iCompletion", () => {
    const proj = (status: string) => ({
      data: {
        project_uuid: "i2i-1",
        status,
        created_at: "2026-06-01T00:00:00Z",
        number_of_images: 1,
        customer_reference_id: 1,
      },
    });

    it("polls until Completed", async () => {
      const bodies = [proj("In Progress"), proj("Completed")];
      global.fetch = jest.fn().mockImplementation(async () => ({
        status: 200,
        ok: true,
        statusText: "OK",
        json: async () => bodies.shift(),
      } as unknown as Response));
      const p = await client.waitForI2iCompletion("i2i-1", { pollIntervalMs: 1 });
      expect(p.status).toBe("Completed");
      expect((global.fetch as jest.Mock).mock.calls.length).toBe(2);
    });

    it("throws ProjectError on Failed", async () => {
      mockJson(proj("Failed"));
      await expect(
        client.waitForI2iCompletion("i2i-1", { pollIntervalMs: 1 })
      ).rejects.toThrow(ProjectError);
    });
  });

  describe("uploadI2iImages routing", () => {
    it("throws when no valid files", async () => {
      mockJson({});
      await expect(client.uploadI2iImages("i2i-1", ["/nope/x.jpg"])).rejects.toThrow(UploadError);
    });

    it("uploads small files via single batched PUT", async () => {
      const f = tmpFile("small.jpg", 16);
      // 1) presigned links, 2) the PUT
      global.fetch = jest
        .fn()
        .mockResolvedValueOnce({
          status: 200,
          ok: true,
          json: async () => ({
            data: { files_list: [{ file_name: "small.jpg", upload_link: "https://s3/up" }] },
          }),
        } as unknown as Response)
        .mockResolvedValueOnce({ status: 200, ok: true, statusText: "OK" } as unknown as Response);

      const summary = await client.uploadI2iImages("i2i-1", [f]);
      expect(summary.successful).toBe(1);
      const firstUrl = (global.fetch as jest.Mock).mock.calls[0][0] as string;
      expect(firstUrl).toContain("/i2i/projects/i2i-1/get_temporary_upload_links");
      const body = JSON.parse((global.fetch as jest.Mock).mock.calls[0][1].body);
      expect(body.client_type).toBe("API");
      expect(body.files_list[0].file_name).toBe("small.jpg");
    });

    it("routes large files to multipart (threshold 0)", async () => {
      const f = tmpFile("big.jpg", 12);
      let created = false;
      global.fetch = jest.fn().mockImplementation((url: string, init?: { method?: string }) => {
        const method = init?.method ?? "GET";
        if (url.includes("/multipart_uploads") && method === "POST" && !url.includes("/complete")) {
          created = true;
          return Promise.resolve({
            status: 200,
            ok: true,
            json: async () => ({
              data: { upload_id: "up1", key: "k1", parts: [{ part_number: 1, upload_url: "https://s3/p1" }] },
            }),
          });
        }
        if (method === "PUT") return Promise.resolve({ status: 200, ok: true, statusText: "OK" });
        if (url.includes("/complete")) return Promise.resolve({ status: 200, ok: true, json: async () => ({}) });
        return Promise.resolve({ status: 200, ok: true, json: async () => ({}) });
      });

      const summary = await client.uploadI2iImages("i2i-1", [f], { multipartThreshold: 0 });
      expect(created).toBe(true);
      expect(summary.successful).toBe(1);
    });
  });

  describe("uploadI2iFileMultipart", () => {
    it("creates, uploads all parts, then completes", async () => {
      const f = tmpFile("file.bin", 10);
      const calls: string[] = [];
      global.fetch = jest.fn().mockImplementation((url: string, init?: { method?: string }) => {
        const method = init?.method ?? "GET";
        if (url.includes("/multipart_uploads") && method === "POST" && !url.includes("/complete")) {
          calls.push("create");
          return Promise.resolve({
            status: 200,
            ok: true,
            json: async () => ({
              data: {
                upload_id: "up1",
                key: "k1",
                parts: [
                  { part_number: 1, upload_url: "https://s3/p1" },
                  { part_number: 2, upload_url: "https://s3/p2" },
                  { part_number: 3, upload_url: "https://s3/p3" },
                ],
              },
            }),
          });
        }
        if (method === "PUT") {
          calls.push("put");
          return Promise.resolve({ status: 200, ok: true, statusText: "OK" });
        }
        if (url.includes("/complete")) {
          calls.push("complete");
          return Promise.resolve({ status: 200, ok: true, json: async () => ({}) });
        }
        return Promise.resolve({ status: 200, ok: true, json: async () => ({}) });
      });

      const links = await client.uploadI2iFileMultipart("i2i-1", f, { partSize: 4 });
      expect(links.uploadId).toBe("up1");
      expect(calls.filter((c) => c === "put")).toHaveLength(3);
      expect(calls[0]).toBe("create");
      expect(calls[calls.length - 1]).toBe("complete");
    });

    it("aborts and throws when a part fails", async () => {
      const f = tmpFile("file.bin", 8);
      let aborted = false;
      global.fetch = jest.fn().mockImplementation((url: string, init?: { method?: string }) => {
        const method = init?.method ?? "GET";
        if (url.includes("/multipart_uploads") && method === "POST" && !url.includes("/complete")) {
          return Promise.resolve({
            status: 200,
            ok: true,
            json: async () => ({
              data: { upload_id: "up1", key: "k1", parts: [{ part_number: 1, upload_url: "https://s3/p1" }] },
            }),
          });
        }
        if (method === "PUT") return Promise.resolve({ status: 500, ok: false, statusText: "boom" });
        if (method === "DELETE") {
          aborted = true;
          return Promise.resolve({ status: 200, ok: true, json: async () => ({}) });
        }
        return Promise.resolve({ status: 200, ok: true, json: async () => ({}) });
      });

      await expect(
        client.uploadI2iFileMultipart("i2i-1", f, { partSize: 4, maxConcurrent: 1 })
      ).rejects.toThrow(UploadError);
      expect(aborted).toBe(true);
    });

    it("throws UploadError when file is missing", async () => {
      mockJson({});
      await expect(
        client.uploadI2iFileMultipart("i2i-1", "/nope/missing.bin")
      ).rejects.toThrow(UploadError);
    });
  });
});
