package com.imagenai;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

/** Paging metadata attached to a project listing. */
@JsonIgnoreProperties(ignoreUnknown = true)
public record Pagination(int total, int size, int page) {
}
