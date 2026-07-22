package ai.imagen;

import com.fasterxml.jackson.annotation.JsonValue;

/** Target aspect ratio when cropping is enabled. */
public enum CropAspectRatio {
    R2X3("2X3"),
    R4X5("4X5"),
    R5X7("5X7");

    private final String wire;

    CropAspectRatio(String wire) {
        this.wire = wire;
    }

    @JsonValue
    public String wire() {
        return wire;
    }
}
