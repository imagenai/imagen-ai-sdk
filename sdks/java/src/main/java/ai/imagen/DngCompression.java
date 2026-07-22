package ai.imagen;

import com.fasterxml.jackson.annotation.JsonValue;

/** Controls compression of HDR-merged DNG output. */
public enum DngCompression {
    LOSSY("LOSSY"),
    LOSSLESS("LOSSLESS");

    private final String wire;

    DngCompression(String wire) {
        this.wire = wire;
    }

    @JsonValue
    public String wire() {
        return wire;
    }
}
