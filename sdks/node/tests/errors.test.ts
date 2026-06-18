import {
  ImagenError,
  AuthenticationError,
  ProjectError,
  UploadError,
  DownloadError,
} from "../src/errors";

describe("Error hierarchy", () => {
  it("ImagenError extends Error", () => {
    const err = new ImagenError("base");
    expect(err).toBeInstanceOf(Error);
    expect(err.message).toBe("base");
    expect(err.name).toBe("ImagenError");
  });

  it("AuthenticationError extends ImagenError", () => {
    const err = new AuthenticationError("bad key");
    expect(err).toBeInstanceOf(ImagenError);
    expect(err).toBeInstanceOf(Error);
    expect(err.name).toBe("AuthenticationError");
  });

  it("ProjectError extends ImagenError", () => {
    const err = new ProjectError("project failed");
    expect(err).toBeInstanceOf(ImagenError);
    expect(err.name).toBe("ProjectError");
  });

  it("UploadError extends ImagenError", () => {
    const err = new UploadError("upload failed");
    expect(err).toBeInstanceOf(ImagenError);
    expect(err.name).toBe("UploadError");
  });

  it("DownloadError extends ImagenError", () => {
    const err = new DownloadError("download failed");
    expect(err).toBeInstanceOf(ImagenError);
    expect(err.name).toBe("DownloadError");
  });

  it("error subclasses are not instanceof each other", () => {
    const authErr = new AuthenticationError("auth");
    const projErr = new ProjectError("proj");
    const uploadErr = new UploadError("upload");
    const downloadErr = new DownloadError("download");

    expect(authErr instanceof ProjectError).toBe(false);
    expect(projErr instanceof AuthenticationError).toBe(false);
    expect(uploadErr instanceof DownloadError).toBe(false);
    expect(downloadErr instanceof UploadError).toBe(false);
  });

  it("subclasses preserve message correctly", () => {
    expect(new AuthenticationError("bad key").message).toBe("bad key");
    expect(new ProjectError("project failed").message).toBe("project failed");
    expect(new UploadError("upload failed").message).toBe("upload failed");
    expect(new DownloadError("download failed").message).toBe("download failed");
  });

  it("instanceof works correctly in catch blocks", () => {
    const errors = [
      new AuthenticationError("a"),
      new ProjectError("p"),
      new UploadError("u"),
      new DownloadError("d"),
    ];

    for (const err of errors) {
      try {
        throw err;
      } catch (e) {
        expect(e instanceof ImagenError).toBe(true);
        expect(e instanceof Error).toBe(true);
      }
    }
  });
});
