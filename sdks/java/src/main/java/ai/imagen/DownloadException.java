package ai.imagen;

/** Raised when downloading bytes from storage fails. */
public class DownloadException extends ImagenException {
    public DownloadException(String message) {
        super(message);
    }

    public DownloadException(String message, Throwable cause) {
        super(message, cause);
    }
}
