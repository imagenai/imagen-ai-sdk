package ai.imagen;

import java.util.List;

/** Aggregates the results of an upload batch. {@code results} is sorted by file name. */
public record UploadSummary(int total, int successful, int failed, List<UploadResult> results) {
}
