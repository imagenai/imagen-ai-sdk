import {
  isValidImageFile,
  isRawFile,
  isJpgFile,
  extractFilenameFromUrl,
  RAW_EXTENSIONS,
  JPG_EXTENSIONS,
  SUPPORTED_EXTENSIONS,
} from "../src/utils";

describe("RAW_EXTENSIONS", () => {
  it("contains expected RAW formats", () => {
    expect(RAW_EXTENSIONS.has(".arw")).toBe(true);
    expect(RAW_EXTENSIONS.has(".cr2")).toBe(true);
    expect(RAW_EXTENSIONS.has(".cr3")).toBe(true);
    expect(RAW_EXTENSIONS.has(".nef")).toBe(true);
    expect(RAW_EXTENSIONS.has(".dng")).toBe(true);
    expect(RAW_EXTENSIONS.has(".orf")).toBe(true);
    expect(RAW_EXTENSIONS.has(".raf")).toBe(true);
    expect(RAW_EXTENSIONS.has(".rw2")).toBe(true);
  });

  it("does not contain non-RAW formats", () => {
    expect(RAW_EXTENSIONS.has(".jpg")).toBe(false);
    expect(RAW_EXTENSIONS.has(".png")).toBe(false);
    expect(RAW_EXTENSIONS.has(".txt")).toBe(false);
  });
});

describe("JPG_EXTENSIONS", () => {
  it("contains .jpg and .jpeg only", () => {
    expect(JPG_EXTENSIONS.has(".jpg")).toBe(true);
    expect(JPG_EXTENSIONS.has(".jpeg")).toBe(true);
    expect(JPG_EXTENSIONS.size).toBe(2);
  });
});

describe("SUPPORTED_EXTENSIONS", () => {
  it("is the union of RAW and JPG extensions", () => {
    for (const ext of RAW_EXTENSIONS) {
      expect(SUPPORTED_EXTENSIONS.has(ext)).toBe(true);
    }
    expect(SUPPORTED_EXTENSIONS.has(".jpg")).toBe(true);
    expect(SUPPORTED_EXTENSIONS.has(".jpeg")).toBe(true);
  });
});

describe("isValidImageFile", () => {
  it("accepts RAW formats", () => {
    expect(isValidImageFile("photo.cr2")).toBe(true);
    expect(isValidImageFile("photo.nef")).toBe(true);
    expect(isValidImageFile("photo.arw")).toBe(true);
    expect(isValidImageFile("photo.dng")).toBe(true);
  });

  it("is case-insensitive", () => {
    expect(isValidImageFile("photo.CR2")).toBe(true);
    expect(isValidImageFile("photo.NEF")).toBe(true);
    expect(isValidImageFile("photo.JPG")).toBe(true);
    expect(isValidImageFile("PHOTO.JPEG")).toBe(true);
  });

  it("accepts JPG formats", () => {
    expect(isValidImageFile("photo.jpg")).toBe(true);
    expect(isValidImageFile("photo.jpeg")).toBe(true);
  });

  it("accepts full paths", () => {
    expect(isValidImageFile("/path/to/photo.cr2")).toBe(true);
    expect(isValidImageFile("./relative/photo.jpg")).toBe(true);
  });

  it("rejects unsupported formats", () => {
    expect(isValidImageFile("photo.txt")).toBe(false);
    expect(isValidImageFile("photo.png")).toBe(false);
    expect(isValidImageFile("photo.gif")).toBe(false);
    expect(isValidImageFile("photo.tiff")).toBe(false);
  });

  it("rejects files with no extension", () => {
    expect(isValidImageFile("photo")).toBe(false);
    expect(isValidImageFile("photofile")).toBe(false);
  });
});

describe("isRawFile", () => {
  it("returns true for RAW files", () => {
    expect(isRawFile("photo.cr2")).toBe(true);
    expect(isRawFile("photo.ARW")).toBe(true);
  });

  it("returns false for JPG files", () => {
    expect(isRawFile("photo.jpg")).toBe(false);
  });
});

describe("isJpgFile", () => {
  it("returns true for JPG files", () => {
    expect(isJpgFile("photo.jpg")).toBe(true);
    expect(isJpgFile("photo.JPEG")).toBe(true);
  });

  it("returns false for RAW files", () => {
    expect(isJpgFile("photo.cr2")).toBe(false);
  });
});

describe("extractFilenameFromUrl", () => {
  it("extracts filename from S3 URL with query string", () => {
    const url = "https://s3.amazonaws.com/bucket/path/photo.xmp?X-Amz-Signature=abc123";
    expect(extractFilenameFromUrl(url, 0)).toBe("photo.xmp");
  });

  it("extracts filename with URL encoding", () => {
    const url = "https://s3.amazonaws.com/bucket/my%20photo.xmp";
    expect(extractFilenameFromUrl(url, 0)).toBe("my photo.xmp");
  });

  it("falls back to index-based name when URL has no filename", () => {
    expect(extractFilenameFromUrl("https://example.com/", 0)).toBe("imagen_edited_00001.jpg");
    expect(extractFilenameFromUrl("https://example.com/", 3)).toBe("imagen_edited_00004.jpg");
  });

  it("falls back when URL path has no extension", () => {
    expect(extractFilenameFromUrl("https://example.com/somepath", 0)).toBe("imagen_edited_00001.jpg");
  });

  it("falls back on invalid URL", () => {
    expect(extractFilenameFromUrl("not-a-url", 2)).toBe("imagen_edited_00003.jpg");
  });

  it("pads index to 5 digits", () => {
    expect(extractFilenameFromUrl("https://example.com/", 99)).toBe("imagen_edited_00100.jpg");
  });
});
