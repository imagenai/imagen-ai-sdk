package com.imagenai;

import com.fasterxml.jackson.annotation.JsonValue;

/**
 * Identifies which project family an enhancement/copilot call targets. Required
 * in enhance, copilot, reset and finalize request bodies.
 */
public enum ProjectSource {
    REGULAR("REGULAR"),
    I2I("I2I");

    private final String wire;

    ProjectSource(String wire) {
        this.wire = wire;
    }

    @JsonValue
    public String wire() {
        return wire;
    }
}
