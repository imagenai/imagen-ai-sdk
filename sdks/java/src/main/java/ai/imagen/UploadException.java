package ai.imagen;

/** Raised when uploading bytes to storage fails outright (not per-file, which is reported in the summary). */
public class UploadException extends ImagenException {
    public UploadException(String message) {
        super(message);
    }

    public UploadException(String message, Throwable cause) {
        super(message, cause);
    }
}
