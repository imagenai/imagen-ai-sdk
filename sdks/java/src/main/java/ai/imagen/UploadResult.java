package ai.imagen;

/** Outcome of uploading a single file. {@code error} is null on success. */
public record UploadResult(String fileName, boolean success, String error) {

    static UploadResult ok(String fileName) {
        return new UploadResult(fileName, true, null);
    }

    static UploadResult failed(String fileName, String error) {
        return new UploadResult(fileName, false, error);
    }
}
