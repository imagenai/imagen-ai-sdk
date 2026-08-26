package com.imagenai;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;

/**
 * Package-private wire DTOs used only for deserialization. Public methods return
 * plain {@code List}/{@code Map}/String, so these envelopes never leak to callers.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
record CreateProjectResponse(String projectUuid) {
}

@JsonIgnoreProperties(ignoreUnknown = true)
record UploadLinksResponse(List<UploadLink> filesList) {
}

@JsonIgnoreProperties(ignoreUnknown = true)
record DownloadLinksList(List<DownloadLink> filesList) {
}

@JsonIgnoreProperties(ignoreUnknown = true)
record SingleUploadLink(String uploadLink) {
}

@JsonIgnoreProperties(ignoreUnknown = true)
record SingleDownloadLink(String downloadLink) {
}
