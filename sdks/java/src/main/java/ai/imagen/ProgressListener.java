package ai.imagen;

/**
 * Callback invoked after each file during an upload or download. Called serially
 * (never from two threads at once) in monotonic {@code done} order.
 */
@FunctionalInterface
public interface ProgressListener {
    void onProgress(int done, int total, String fileName);
}
