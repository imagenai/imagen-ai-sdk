package ai.imagen;

/** An editing profile (a saved look) available to the account. {@code imageType} is "RAW" or "JPG". */
public record Profile(String imageType, int profileKey, String profileName, String profileType) {
}
