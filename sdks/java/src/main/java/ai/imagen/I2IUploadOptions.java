package ai.imagen;

/**
 * Tunes {@code uploadI2IImages}. Files larger than {@code multipartThreshold} use
 * S3 multipart upload with {@code partSize}-byte parts. Values <= 0 use defaults
 * ({@link ImagenClient#I2I_DEFAULT_PART_SIZE}).
 */
public record I2IUploadOptions(
        boolean calculateMd5, long multipartThreshold, long partSize, int maxConcurrency, ProgressListener progress) {

    public static I2IUploadOptions defaults() {
        return new I2IUploadOptions(false, 0, 0, 0, null);
    }

    public static Builder builder() {
        return new Builder();
    }

    public static final class Builder {
        private boolean calculateMd5;
        private long multipartThreshold, partSize;
        private int maxConcurrency;
        private ProgressListener progress;

        public Builder calculateMd5(boolean v) { this.calculateMd5 = v; return this; }
        public Builder multipartThreshold(long v) { this.multipartThreshold = v; return this; }
        public Builder partSize(long v) { this.partSize = v; return this; }
        public Builder maxConcurrency(int v) { this.maxConcurrency = v; return this; }
        public Builder progress(ProgressListener v) { this.progress = v; return this; }

        public I2IUploadOptions build() {
            return new I2IUploadOptions(calculateMd5, multipartThreshold, partSize, maxConcurrency, progress);
        }
    }
}
