class ImagenError(Exception):
    """Base exception for Imagen SDK errors."""

    pass


class AuthenticationError(ImagenError):
    """Raised when authentication fails."""

    pass


class ProjectError(ImagenError):
    """Raised when project operations fail."""

    pass


class UploadError(ImagenError):
    """Raised when upload operations fail."""

    pass


class DownloadError(ImagenError):
    """Raised when download operations fail."""

    pass
