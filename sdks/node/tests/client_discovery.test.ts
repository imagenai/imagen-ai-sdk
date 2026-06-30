import { ImagenClient } from "../src/client";
import { ProjectError, ImagenError } from "../src/errors";

function mockJson(body: unknown, status = 200) {
  global.fetch = jest.fn().mockResolvedValue({
    status,
    ok: status < 400,
    json: async () => body,
  } as unknown as Response);
}

const PROJECT_ITEM = {
  project_id: 1,
  project_uuid: "proj-1",
  name: "Wedding A",
  status: "Completed",
  created_at: "2026-06-01T00:00:00Z",
  number_of_images: 12,
  profile: "premium",
  ai_tools: ["sky"],
  customer_reference_id: 99,
  thumbnail_src: "https://s3/thumb.jpg",
  export_status: "Completed",
};

describe("ImagenClient discovery (Workflow E)", () => {
  let client: ImagenClient;
  beforeEach(() => (client = new ImagenClient("test-key")));
  afterEach(async () => await client.close());

  describe("listProjects", () => {
    it("parses paginated response and transforms to camelCase", async () => {
      mockJson({
        data: { projects: [PROJECT_ITEM], pagination: { total: 1, size: 20, page: 0 } },
      });
      const res = await client.listProjects({ size: 20, page: 0 });
      expect(res.pagination.total).toBe(1);
      expect(res.projects[0]?.projectUuid).toBe("proj-1");
      expect(res.projects[0]?.numberOfImages).toBe(12);
      expect(res.projects[0]?.createdAt).toBe("2026-06-01T00:00:00Z");
    });

    it("sends pagination + filter query params", async () => {
      mockJson({ data: { projects: [], pagination: { total: 0, size: 5, page: 2 } } });
      await client.listProjects({ size: 5, page: 2 });
      const url = (global.fetch as jest.Mock).mock.calls[0][0] as string;
      expect(url).toContain("size=5");
      expect(url).toContain("page=2");
      expect(url).toContain("client_type=API");
      expect(url).toContain("is_archived=false");
    });

    it("omits is_archived when null", async () => {
      mockJson({ data: { projects: [], pagination: { total: 0, size: 20, page: 0 } } });
      await client.listProjects({ isArchived: null });
      const url = (global.fetch as jest.Mock).mock.calls[0][0] as string;
      expect(url).not.toContain("is_archived");
    });

    it("works against prod root-shape (no data envelope)", async () => {
      mockJson({ projects: [PROJECT_ITEM], pagination: { total: 1, size: 20, page: 0 } });
      const res = await client.listProjects();
      expect(res.projects[0]?.projectUuid).toBe("proj-1");
    });

    it("throws ProjectError on bad shape", async () => {
      mockJson({ data: { nope: true } });
      await expect(client.listProjects()).rejects.toThrow(ProjectError);
    });
  });

  describe("getProject", () => {
    it("returns a single transformed project", async () => {
      mockJson({ data: PROJECT_ITEM });
      const p = await client.getProject("proj-1");
      expect(p.projectUuid).toBe("proj-1");
      expect(p.exportStatus).toBe("Completed");
    });

    it("tolerates nullable/missing optional fields", async () => {
      mockJson({
        data: {
          project_uuid: "proj-2",
          status: "In Progress",
          created_at: "2026-06-02T00:00:00Z",
          number_of_images: 0,
          customer_reference_id: 1,
        },
      });
      const p = await client.getProject("proj-2");
      expect(p.name).toBeNull();
      expect(p.aiTools).toBeNull();
      expect(p.projectId).toBeNull();
    });
  });

  describe("getProjectUuid", () => {
    it("accepts a bare string response", async () => {
      mockJson({ data: "uuid-from-string" });
      expect(await client.getProjectUuid("My Project")).toBe("uuid-from-string");
    });

    it("accepts project_uuid object response", async () => {
      mockJson({ data: { project_uuid: "uuid-obj" } });
      expect(await client.getProjectUuid("My Project")).toBe("uuid-obj");
    });

    it("accepts uuid object response", async () => {
      mockJson({ data: { uuid: "uuid-alt" } });
      expect(await client.getProjectUuid("My Project")).toBe("uuid-alt");
    });

    it("throws ProjectError when uuid cannot be extracted", async () => {
      mockJson({ data: { something: "else" } });
      await expect(client.getProjectUuid("Missing")).rejects.toThrow(ProjectError);
    });
  });

  describe("getSkyReplacementTemplates", () => {
    it("returns transformed templates", async () => {
      mockJson({
        data: { templates: [{ id: 1, is_default: true }, { id: 2, is_default: false }] },
      });
      const t = await client.getSkyReplacementTemplates();
      expect(t).toHaveLength(2);
      expect(t[0]?.isDefault).toBe(true);
      expect(t[1]?.id).toBe(2);
    });

    it("throws ImagenError on bad shape", async () => {
      mockJson({ data: { wrong: true } });
      await expect(client.getSkyReplacementTemplates()).rejects.toThrow(ImagenError);
    });

    it("calls the templates endpoint", async () => {
      mockJson({ data: { templates: [] } });
      await client.getSkyReplacementTemplates();
      const url = (global.fetch as jest.Mock).mock.calls[0][0] as string;
      expect(url).toContain("/projects/sky_replacement/templates");
    });
  });

  describe("per-image export links", () => {
    it("getExportUploadLink transforms response", async () => {
      mockJson({ data: { file_name: "a.jpg", upload_link: "https://s3/up" } });
      const r = await client.getExportUploadLink("proj-1", "a.jpg");
      expect(r.fileName).toBe("a.jpg");
      expect(r.uploadLink).toBe("https://s3/up");
    });

    it("getExportDownloadLink transforms response", async () => {
      mockJson({ data: { file_name: "a.jpg", download_link: "https://s3/down" } });
      const r = await client.getExportDownloadLink("proj-1", "a.jpg");
      expect(r.downloadLink).toBe("https://s3/down");
    });
  });
});
