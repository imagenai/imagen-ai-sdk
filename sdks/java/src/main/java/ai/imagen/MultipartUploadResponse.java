package ai.imagen;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;

/** The handle and per-part URLs for an S3 multipart upload. */
@JsonIgnoreProperties(ignoreUnknown = true)
public record MultipartUploadResponse(String uploadId, String key, List<MultipartUploadPart> parts) {
}
