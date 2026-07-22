package com.imagenai;

import java.util.List;

/** Artifacts produced by {@code quickEdit}. */
public record QuickEditResult(
        String projectUuid,
        UploadSummary uploadSummary,
        List<DownloadLink> editLinks,
        List<DownloadLink> exportLinks,
        List<String> downloadedFiles,
        List<String> exportedFiles) {
}
