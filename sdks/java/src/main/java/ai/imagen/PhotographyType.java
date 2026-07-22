package ai.imagen;

import com.fasterxml.jackson.annotation.JsonValue;

/** Selects AI optimization tuned to a shoot type. */
public enum PhotographyType {
    NO_TYPE("NO_TYPE"),
    OTHER("OTHER"),
    PORTRAITS("PORTRAITS"),
    WEDDING("WEDDING"),
    REAL_ESTATE("REAL_ESTATE"),
    LANDSCAPE_NATURE("LANDSCAPE_NATURE"),
    EVENTS("EVENTS"),
    FAMILY_NEWBORN("FAMILY_NEWBORN"),
    BOUDOIR("BOUDOIR"),
    SPORTS("SPORTS"),
    SCHOOL("SCHOOL");

    private final String wire;

    PhotographyType(String wire) {
        this.wire = wire;
    }

    @JsonValue
    public String wire() {
        return wire;
    }
}
