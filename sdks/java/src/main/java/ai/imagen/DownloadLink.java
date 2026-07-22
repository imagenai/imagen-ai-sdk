package ai.imagen;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

/** Pairs a file name with its presigned GET URL. */
@JsonIgnoreProperties(ignoreUnknown = true)
public record DownloadLink(String fileName, String downloadLink) {
}
