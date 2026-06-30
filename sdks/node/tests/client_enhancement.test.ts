import { ImagenClient } from "../src/client";
import { ImagenError } from "../src/errors";
import { ProjectSource } from "../src/enums";

function mockJson(body: unknown, status = 200) {
  global.fetch = jest.fn().mockResolvedValue({
    status,
    ok: status < 400,
    json: async () => body,
  } as unknown as Response);
}

function lastCall() {
  return (global.fetch as jest.Mock).mock.calls[0];
}

describe("ImagenClient enhancement (Workflow C)", () => {
  let client: ImagenClient;
  beforeEach(() => (client = new ImagenClient("test-key")));
  afterEach(async () => await client.close());

  describe("getAiTools", () => {
    it("parses tools and transforms to camelCase", async () => {
      mockJson({
        data: {
          prompts: [
            { enhancement_type: "warm", label: "Warm", enabled_for_batch: true },
            { enhancement_type: "cool" },
          ],
        },
      });
      const res = await client.getAiTools("proj-1");
      expect(res.prompts).toHaveLength(2);
      expect(res.prompts[0]?.enhancementType).toBe("warm");
      expect(res.prompts[0]?.enabledForBatch).toBe(true);
      expect(res.prompts[1]?.label).toBeNull();
    });

    it("sends GET with project_source query param", async () => {
      mockJson({ data: { prompts: [] } });
      await client.getAiTools("proj-1", ProjectSource.I2I);
      const [url, init] = lastCall();
      expect(url).toContain("/projects/proj-1/ai-tools");
      expect(url).toContain("project_source=I2I");
      expect(init.method).toBe("GET");
    });

    it("works against prod root-shape (no data envelope)", async () => {
      mockJson({ prompts: [{ enhancement_type: "warm" }] });
      const res = await client.getAiTools("proj-1");
      expect(res.prompts[0]?.enhancementType).toBe("warm");
    });

    it("preserves provider-added fields (passthrough)", async () => {
      mockJson({ data: { prompts: [{ enhancement_type: "x", extra_flag: 7 }] } });
      const res = await client.getAiTools("proj-1");
      expect((res.prompts[0] as Record<string, unknown>)["extra_flag"]).toBe(7);
    });

    it("throws ImagenError on bad shape", async () => {
      mockJson({ data: { prompts: [{ no_type: true }] } });
      await expect(client.getAiTools("proj-1")).rejects.toThrow(ImagenError);
    });
  });

  describe("enhanceImage", () => {
    it("posts tool_id + default project_source and parses result", async () => {
      mockJson({
        data: { status: "SUCCESS", version_id: 3, enhanced_image_url: "https://s3/e.jpg" },
      });
      const res = await client.enhanceImage("proj-1", "img.jpg", "warm");
      const [url, init] = lastCall();
      expect(url).toContain("/projects/proj-1/images/img.jpg/enhance");
      expect(init.method).toBe("POST");
      expect(JSON.parse(init.body)).toEqual({ tool_id: "warm", project_source: "REGULAR" });
      expect(res.status).toBe("SUCCESS");
      expect(res.versionId).toBe(3);
      expect(res.enhancedImageUrl).toBe("https://s3/e.jpg");
    });

    it("includes parent_version_id when provided", async () => {
      mockJson({ data: { status: "SUCCESS", enhanced_image_url: "https://s3/e.jpg" } });
      await client.enhanceImage("proj-1", "img.jpg", "warm", {
        parentVersionId: 9,
        projectSource: ProjectSource.I2I,
      });
      expect(JSON.parse(lastCall()[1].body)).toEqual({
        tool_id: "warm",
        project_source: "I2I",
        parent_version_id: 9,
      });
    });

    it("tolerates missing version_id (null)", async () => {
      mockJson({ data: { status: "SUCCESS", enhanced_image_url: "https://s3/e.jpg" } });
      const res = await client.enhanceImage("proj-1", "img.jpg", "warm");
      expect(res.versionId).toBeNull();
    });

    it("throws ImagenError on bad shape", async () => {
      mockJson({ data: { status: "SUCCESS" } });
      await expect(client.enhanceImage("proj-1", "img.jpg", "warm")).rejects.toThrow(ImagenError);
    });
  });

  describe("applyCopilot", () => {
    it("posts instruction and parses result", async () => {
      mockJson({ data: { status: "SUCCESS", enhanced_image_url: "https://s3/c.jpg" } });
      const res = await client.applyCopilot("proj-1", "img.jpg", "add warm light");
      const [url, init] = lastCall();
      expect(url).toContain("/projects/proj-1/images/img.jpg/copilot");
      expect(init.method).toBe("POST");
      expect(JSON.parse(init.body)).toEqual({
        instruction: "add warm light",
        project_source: "REGULAR",
      });
      expect(res.enhancedImageUrl).toBe("https://s3/c.jpg");
    });

    it("rejects empty instruction", async () => {
      mockJson({ data: {} });
      await expect(client.applyCopilot("proj-1", "img.jpg", "")).rejects.toThrow(ImagenError);
    });

    it("rejects instruction over 255 chars", async () => {
      mockJson({ data: {} });
      await expect(
        client.applyCopilot("proj-1", "img.jpg", "x".repeat(256))
      ).rejects.toThrow(ImagenError);
    });

    it("includes parent_version_id when provided", async () => {
      mockJson({ data: { status: "SUCCESS", enhanced_image_url: "https://s3/c.jpg" } });
      await client.applyCopilot("proj-1", "img.jpg", "tweak", { parentVersionId: 2 });
      expect(JSON.parse(lastCall()[1].body)).toEqual({
        instruction: "tweak",
        project_source: "REGULAR",
        parent_version_id: 2,
      });
    });
  });

  describe("resetCopilot", () => {
    it("sends DELETE with project_source and returns void", async () => {
      mockJson({}, 204);
      const res = await client.resetCopilot("proj-1", "img.jpg");
      const [url, init] = lastCall();
      expect(url).toContain("/projects/proj-1/images/img.jpg/copilot");
      expect(init.method).toBe("DELETE");
      expect(JSON.parse(init.body)).toEqual({ project_source: "REGULAR" });
      expect(res).toBeUndefined();
    });
  });

  describe("finalizeProject", () => {
    it("posts and maps files_list to download URLs", async () => {
      mockJson({
        data: {
          files_list: [
            { file_name: "a.jpg", download_link: "https://s3/a" },
            { file_name: "b.jpg", download_link: "https://s3/b" },
          ],
        },
      });
      const links = await client.finalizeProject("proj-1");
      const [url, init] = lastCall();
      expect(url).toContain("/projects/proj-1/finalize");
      expect(init.method).toBe("POST");
      expect(JSON.parse(init.body)).toEqual({ project_source: "REGULAR" });
      expect(links).toEqual(["https://s3/a", "https://s3/b"]);
    });

    it("throws ImagenError on bad shape", async () => {
      mockJson({ data: { nope: true } });
      await expect(client.finalizeProject("proj-1")).rejects.toThrow(ImagenError);
    });
  });
});
