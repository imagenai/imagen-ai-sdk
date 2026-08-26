package com.imagenai;

import java.time.Duration;
import java.util.function.Consumer;

/**
 * Tunes status polling. Null durations use the defaults (first wait 5s, capped at
 * 30s, exponential backoff factor 1.5).
 */
public record PollOptions(Duration interval, Duration maxInterval, Consumer<StatusDetails> progress) {

    public static PollOptions defaults() {
        return new PollOptions(null, null, null);
    }

    public static Builder builder() {
        return new Builder();
    }

    public static final class Builder {
        private Duration interval, maxInterval;
        private Consumer<StatusDetails> progress;

        public Builder interval(Duration v) { this.interval = v; return this; }
        public Builder maxInterval(Duration v) { this.maxInterval = v; return this; }
        public Builder progress(Consumer<StatusDetails> v) { this.progress = v; return this; }

        public PollOptions build() {
            return new PollOptions(interval, maxInterval, progress);
        }
    }
}
