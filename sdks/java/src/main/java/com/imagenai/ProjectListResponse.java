package com.imagenai;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;

/** A page of projects. */
@JsonIgnoreProperties(ignoreUnknown = true)
public record ProjectListResponse(List<ProjectListItem> projects, Pagination pagination) {
}
