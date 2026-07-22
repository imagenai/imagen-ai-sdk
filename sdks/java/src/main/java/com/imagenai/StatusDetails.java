package com.imagenai;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

/**
 * Payload of an edit/export status poll. Terminal values of {@code status} are
 * {@link #COMPLETED} and {@link #FAILED}; any other value means keep polling.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public record StatusDetails(String status, double progress, String details) {
    public static final String COMPLETED = "Completed";
    public static final String FAILED = "Failed";

    /** Reports whether the status will not change with further polling. */
    public boolean isTerminal() {
        return COMPLETED.equals(status) || FAILED.equals(status);
    }
}
