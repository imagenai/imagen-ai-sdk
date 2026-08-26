package com.imagenai;

import java.util.List;

/**
 * Configures the one-call {@code quickEdit} workflow. {@code profileKey} and
 * {@code imagePaths} are required; build with {@link #builder()}.
 */
public record QuickEditParams(
        String projectName,
        int profileKey,
        List<String> imagePaths,
        PhotographyType photographyType,
        EditOptions editOptions,
        boolean export,
        boolean download,
        String downloadDir,
        String exportDownloadDir,
        UploadOptions upload,
        PollOptions poll) {

    public static Builder builder() {
        return new Builder();
    }

    public static final class Builder {
        private String projectName;
        private int profileKey;
        private List<String> imagePaths = List.of();
        private PhotographyType photographyType;
        private EditOptions editOptions = EditOptions.none();
        private boolean export, download;
        private String downloadDir, exportDownloadDir;
        private UploadOptions upload;
        private PollOptions poll;

        public Builder projectName(String v) { this.projectName = v; return this; }
        public Builder profileKey(int v) { this.profileKey = v; return this; }
        public Builder imagePaths(List<String> v) { this.imagePaths = v; return this; }
        public Builder photographyType(PhotographyType v) { this.photographyType = v; return this; }
        public Builder editOptions(EditOptions v) { this.editOptions = v; return this; }
        public Builder export(boolean v) { this.export = v; return this; }
        public Builder download(boolean v) { this.download = v; return this; }
        public Builder downloadDir(String v) { this.downloadDir = v; return this; }
        public Builder exportDownloadDir(String v) { this.exportDownloadDir = v; return this; }
        public Builder upload(UploadOptions v) { this.upload = v; return this; }
        public Builder poll(PollOptions v) { this.poll = v; return this; }

        public QuickEditParams build() {
            return new QuickEditParams(projectName, profileKey, imagePaths, photographyType,
                    editOptions, export, download, downloadDir, exportDownloadDir, upload, poll);
        }
    }
}
