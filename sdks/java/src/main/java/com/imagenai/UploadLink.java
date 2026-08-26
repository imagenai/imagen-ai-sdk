package com.imagenai;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

/** Pairs a file name with its presigned PUT URL. */
@JsonIgnoreProperties(ignoreUnknown = true)
public record UploadLink(String fileName, String uploadLink) {
}
