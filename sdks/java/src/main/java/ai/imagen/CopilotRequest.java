package ai.imagen;

/**
 * Applies a natural-language instruction (1..255 chars) to one image. Leave
 * {@code parentVersionId} null to start from the base edited image.
 */
public record CopilotRequest(String instruction, Object parentVersionId, ProjectSource projectSource) {

    public CopilotRequest(String instruction, ProjectSource projectSource) {
        this(instruction, null, projectSource);
    }
}
