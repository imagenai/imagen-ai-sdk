package com.imagenai;

/** Optional toggles for an image-to-image editing job. Build with {@link #builder()}. */
public record I2IEditOptions(
        Boolean hdrMerge,
        Boolean skyReplacement,
        Integer skyReplacementTemplateId,
        Boolean perspectiveCorrection,
        String callbackUrl) {

    public static Builder builder() {
        return new Builder();
    }

    public static final class Builder {
        private Boolean hdrMerge, skyReplacement, perspectiveCorrection;
        private Integer skyReplacementTemplateId;
        private String callbackUrl;

        public Builder hdrMerge(boolean v) { this.hdrMerge = v; return this; }
        public Builder skyReplacement(boolean v) { this.skyReplacement = v; return this; }
        public Builder skyReplacementTemplateId(int v) { this.skyReplacementTemplateId = v; return this; }
        public Builder perspectiveCorrection(boolean v) { this.perspectiveCorrection = v; return this; }
        public Builder callbackUrl(String v) { this.callbackUrl = v; return this; }

        public I2IEditOptions build() {
            return new I2IEditOptions(hdrMerge, skyReplacement, skyReplacementTemplateId,
                    perspectiveCorrection, callbackUrl);
        }
    }
}
