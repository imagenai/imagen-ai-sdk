package ai.imagen;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

/** One presigned part URL of a multipart upload. */
@JsonIgnoreProperties(ignoreUnknown = true)
public record MultipartUploadPart(int partNumber, String uploadUrl) {
}
