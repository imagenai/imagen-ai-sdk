import {
  ProfileSchema,
  ProjectCreationResponseSchema,
  PresignedUrlResponseSchema,
  StatusResponseSchema,
  DownloadLinksResponseSchema,
  EditOptionsSchema,
} from "../src/models";

describe("ProfileSchema", () => {
  it("parses valid profile and transforms snake_case to camelCase", () => {
    const raw = {
      image_type: "RAW",
      profile_key: 5700,
      profile_name: "My Wedding Profile",
      profile_type: "premium",
    };
    const result = ProfileSchema.parse(raw);
    expect(result.profileKey).toBe(5700);
    expect(result.profileName).toBe("My Wedding Profile");
    expect(result.imageType).toBe("RAW");
    expect(result.profileType).toBe("premium");
  });

  it("throws on missing profile_key", () => {
    expect(() =>
      ProfileSchema.parse({ image_type: "RAW", profile_name: "x", profile_type: "y" })
    ).toThrow();
  });
});

describe("ProjectCreationResponseSchema", () => {
  it("parses valid response and transforms project_uuid to camelCase", () => {
    const raw = { data: { project_uuid: "abc-123" } };
    const result = ProjectCreationResponseSchema.parse(raw);
    expect(result.data.projectUuid).toBe("abc-123");
  });

  it("throws on missing data.project_uuid", () => {
    expect(() => ProjectCreationResponseSchema.parse({ data: {} })).toThrow();
  });
});

describe("StatusResponseSchema", () => {
  it("parses completed status with progress", () => {
    const raw = { data: { status: "Completed", progress: 100, details: null } };
    const result = StatusResponseSchema.parse(raw);
    expect(result.data.status).toBe("Completed");
    expect(result.data.progress).toBe(100);
    expect(result.data.details).toBeNull();
  });

  it("parses status without progress (defaults to null)", () => {
    const raw = { data: { status: "Processing" } };
    const result = StatusResponseSchema.parse(raw);
    expect(result.data.progress).toBeNull();
    expect(result.data.details).toBeNull();
  });
});

describe("EditOptionsSchema", () => {
  it("accepts valid single crop option", () => {
    const result = EditOptionsSchema.parse({ crop: true });
    expect(result.crop).toBe(true);
  });

  it("accepts valid straighten option", () => {
    const result = EditOptionsSchema.parse({ straighten: true });
    expect(result.straighten).toBe(true);
  });

  it("rejects crop + portrait_crop set simultaneously", () => {
    expect(() =>
      EditOptionsSchema.parse({ crop: true, portrait_crop: true })
    ).toThrow();
  });

  it("rejects crop + headshot_crop set simultaneously", () => {
    expect(() =>
      EditOptionsSchema.parse({ crop: true, headshot_crop: true })
    ).toThrow();
  });

  it("rejects straighten + perspective_correction together", () => {
    expect(() =>
      EditOptionsSchema.parse({ straighten: true, perspective_correction: true })
    ).toThrow();
  });

  it("accepts empty options object", () => {
    expect(() => EditOptionsSchema.parse({})).not.toThrow();
  });
});

describe("DownloadLinksResponseSchema", () => {
  it("parses response and transforms to camelCase", () => {
    const raw = {
      data: {
        files_list: [
          { file_name: "photo.xmp", download_link: "https://s3.example.com/photo.xmp" },
        ],
      },
    };
    const result = DownloadLinksResponseSchema.parse(raw);
    expect(result.data.files_list[0]?.fileName).toBe("photo.xmp");
    expect(result.data.files_list[0]?.downloadLink).toBe("https://s3.example.com/photo.xmp");
  });
});
