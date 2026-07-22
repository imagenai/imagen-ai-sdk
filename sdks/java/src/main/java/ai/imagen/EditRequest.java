package ai.imagen;

/**
 * Body for starting a regular editing job. {@code profileKey} is required;
 * {@code photographyType} and {@code options} are optional. The client flattens
 * {@code options} into the same JSON object when sending.
 */
public record EditRequest(int profileKey, PhotographyType photographyType, EditOptions options) {

    public EditRequest(int profileKey) {
        this(profileKey, null, EditOptions.none());
    }

    public EditRequest(int profileKey, EditOptions options) {
        this(profileKey, null, options);
    }

    /** Canonical constructor normalizes a null {@code options} to the all-unset value. */
    public EditRequest {
        if (options == null) {
            options = EditOptions.none();
        }
    }
}
