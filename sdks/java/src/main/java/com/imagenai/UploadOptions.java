package com.imagenai;

/** Tunes {@code uploadImages}. {@code maxConcurrency} <= 0 uses the client default. */
public record UploadOptions(boolean calculateMd5, int maxConcurrency, ProgressListener progress) {

    /** Default options: no MD5, client-default concurrency, no progress callback. */
    public static UploadOptions defaults() {
        return new UploadOptions(false, 0, null);
    }

    public static Builder builder() {
        return new Builder();
    }

    public static final class Builder {
        private boolean calculateMd5;
        private int maxConcurrency;
        private ProgressListener progress;

        public Builder calculateMd5(boolean v) { this.calculateMd5 = v; return this; }
        public Builder maxConcurrency(int v) { this.maxConcurrency = v; return this; }
        public Builder progress(ProgressListener v) { this.progress = v; return this; }

        public UploadOptions build() {
            return new UploadOptions(calculateMd5, maxConcurrency, progress);
        }
    }
}
