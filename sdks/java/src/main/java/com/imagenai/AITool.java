package com.imagenai;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

/** Describes one available quick AI tool. */
@JsonIgnoreProperties(ignoreUnknown = true)
public record AITool(String enhancementType, String label, boolean enabledForBatch) {
}
