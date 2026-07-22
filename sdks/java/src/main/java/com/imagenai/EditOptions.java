package com.imagenai;

/**
 * Optional toggles for a regular editing job. All fields are nullable so an unset
 * option is omitted from the request (the client serializes with non-null
 * inclusion) rather than sent as {@code false}. Build with {@link #builder()}.
 *
 * <p>Mutual-exclusivity rules (checked by {@link #validate()}, also called
 * automatically by {@code startEditing}):
 * <ul>
 *   <li>at most one crop mode: {@code crop}, {@code headshotCrop}, {@code portraitCrop}</li>
 *   <li>at most one straightening mode: {@code straighten}, {@code perspectiveCorrection}</li>
 * </ul>
 */
public record EditOptions(
        Boolean crop,
        Boolean straighten,
        Boolean hdrMerge,
        Boolean portraitCrop,
        Boolean smoothSkin,
        Boolean subjectMask,
        Boolean headshotCrop,
        Boolean perspectiveCorrection,
        Boolean skyReplacement,
        Integer skyReplacementTemplateId,
        Boolean windowPull,
        CropAspectRatio cropAspectRatio,
        String callbackUrl,
        DngCompression hdrOutputCompression) {

    /** All-unset options. */
    public static EditOptions none() {
        return builder().build();
    }

    public static Builder builder() {
        return new Builder();
    }

    private static boolean isTrue(Boolean b) {
        return Boolean.TRUE.equals(b);
    }

    /** Enforces the crop/straighten mutual-exclusivity rules. */
    public void validate() {
        int crops = (isTrue(crop) ? 1 : 0) + (isTrue(headshotCrop) ? 1 : 0) + (isTrue(portraitCrop) ? 1 : 0);
        if (crops > 1) {
            throw new ImagenException("at most one crop mode may be set (crop, headshot_crop, portrait_crop)");
        }
        int straightens = (isTrue(straighten) ? 1 : 0) + (isTrue(perspectiveCorrection) ? 1 : 0);
        if (straightens > 1) {
            throw new ImagenException("at most one straightening mode may be set (straighten, perspective_correction)");
        }
    }

    public static final class Builder {
        private Boolean crop, straighten, hdrMerge, portraitCrop, smoothSkin, subjectMask,
                headshotCrop, perspectiveCorrection, skyReplacement, windowPull;
        private Integer skyReplacementTemplateId;
        private CropAspectRatio cropAspectRatio;
        private String callbackUrl;
        private DngCompression hdrOutputCompression;

        public Builder crop(boolean v) { this.crop = v; return this; }
        public Builder straighten(boolean v) { this.straighten = v; return this; }
        public Builder hdrMerge(boolean v) { this.hdrMerge = v; return this; }
        public Builder portraitCrop(boolean v) { this.portraitCrop = v; return this; }
        public Builder smoothSkin(boolean v) { this.smoothSkin = v; return this; }
        public Builder subjectMask(boolean v) { this.subjectMask = v; return this; }
        public Builder headshotCrop(boolean v) { this.headshotCrop = v; return this; }
        public Builder perspectiveCorrection(boolean v) { this.perspectiveCorrection = v; return this; }
        public Builder skyReplacement(boolean v) { this.skyReplacement = v; return this; }
        public Builder skyReplacementTemplateId(int v) { this.skyReplacementTemplateId = v; return this; }
        public Builder windowPull(boolean v) { this.windowPull = v; return this; }
        public Builder cropAspectRatio(CropAspectRatio v) { this.cropAspectRatio = v; return this; }
        public Builder callbackUrl(String v) { this.callbackUrl = v; return this; }
        public Builder hdrOutputCompression(DngCompression v) { this.hdrOutputCompression = v; return this; }

        public EditOptions build() {
            return new EditOptions(crop, straighten, hdrMerge, portraitCrop, smoothSkin, subjectMask,
                    headshotCrop, perspectiveCorrection, skyReplacement, skyReplacementTemplateId,
                    windowPull, cropAspectRatio, callbackUrl, hdrOutputCompression);
        }
    }
}
