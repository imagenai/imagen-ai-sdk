package ai.imagen;

/** Tunes {@code downloadFiles}. {@code maxConcurrency} <= 0 uses the client default. */
public record DownloadOptions(int maxConcurrency, ProgressListener progress) {

    public static DownloadOptions defaults() {
        return new DownloadOptions(0, null);
    }

    public static Builder builder() {
        return new Builder();
    }

    public static final class Builder {
        private int maxConcurrency;
        private ProgressListener progress;

        public Builder maxConcurrency(int v) { this.maxConcurrency = v; return this; }
        public Builder progress(ProgressListener v) { this.progress = v; return this; }

        public DownloadOptions build() {
            return new DownloadOptions(maxConcurrency, progress);
        }
    }
}
