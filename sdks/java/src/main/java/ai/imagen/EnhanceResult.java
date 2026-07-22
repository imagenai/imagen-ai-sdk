package ai.imagen;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

/**
 * Result of an enhance or copilot call. {@code versionId} is intentionally
 * untyped ({@link Object}) because the server declares it as an open optional field.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public record EnhanceResult(String status, Object versionId, String enhancedImageUrl) {
}
