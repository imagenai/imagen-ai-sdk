import { ImagenClient } from "../src/client";
import { AuthenticationError, ImagenError } from "../src/errors";

describe("ImagenClient construction", () => {
  it("throws on empty API key", () => {
    expect(() => new ImagenClient("")).toThrow("API key cannot be empty");
  });

  it("throws on whitespace-only API key", () => {
    expect(() => new ImagenClient("   ")).toThrow("API key cannot be empty");
  });

  it("constructs with valid API key", () => {
    const client = new ImagenClient("test-key");
    expect(client).toBeInstanceOf(ImagenClient);
  });

  it("strips trailing slash from baseUrl option", () => {
    const client = new ImagenClient("key", { baseUrl: "https://api.example.com/" });
    // access via casting since baseUrl is private
    expect((client as unknown as { baseUrl: string }).baseUrl).toBe("https://api.example.com");
  });

  it("uses default baseUrl when not provided", () => {
    const client = new ImagenClient("key");
    expect((client as unknown as { baseUrl: string }).baseUrl).toContain("imagen-ai.com");
  });

  it("implements Symbol.asyncDispose", async () => {
    const client = new ImagenClient("key");
    await expect(client[Symbol.asyncDispose]()).resolves.toBeUndefined();
  });

  it("accepts a custom logger", async () => {
    const logs: string[] = [];
    const logger = {
      debug: (msg: string) => logs.push(`DEBUG: ${msg}`),
      info: (msg: string) => logs.push(`INFO: ${msg}`),
      warn: (msg: string) => logs.push(`WARN: ${msg}`),
      error: (msg: string) => logs.push(`ERROR: ${msg}`),
    };
    const client = new ImagenClient("key", { logger });
    await client.close();
    // logger should have been called (debug message on init)
    expect(logs.some(l => l.startsWith("DEBUG:"))).toBe(true);
  });
});

describe("ImagenClient._makeRequest", () => {
  let client: ImagenClient;

  beforeEach(() => {
    client = new ImagenClient("test-key");
  });

  afterEach(async () => {
    await client.close();
  });

  it("throws AuthenticationError on 401", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      status: 401,
      ok: false,
      json: async () => ({}),
      text: async () => "Unauthorized",
    } as unknown as Response);

    await expect(
      (client as unknown as { _makeRequest: (m: string, e: string) => Promise<unknown> })
        ._makeRequest("GET", "/test")
    ).rejects.toThrow(AuthenticationError);
  });

  it("throws ImagenError on 500 with JSON detail field", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      status: 500,
      ok: false,
      json: async () => ({ detail: "Internal server error" }),
      text: async () => "error",
    } as unknown as Response);

    await expect(
      (client as unknown as { _makeRequest: (m: string, e: string) => Promise<unknown> })
        ._makeRequest("GET", "/test")
    ).rejects.toThrow("API Error (500): Internal server error");
  });

  it("throws ImagenError on 400 when JSON parse fails (uses statusText)", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      status: 400,
      ok: false,
      json: async () => { throw new Error("not json"); },
      statusText: "Bad Request",
      text: async () => "Bad Request",
    } as unknown as Response);

    await expect(
      (client as unknown as { _makeRequest: (m: string, e: string) => Promise<unknown> })
        ._makeRequest("GET", "/test")
    ).rejects.toThrow(ImagenError);
  });

  it("returns empty object on 204 No Content", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      status: 204,
      ok: true,
      json: async () => ({}),
    } as unknown as Response);

    const result = await (client as unknown as { _makeRequest: (m: string, e: string) => Promise<unknown> })
      ._makeRequest("DELETE", "/test");
    expect(result).toEqual({});
  });

  it("returns parsed JSON on 200", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      status: 200,
      ok: true,
      json: async () => ({ data: "ok" }),
    } as unknown as Response);

    const result = await (client as unknown as { _makeRequest: (m: string, e: string) => Promise<unknown> })
      ._makeRequest("GET", "/test");
    expect(result).toEqual({ data: "ok" });
  });

  it("throws ImagenError on network failure (fetch throws)", async () => {
    global.fetch = jest.fn().mockRejectedValue(new TypeError("fetch failed"));

    await expect(
      (client as unknown as { _makeRequest: (m: string, e: string) => Promise<unknown> })
        ._makeRequest("GET", "/test")
    ).rejects.toThrow(ImagenError);
  });

  it("sends x-api-key header", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      status: 200,
      ok: true,
      json: async () => ({}),
    } as unknown as Response);

    await (client as unknown as { _makeRequest: (m: string, e: string) => Promise<unknown> })
      ._makeRequest("GET", "/test");

    const callArgs = (global.fetch as jest.Mock).mock.calls[0];
    expect(callArgs[1].headers["x-api-key"]).toBe("test-key");
  });
});
