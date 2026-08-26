package com.imagenai;

/**
 * Applies a quick AI tool to one image. {@code toolId} is a tool's
 * {@code enhancementType} from {@code getAITools}. Leave {@code parentVersionId}
 * null to start from the base edited image.
 */
public record EnhanceRequest(String toolId, Object parentVersionId, ProjectSource projectSource) {

    public EnhanceRequest(String toolId, ProjectSource projectSource) {
        this(toolId, null, projectSource);
    }
}
