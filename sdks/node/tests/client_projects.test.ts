import { ImagenClient } from "../src/client";
import { ProjectError, ImagenError } from "../src/errors";

describe("ImagenClient.createProject", () => {
  let client: ImagenClient;

  beforeEach(() => {
    client = new ImagenClient("test-key");
  });

  afterEach(async () => {
    await client.close();
  });

  it("returns project UUID when name is provided", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      status: 200,
      ok: true,
      json: async () => ({ data: { project_uuid: "proj-abc-123" } }),
    } as unknown as Response);

    const uuid = await client.createProject("My Project");
    expect(uuid).toBe("proj-abc-123");
  });

  it("creates project without name (sends empty body)", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      status: 200,
      ok: true,
      json: async () => ({ data: { project_uuid: "proj-no-name" } }),
    } as unknown as Response);

    const uuid = await client.createProject();
    expect(uuid).toBe("proj-no-name");

    const callBody = JSON.parse((global.fetch as jest.Mock).mock.calls[0][1].body);
    expect(callBody).toEqual({});
  });

  it("sends name in body when provided", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      status: 200,
      ok: true,
      json: async () => ({ data: { project_uuid: "proj-named" } }),
    } as unknown as Response);

    await client.createProject("Test Project");

    const callBody = JSON.parse((global.fetch as jest.Mock).mock.calls[0][1].body);
    expect(callBody).toEqual({ name: "Test Project" });
  });

  it("throws ProjectError on invalid response shape", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      status: 200,
      ok: true,
      json: async () => ({ unexpected: "shape" }),
    } as unknown as Response);

    await expect(client.createProject()).rejects.toThrow(ProjectError);
  });

  it("calls POST /projects/ endpoint", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      status: 200,
      ok: true,
      json: async () => ({ data: { project_uuid: "proj-123" } }),
    } as unknown as Response);

    await client.createProject();

    const callUrl = (global.fetch as jest.Mock).mock.calls[0][0] as string;
    expect(callUrl).toContain("/projects/");
    expect((global.fetch as jest.Mock).mock.calls[0][1].method).toBe("POST");
  });
});

describe("ImagenClient.getProfiles", () => {
  let client: ImagenClient;

  beforeEach(() => {
    client = new ImagenClient("test-key");
  });

  afterEach(async () => {
    await client.close();
  });

  it("returns parsed and transformed profiles", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      status: 200,
      ok: true,
      json: async () => ({
        data: {
          profiles: [
            {
              image_type: "RAW",
              profile_key: 5700,
              profile_name: "Wedding",
              profile_type: "premium",
            },
            {
              image_type: "JPG",
              profile_key: 1234,
              profile_name: "Portraits",
              profile_type: "standard",
            },
          ],
        },
      }),
    } as unknown as Response);

    const profiles = await client.getProfiles();
    expect(profiles).toHaveLength(2);
    expect(profiles[0]?.profileKey).toBe(5700);
    expect(profiles[0]?.profileName).toBe("Wedding");
    expect(profiles[0]?.imageType).toBe("RAW");
    expect(profiles[1]?.imageType).toBe("JPG");
  });

  it("returns empty array when no profiles", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      status: 200,
      ok: true,
      json: async () => ({ data: { profiles: [] } }),
    } as unknown as Response);

    const profiles = await client.getProfiles();
    expect(profiles).toHaveLength(0);
  });

  it("throws ImagenError on invalid response shape", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      status: 200,
      ok: true,
      json: async () => ({ wrong: "shape" }),
    } as unknown as Response);

    await expect(client.getProfiles()).rejects.toThrow(ImagenError);
  });

  it("calls GET /profiles endpoint", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      status: 200,
      ok: true,
      json: async () => ({ data: { profiles: [] } }),
    } as unknown as Response);

    await client.getProfiles();

    const callUrl = (global.fetch as jest.Mock).mock.calls[0][0] as string;
    expect(callUrl).toContain("/profiles");
    expect((global.fetch as jest.Mock).mock.calls[0][1].method).toBe("GET");
  });
});
