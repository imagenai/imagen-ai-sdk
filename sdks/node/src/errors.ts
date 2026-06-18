export class ImagenError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ImagenError";
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

export class AuthenticationError extends ImagenError {
  constructor(message: string) {
    super(message);
    this.name = "AuthenticationError";
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

export class ProjectError extends ImagenError {
  constructor(message: string) {
    super(message);
    this.name = "ProjectError";
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

export class UploadError extends ImagenError {
  constructor(message: string) {
    super(message);
    this.name = "UploadError";
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

export class DownloadError extends ImagenError {
  constructor(message: string) {
    super(message);
    this.name = "DownloadError";
    Object.setPrototypeOf(this, new.target.prototype);
  }
}
