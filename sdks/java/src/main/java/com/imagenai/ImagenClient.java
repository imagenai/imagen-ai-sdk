package com.imagenai;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.json.JsonMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.io.IOException;
import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Consumer;
import java.util.function.Supplier;

/**
 * Thread-safe client for the Imagen AI photo-editing API. Build one with
 * {@link #builder(String)} and reuse it. Every method blocks until the HTTP call
 * completes and throws an {@link ApiException} on a non-2xx response; concurrent
 * upload/download is handled internally with a bounded thread pool.
 *
 * <pre>{@code
 * ImagenClient client = ImagenClient.builder("YOUR_API_KEY").build();
 * String uuid = client.createProject("My Photos");
 * client.uploadImages(uuid, List.of("photo1.dng"), null);
 * client.editAndWait(uuid, new EditRequest(profileKey), null);
 * List<DownloadLink> links = client.getDownloadLinks(uuid);
 * client.downloadFiles(links, "out", null);
 * }</pre>
 */
public final class ImagenClient {

    /** Production Imagen AI API root. */
    public static final String DEFAULT_BASE_URL = "https://api.imagen-ai.com/v1";
    /** Default bound on concurrent S3 uploads/downloads. */
    public static final int DEFAULT_MAX_CONCURRENCY = 10;
    /** Default multipart part size and threshold (S3 requires parts >= 5 MB except the last). */
    public static final long I2I_DEFAULT_PART_SIZE = 64L << 20;
    private static final int MAX_S3_PARTS = 10_000;
    /** Default per-request timeout for API (JSON) calls; transfers are not capped this way. */
    private static final Duration DEFAULT_REQUEST_TIMEOUT = Duration.ofSeconds(60);

    private static final Duration DEFAULT_POLL_INTERVAL = Duration.ofSeconds(5);
    private static final Duration DEFAULT_MAX_POLL_INTERVAL = Duration.ofSeconds(30);
    private static final double POLL_BACKOFF = 1.5;

    private static final ObjectMapper MAPPER = JsonMapper.builder()
            .propertyNamingStrategy(PropertyNamingStrategies.SNAKE_CASE)
            .serializationInclusion(JsonInclude.Include.NON_NULL)
            .configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false)
            .build();

    private final String apiKey;
    private final String baseUrl;
    private final int maxConcurrency;
    private final Duration requestTimeout;
    private final HttpClient http;

    private ImagenClient(Builder b) {
        this.apiKey = b.apiKey;
        this.baseUrl = b.baseUrl;
        this.maxConcurrency = b.maxConcurrency;
        this.requestTimeout = b.requestTimeout;
        this.http = b.httpClient != null ? b.httpClient
                : HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(30)).build();
    }

    public static Builder builder(String apiKey) {
        return new Builder(apiKey);
    }

    public static final class Builder {
        private final String apiKey;
        private String baseUrl = DEFAULT_BASE_URL;
        private int maxConcurrency = DEFAULT_MAX_CONCURRENCY;
        private Duration requestTimeout = DEFAULT_REQUEST_TIMEOUT;
        private HttpClient httpClient;

        private Builder(String apiKey) {
            if (apiKey == null || apiKey.isBlank()) {
                throw new ImagenException("api key must not be empty");
            }
            this.apiKey = apiKey.strip();
        }

        /** Overrides the API root (staging or a mock server). Trailing slash is trimmed. */
        public Builder baseUrl(String url) {
            this.baseUrl = url.replaceAll("/+$", "");
            return this;
        }

        /** Caps concurrent uploads and downloads (>= 1). */
        public Builder maxConcurrency(int n) {
            if (n >= 1) {
                this.maxConcurrency = n;
            }
            return this;
        }

        /**
         * Per-request timeout for API (JSON) calls (default 60s). Applies to
         * {@code createProject}, editing, status polls, etc. — not to S3
         * uploads/downloads, whose duration scales with file size. A null value
         * disables the API timeout.
         */
        public Builder requestTimeout(Duration timeout) {
            this.requestTimeout = timeout;
            return this;
        }

        /** Supplies a custom {@link HttpClient} (timeouts, proxy, executor). */
        public Builder httpClient(HttpClient client) {
            this.httpClient = client;
            return this;
        }

        public ImagenClient build() {
            return new ImagenClient(this);
        }
    }

    // === Projects ===========================================================

    /** Creates a regular project and returns its UUID. Empty name = server-generated. */
    public String createProject(String name) {
        return createProject("/projects/", name);
    }

    private String createProject(String path, String name) {
        Object body = (name != null && !name.isEmpty()) ? Map.of("name", name) : null;
        CreateProjectResponse r = request("POST", path, null, body, null, CreateProjectResponse.class);
        if (r == null || r.projectUuid() == null || r.projectUuid().isEmpty()) {
            throw new ImagenException("create project response missing project_uuid");
        }
        return r.projectUuid();
    }

    /** Returns a page of regular projects. Pass null for defaults. */
    public ProjectListResponse listProjects(ListProjectsOptions opts) {
        Map<String, String> q = new LinkedHashMap<>();
        if (opts != null) {
            putIf(q, "size", opts.size());
            putIf(q, "page", opts.page());
            putIf(q, "client_type", opts.clientType());
            putIf(q, "is_archived", opts.isArchived());
            putIf(q, "get_thumbnail", opts.getThumbnail());
        }
        return request("GET", "/projects", q, null, null, ProjectListResponse.class);
    }

    /** Fetches a single project by UUID. */
    public ProjectListItem getProject(String projectUuid, boolean getThumbnail) {
        Map<String, String> q = new LinkedHashMap<>();
        if (getThumbnail) {
            q.put("get_thumbnail", "true");
        }
        return request("GET", "/projects/" + seg(projectUuid), q, null, null, ProjectListItem.class);
    }

    /** Resolves a project name to its UUID (tolerates a bare string, {project_uuid}, or {uuid}). */
    public String getProjectUuidByName(String name) {
        JsonNode n = request("GET", "/projects/" + seg(name) + "/uuid", null, null, null);
        if (n.isTextual() && !n.asText().isEmpty()) {
            return n.asText();
        }
        String uuid = firstText(n, "project_uuid", "uuid");
        if (uuid == null) {
            throw new ImagenException("uuid response for \"" + name + "\" contained no uuid");
        }
        return uuid;
    }

    /** Requests presigned PUT URLs and returns a map of file name to upload URL. */
    public Map<String, String> getUploadLinks(String projectUuid, List<FileUploadInfo> files) {
        UploadLinksResponse r = request("POST",
                "/projects/" + seg(projectUuid) + "/get_temporary_upload_links",
                null, Map.of("files_list", files), null, UploadLinksResponse.class);
        return uploadLinkMap(r);
    }

    // === Editing / export ===================================================

    /** Triggers a regular editing job (validates options; sends the empty Content-Type /edit requires). */
    public void startEditing(String projectUuid, EditRequest edit) {
        edit.options().validate();
        ObjectNode node = MAPPER.valueToTree(edit.options());
        node.put("profile_key", edit.profileKey());
        if (edit.photographyType() != null) {
            node.put("photography_type", edit.photographyType().wire());
        }
        request("POST", "/projects/" + seg(projectUuid) + "/edit", null, node, "");
    }

    /** Polls the editing status for a project. */
    public StatusDetails editStatus(String projectUuid) {
        return request("GET", "/projects/" + seg(projectUuid) + "/edit/status", null, null, null, StatusDetails.class);
    }

    /** Returns the XMP download links produced by editing. */
    public List<DownloadLink> getDownloadLinks(String projectUuid) {
        return downloadLinks("/projects/" + seg(projectUuid) + "/edit/get_temporary_download_links");
    }

    /** Starts exporting edited images to JPEG. */
    public void startExport(String projectUuid) {
        request("POST", "/projects/" + seg(projectUuid) + "/export", null, null, null);
    }

    /** Polls the export status for a project. */
    public StatusDetails exportStatus(String projectUuid) {
        return request("GET", "/projects/" + seg(projectUuid) + "/export/status", null, null, null, StatusDetails.class);
    }

    /** Returns the JPEG export download links. */
    public List<DownloadLink> getExportDownloadLinks(String projectUuid) {
        return downloadLinks("/projects/" + seg(projectUuid) + "/export/get_temporary_download_links");
    }

    /** Returns a per-image presigned PUT URL for export. */
    public String getExportUploadLink(String projectUuid, String fileName) {
        return request("GET", "/projects/" + seg(projectUuid) + "/export/get_upload_link",
                Map.of("file_name", fileName), null, null, SingleUploadLink.class).uploadLink();
    }

    /** Returns a per-image presigned GET URL for export. */
    public String getExportDownloadLink(String projectUuid, String fileName) {
        return request("GET", "/projects/" + seg(projectUuid) + "/export/get_download_link",
                Map.of("file_name", fileName), null, null, SingleDownloadLink.class).downloadLink();
    }

    // === Discovery ==========================================================

    /** Lists the editing profiles available to the account. */
    public List<Profile> getProfiles() {
        JsonNode n = request("GET", "/profiles", null, null, null);
        JsonNode arr = n.isArray() ? n : n.path("profiles");
        return toList(arr, Profile.class);
    }

    /** Returns the single profile matching profileKey, or throws if none matches. */
    public Profile getProfile(int profileKey) {
        for (Profile p : getProfiles()) {
            if (p.profileKey() == profileKey) {
                return p;
            }
        }
        throw new ImagenException("no profile with key " + profileKey);
    }

    /** Lists sky-replacement templates (tolerates a bare list or {templates:[...]}). */
    public List<SkyTemplate> getSkyReplacementTemplates() {
        JsonNode n = request("GET", "/projects/sky_replacement/templates", null, null, null);
        JsonNode arr = n.isArray() ? n : n.path("templates");
        return toList(arr, SkyTemplate.class);
    }

    /** Lists the available quick AI tools for a project. */
    public AIToolsResponse getAITools(String projectUuid, ProjectSource source) {
        return request("GET", "/projects/" + seg(projectUuid) + "/ai-tools",
                Map.of("project_source", source.wire()), null, null, AIToolsResponse.class);
    }

    // === Enhance / copilot / finalize =======================================

    /** Applies a quick AI tool to one image and returns the result. */
    public EnhanceResult enhanceImage(String projectUuid, String fileName, EnhanceRequest req) {
        return request("POST", "/projects/" + seg(projectUuid) + "/images/" + seg(fileName) + "/enhance",
                null, req, null, EnhanceResult.class);
    }

    /** Applies a natural-language instruction to one image. */
    public EnhanceResult copilot(String projectUuid, String fileName, CopilotRequest req) {
        return request("POST", "/projects/" + seg(projectUuid) + "/images/" + seg(fileName) + "/copilot",
                null, req, null, EnhanceResult.class);
    }

    /** Clears the copilot conversation history for one image. */
    public void resetCopilot(String projectUuid, String fileName, ProjectSource source) {
        request("DELETE", "/projects/" + seg(projectUuid) + "/images/" + seg(fileName) + "/copilot",
                null, Map.of("project_source", source.wire()), null);
    }

    /** Generates final download URLs and upscales enhanced images. */
    public List<DownloadLink> finalizeProject(String projectUuid, ProjectSource source) {
        DownloadLinksList r = request("POST", "/projects/" + seg(projectUuid) + "/finalize",
                null, Map.of("project_source", source.wire()), null, DownloadLinksList.class);
        return listOrEmpty(r);
    }

    // === I2I ================================================================

    /** Creates an image-to-image project and returns its UUID. */
    public String createI2IProject(String name) {
        return createProject("/i2i/projects/", name);
    }

    /** Returns a page of I2I projects (only size, page and isArchived are honoured). */
    public ProjectListResponse listI2IProjects(ListProjectsOptions opts) {
        Map<String, String> q = new LinkedHashMap<>();
        if (opts != null) {
            putIf(q, "size", opts.size());
            putIf(q, "page", opts.page());
            putIf(q, "is_archived", opts.isArchived());
        }
        return request("GET", "/i2i/projects", q, null, null, ProjectListResponse.class);
    }

    /** Reports whether an I2I project name is available (a 2xx with no flag is treated as valid). */
    public boolean isValidI2IName(String name) {
        JsonNode n = request("GET", "/i2i/projects/is_valid_name", Map.of("name", name), null, null);
        if (n.isBoolean()) {
            return n.asBoolean();
        }
        for (String key : new String[]{"is_valid", "valid"}) {
            if (n.has(key)) {
                return n.get(key).asBoolean();
            }
        }
        return true;
    }

    /** Fetches a single I2I project by UUID. */
    public ProjectListItem getI2IProject(String projectUuid, boolean getThumbnail) {
        Map<String, String> q = new LinkedHashMap<>();
        if (getThumbnail) {
            q.put("get_thumbnail", "true");
        }
        return request("GET", "/i2i/projects/" + seg(projectUuid), q, null, null, ProjectListItem.class);
    }

    /** Requests batched presigned PUT URLs for small files. */
    public Map<String, String> getI2IUploadLinks(String projectUuid, List<FileUploadInfo> files) {
        UploadLinksResponse r = request("POST",
                "/i2i/projects/" + seg(projectUuid) + "/get_temporary_upload_links",
                null, bodyMap("files_list", files, "client_type", "API"), null, UploadLinksResponse.class);
        return uploadLinkMap(r);
    }

    /** Returns a single presigned PUT URL (advanced use). */
    public String getI2IUploadLink(String projectUuid, String fileName) {
        return request("GET", "/i2i/projects/" + seg(projectUuid) + "/get_upload_link",
                Map.of("file_name", fileName), null, null, SingleUploadLink.class).uploadLink();
    }

    /** Starts an S3 multipart upload and returns per-part presigned URLs (1..10000 parts). */
    public MultipartUploadResponse createMultipartUpload(String projectUuid, String fileName, int partCount) {
        return request("POST", "/i2i/projects/" + seg(projectUuid) + "/multipart_uploads",
                null, bodyMap("file_name", fileName, "part_count", partCount), null, MultipartUploadResponse.class);
    }

    /** Finalizes a multipart upload. */
    public void completeMultipartUpload(String projectUuid, String uploadId, String fileName) {
        request("POST", "/i2i/projects/" + seg(projectUuid) + "/multipart_uploads/" + seg(uploadId) + "/complete",
                null, Map.of("file_name", fileName), null);
    }

    /** Cancels a multipart upload identified by its storage key. */
    public void abortMultipartUpload(String projectUuid, String uploadId, String key) {
        request("DELETE", "/i2i/projects/" + seg(projectUuid) + "/multipart_uploads/" + seg(uploadId),
                null, Map.of("key", key), null);
    }

    /** Triggers I2I editing and returns immediately (detect completion via callback or waitForI2ICompletion). */
    public void startI2IEditing(String projectUuid, I2IEditOptions opts) {
        request("POST", "/i2i/projects/" + seg(projectUuid) + "/edit", null, opts, null);
    }

    /** Returns all I2I result download links. */
    public List<DownloadLink> getI2IDownloadLinks(String projectUuid) {
        return downloadLinks("/i2i/projects/" + seg(projectUuid) + "/get_temporary_download_links");
    }

    /** Returns a single I2I result download link. */
    public String getI2IDownloadLink(String projectUuid, String fileName) {
        return request("GET", "/i2i/projects/" + seg(projectUuid) + "/get_download_link",
                Map.of("file_name", fileName), null, null, SingleDownloadLink.class).downloadLink();
    }

    // === Upload / download engines ==========================================

    /**
     * Uploads local files to presigned S3 URLs concurrently. Unsupported or
     * unreadable paths are silently skipped; duplicate base names are rejected.
     * Per-file failures are recorded in the summary rather than aborting the batch.
     */
    public UploadSummary uploadImages(String projectUuid, List<String> paths, UploadOptions opts) {
        UploadOptions o = opts != null ? opts : UploadOptions.defaults();
        Prepared prep = prepare(paths, o.calculateMd5());
        if (prep.infos.isEmpty()) {
            throw new UploadException("no valid image files to upload");
        }
        ImageFiles.checkUniqueBaseNames(prep.validPaths());
        Map<String, String> links = getUploadLinks(projectUuid, prep.infos);
        int concurrency = o.maxConcurrency() >= 1 ? o.maxConcurrency() : maxConcurrency;
        return Transfers.runUploads(http, prep.paths, links, prep.md5ByName(), concurrency, o.progress());
    }

    /** Downloads each link into dir (created if needed) concurrently; returns the paths written. */
    public List<String> downloadFiles(List<DownloadLink> links, String dir, DownloadOptions opts) {
        DownloadOptions o = opts != null ? opts : DownloadOptions.defaults();
        if (links == null || links.isEmpty()) {
            throw new DownloadException("no download links provided");
        }
        Path dirPath = Path.of(dir);
        try {
            Files.createDirectories(dirPath);
        } catch (IOException e) {
            throw new DownloadException("creating download dir: " + e.getMessage(), e);
        }
        int concurrency = o.maxConcurrency() >= 1 ? o.maxConcurrency() : maxConcurrency;
        return Transfers.download(http, links, dirPath, concurrency, o.progress());
    }

    /**
     * Uploads files to an I2I project, routing each by size: files at or below the
     * threshold are batched into single PUTs, larger files use S3 multipart upload.
     */
    public UploadSummary uploadI2IImages(String projectUuid, List<String> paths, I2IUploadOptions opts) {
        I2IUploadOptions o = opts != null ? opts : I2IUploadOptions.defaults();
        long threshold = o.multipartThreshold() > 0 ? o.multipartThreshold() : I2I_DEFAULT_PART_SIZE;
        long partSize = o.partSize() > 0 ? o.partSize() : I2I_DEFAULT_PART_SIZE;
        int concurrency = o.maxConcurrency() >= 1 ? o.maxConcurrency() : maxConcurrency;

        List<Path> small = new ArrayList<>();
        List<Path> large = new ArrayList<>();
        for (String p : paths) {
            if (!ImageFiles.supportedExtension(p)) {
                continue;
            }
            Path path = Path.of(p);
            if (!Files.isRegularFile(path)) {
                continue;
            }
            long size;
            try {
                size = Files.size(path);
            } catch (IOException e) {
                continue;
            }
            (size > threshold ? large : small).add(path);
        }
        if (small.isEmpty() && large.isEmpty()) {
            throw new UploadException("no valid image files to upload");
        }
        List<String> allNames = new ArrayList<>();
        small.forEach(p -> allNames.add(p.toString()));
        large.forEach(p -> allNames.add(p.toString()));
        ImageFiles.checkUniqueBaseNames(allNames);

        List<UploadResult> results = new ArrayList<>();
        if (!small.isEmpty()) {
            Prepared prep = prepare(small.stream().map(Path::toString).toList(), o.calculateMd5());
            Map<String, String> links = getI2IUploadLinks(projectUuid, prep.infos);
            results.addAll(Transfers.runUploads(http, prep.paths, links, prep.md5ByName(), concurrency, o.progress()).results());
        }
        for (Path path : large) {
            String name = ImageFiles.baseName(path.toString());
            try {
                uploadFileMultipart(projectUuid, path, partSize, concurrency);
                results.add(UploadResult.ok(name));
            } catch (Exception e) {
                results.add(UploadResult.failed(name, "upload failed: " + e.getMessage()));
            }
        }
        results.sort((a, b) -> a.fileName().compareTo(b.fileName()));
        int ok = (int) results.stream().filter(UploadResult::success).count();
        return new UploadSummary(results.size(), ok, results.size() - ok, List.copyOf(results));
    }

    private void uploadFileMultipart(String projectUuid, Path path, long partSize, int concurrency) throws IOException {
        long fileSize = Files.size(path);
        // S3 allows at most 10000 parts; grow partSize (ceil-division) to stay within that.
        if (ceilDiv(fileSize, partSize) > MAX_S3_PARTS) {
            partSize = Math.max(partSize, ceilDiv(fileSize, MAX_S3_PARTS));
        }
        int partCount = (int) Math.max(1, ceilDiv(fileSize, partSize));
        String name = ImageFiles.baseName(path.toString());

        MultipartUploadResponse mp = createMultipartUpload(projectUuid, name, partCount);
        try {
            Transfers.validateParts(mp.parts(), partCount);
            Transfers.uploadParts(http, path, partSize, mp.parts(), concurrency);
            completeMultipartUpload(projectUuid, mp.uploadId(), name);
        } catch (RuntimeException | IOException e) {
            abortBestEffort(projectUuid, mp.uploadId(), mp.key());
            throw e;
        }
    }

    private void abortBestEffort(String projectUuid, String uploadId, String key) {
        try {
            abortMultipartUpload(projectUuid, uploadId, key);
        } catch (RuntimeException ignored) {
            // The caller's original error is what matters.
        }
    }

    // === Polling ============================================================

    /** Polls the edit status until it reaches a terminal state. */
    public StatusDetails waitForEditing(String projectUuid, PollOptions opts) {
        return pollStatus(() -> editStatus(projectUuid), opts);
    }

    /** Polls the export status until it reaches a terminal state. */
    public StatusDetails waitForExport(String projectUuid, PollOptions opts) {
        return pollStatus(() -> exportStatus(projectUuid), opts);
    }

    /** Starts editing and blocks until it completes or fails. */
    public void editAndWait(String projectUuid, EditRequest edit, PollOptions opts) {
        startEditing(projectUuid, edit);
        waitForEditing(projectUuid, opts);
    }

    /** Starts an export and blocks until it completes or fails. */
    public void exportAndWait(String projectUuid, PollOptions opts) {
        startExport(projectUuid);
        waitForExport(projectUuid, opts);
    }

    /**
     * Polls the I2I project's status until terminal, then returns the result
     * download links. I2I has no dedicated status endpoint; status lives on the
     * project object. A Failed status throws {@link ProjectException}.
     */
    public List<DownloadLink> waitForI2ICompletion(String projectUuid, PollOptions opts) {
        Poll p = Poll.from(opts);
        while (true) {
            ProjectListItem project = getI2IProject(projectUuid, false);
            if (StatusDetails.COMPLETED.equals(project.status())) {
                return getI2IDownloadLinks(projectUuid);
            }
            if (StatusDetails.FAILED.equals(project.status())) {
                throw new ProjectException("I2I editing failed for project " + projectUuid);
            }
            if (p.progress != null) {
                p.progress.accept(new StatusDetails(project.status(), 0, null));
            }
            p.sleep();
        }
    }

    private StatusDetails pollStatus(Supplier<StatusDetails> fetch, PollOptions opts) {
        Poll p = Poll.from(opts);
        while (true) {
            StatusDetails status = fetch.get();
            if (StatusDetails.FAILED.equals(status.status())) {
                throw new ProjectException("editing failed: " + status.details());
            }
            if (status.isTerminal()) {
                return status;
            }
            if (p.progress != null) {
                p.progress.accept(status);
            }
            p.sleep();
        }
    }

    /** Mutable backoff state for a single poll loop. */
    private static final class Poll {
        long intervalMillis;
        final long maxMillis;
        final Consumer<StatusDetails> progress;

        private Poll(long intervalMillis, long maxMillis, Consumer<StatusDetails> progress) {
            this.intervalMillis = intervalMillis;
            this.maxMillis = maxMillis;
            this.progress = progress;
        }

        private static boolean isPositive(Duration d) {
            return d != null && !d.isZero() && !d.isNegative();
        }

        static Poll from(PollOptions opts) {
            long interval = DEFAULT_POLL_INTERVAL.toMillis();
            long max = DEFAULT_MAX_POLL_INTERVAL.toMillis();
            Consumer<StatusDetails> progress = null;
            if (opts != null) {
                // Only positive durations override the defaults (matches Go); a zero
                // interval would busy-loop and a negative one would throw in sleep().
                if (isPositive(opts.interval())) {
                    interval = opts.interval().toMillis();
                }
                if (isPositive(opts.maxInterval())) {
                    max = opts.maxInterval().toMillis();
                }
                progress = opts.progress();
            }
            return new Poll(interval, max, progress);
        }

        void sleep() {
            try {
                Thread.sleep(intervalMillis);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                throw new ImagenException("interrupted while polling", e);
            }
            intervalMillis = Math.min((long) (intervalMillis * POLL_BACKOFF), maxMillis);
        }
    }

    // === QuickEdit ==========================================================

    /**
     * Runs the full workflow: create project, upload images, edit and wait, then
     * optionally export and download. Throws on the first failure; use the
     * step-by-step methods when you need partial-progress recovery.
     */
    public QuickEditResult quickEdit(QuickEditParams p) {
        if (p.profileKey() == 0) {
            throw new ImagenException("quickEdit requires a profileKey");
        }
        if (p.imagePaths() == null || p.imagePaths().isEmpty()) {
            throw new ImagenException("quickEdit requires at least one image path");
        }
        if (p.download() && (p.downloadDir() == null || p.downloadDir().isEmpty())) {
            throw new ImagenException("quickEdit download requires a downloadDir");
        }

        // Fail fast on profile/file-type mismatch before creating server-side state.
        Profile profile = getProfile(p.profileKey());
        ImageFiles.checkFilesMatchProfileType(profile, p.imagePaths());

        String uuid = createProject(p.projectName());
        UploadSummary summary = uploadImages(uuid, p.imagePaths(), p.upload());
        if (summary.successful() == 0) {
            throw new UploadException("quickEdit: no images uploaded successfully");
        }

        EditRequest edit = new EditRequest(p.profileKey(), p.photographyType(),
                p.editOptions() != null ? p.editOptions() : EditOptions.none());
        editAndWait(uuid, edit, p.poll());

        List<DownloadLink> editLinks = getDownloadLinks(uuid);
        List<DownloadLink> exportLinks = List.of();
        List<String> downloadedFiles = List.of();
        List<String> exportedFiles = List.of();

        if (p.export()) {
            exportAndWait(uuid, p.poll());
            exportLinks = getExportDownloadLinks(uuid);
        }
        if (p.download()) {
            downloadedFiles = downloadFiles(editLinks, p.downloadDir(), null);
            if (p.export()) {
                String exportDir = (p.exportDownloadDir() != null && !p.exportDownloadDir().isEmpty())
                        ? p.exportDownloadDir()
                        : Path.of(p.downloadDir(), "exported").toString();
                exportedFiles = downloadFiles(exportLinks, exportDir, null);
            }
        }
        return new QuickEditResult(uuid, summary, editLinks, exportLinks, downloadedFiles, exportedFiles);
    }

    // === HTTP core ==========================================================

    /** Executes a request and returns the envelope-unwrapped body as a JsonNode. */
    private JsonNode request(String method, String path, Map<String, String> query, Object body, String contentType) {
        String url = baseUrl + path + queryString(query);
        byte[] bodyBytes = body != null ? writeJson(body) : null;
        HttpRequest.Builder b = HttpRequest.newBuilder(URI.create(url)).header("x-api-key", apiKey);
        if (requestTimeout != null) {
            b.timeout(requestTimeout);
        }
        b.method(method, bodyBytes != null
                ? HttpRequest.BodyPublishers.ofByteArray(bodyBytes)
                : HttpRequest.BodyPublishers.noBody());
        if (contentType != null) {
            b.header("Content-Type", contentType);
        } else if (bodyBytes != null) {
            b.header("Content-Type", "application/json");
        }

        HttpResponse<byte[]> resp;
        try {
            resp = http.send(b.build(), HttpResponse.BodyHandlers.ofByteArray());
        } catch (IOException e) {
            throw new ImagenException(method + " " + path + ": " + e.getMessage(), e);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new ImagenException(method + " " + path + " interrupted", e);
        }

        byte[] respBody = resp.body();
        if (resp.statusCode() < 200 || resp.statusCode() >= 300) {
            String raw = new String(respBody, StandardCharsets.UTF_8);
            throw ApiException.forStatus(resp.statusCode(), path, parseErrorMessage(raw), raw);
        }
        return unwrapEnvelope(respBody);
    }

    private <T> T request(String method, String path, Map<String, String> query, Object body,
                          String contentType, Class<T> type) {
        JsonNode node = request(method, path, query, body, contentType);
        if (node == null || node.isMissingNode() || node.isNull()) {
            return null;
        }
        try {
            return MAPPER.treeToValue(node, type);
        } catch (IOException e) {
            throw new ImagenException("decoding " + path + " response: " + e.getMessage(), e);
        }
    }

    private List<DownloadLink> downloadLinks(String path) {
        return listOrEmpty(request("GET", path, null, null, null, DownloadLinksList.class));
    }

    private byte[] writeJson(Object body) {
        try {
            return MAPPER.writeValueAsBytes(body);
        } catch (IOException e) {
            throw new ImagenException("encoding request body: " + e.getMessage(), e);
        }
    }

    /** If the body is an object whose only key is "data", returns that value; else the body. */
    private JsonNode unwrapEnvelope(byte[] body) {
        if (body == null || body.length == 0) {
            return MAPPER.missingNode();
        }
        JsonNode node;
        try {
            node = MAPPER.readTree(body);
        } catch (IOException e) {
            throw new ImagenException("decoding response: " + e.getMessage(), e);
        }
        if (node != null && node.isObject() && node.size() == 1 && node.has("data")) {
            return node.get("data");
        }
        return node != null ? node : MAPPER.missingNode();
    }

    private String parseErrorMessage(String body) {
        try {
            JsonNode n = MAPPER.readTree(body);
            String msg = n.path("error").path("message").asText(null);
            if (msg != null && !msg.isEmpty()) {
                return msg;
            }
            String detail = n.path("detail").asText(null);
            if (detail != null && !detail.isEmpty()) {
                return detail;
            }
        } catch (IOException ignored) {
            // Non-JSON error body; fall through to empty message.
        }
        return "";
    }

    private <T> List<T> toList(JsonNode arr, Class<T> type) {
        List<T> out = new ArrayList<>();
        if (arr != null && arr.isArray()) {
            for (JsonNode el : arr) {
                try {
                    out.add(MAPPER.treeToValue(el, type));
                } catch (IOException e) {
                    throw new ImagenException("decoding " + type.getSimpleName() + ": " + e.getMessage(), e);
                }
            }
        }
        return out;
    }

    // === small helpers ======================================================

    private static List<DownloadLink> listOrEmpty(DownloadLinksList r) {
        return (r == null || r.filesList() == null) ? List.of() : r.filesList();
    }

    private static Map<String, String> uploadLinkMap(UploadLinksResponse r) {
        Map<String, String> m = new LinkedHashMap<>();
        if (r != null && r.filesList() != null) {
            for (UploadLink l : r.filesList()) {
                m.put(l.fileName(), l.uploadLink());
            }
        }
        return m;
    }

    private static String firstText(JsonNode node, String... keys) {
        for (String key : keys) {
            String v = node.path(key).asText(null);
            if (v != null && !v.isEmpty()) {
                return v;
            }
        }
        return null;
    }

    private static void putIf(Map<String, String> q, String key, Object value) {
        if (value != null) {
            q.put(key, String.valueOf(value));
        }
    }

    private static Map<String, Object> bodyMap(String k1, Object v1, String k2, Object v2) {
        Map<String, Object> m = new HashMap<>();
        m.put(k1, v1);
        m.put(k2, v2);
        return m;
    }

    private static String queryString(Map<String, String> query) {
        if (query == null || query.isEmpty()) {
            return "";
        }
        StringBuilder sb = new StringBuilder("?");
        for (Map.Entry<String, String> e : query.entrySet()) {
            if (sb.length() > 1) {
                sb.append('&');
            }
            sb.append(enc(e.getKey())).append('=').append(enc(e.getValue()));
        }
        return sb.toString();
    }

    private static String enc(String s) {
        return URLEncoder.encode(s, StandardCharsets.UTF_8);
    }

    /** URL-encodes a single path segment (spaces as %20, not '+'). */
    private static String seg(String s) {
        return URLEncoder.encode(s, StandardCharsets.UTF_8).replace("+", "%20");
    }

    private static long ceilDiv(long a, long b) {
        // Overflow-safe: a + b - 1 would wrap for a near Long.MAX_VALUE.
        return b <= 0 ? a : a / b + (a % b == 0 ? 0 : 1);
    }

    // === upload preparation =================================================

    private record Prepared(List<FileUploadInfo> infos, List<Path> paths) {
        List<String> validPaths() {
            return paths.stream().map(Path::toString).toList();
        }

        Map<String, String> md5ByName() {
            Map<String, String> m = new LinkedHashMap<>();
            for (FileUploadInfo info : infos) {
                if (info.md5() != null && !info.md5().isEmpty()) {
                    m.put(info.fileName(), info.md5());
                }
            }
            return m;
        }
    }

    /** Filters to supported, regular files and builds the upload-info list (optionally with MD5). */
    private static Prepared prepare(List<String> paths, boolean calcMd5) {
        List<FileUploadInfo> infos = new ArrayList<>();
        List<Path> valid = new ArrayList<>();
        for (String p : paths) {
            if (!ImageFiles.supportedExtension(p)) {
                continue;
            }
            Path path = Path.of(p);
            if (!Files.isRegularFile(path)) {
                continue;
            }
            String md5 = null;
            if (calcMd5) {
                try {
                    md5 = ImageFiles.md5Base64(path);
                } catch (IOException e) {
                    throw new UploadException("computing md5 for " + p + ": " + e.getMessage(), e);
                }
            }
            infos.add(new FileUploadInfo(ImageFiles.baseName(p), md5));
            valid.add(path);
        }
        return new Prepared(infos, valid);
    }
}
