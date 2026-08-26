package com.imagenai;

import java.io.IOException;
import java.io.InputStream;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.channels.SeekableByteChannel;
import java.nio.ByteBuffer;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.atomic.AtomicReference;

/**
 * Concurrent S3 transfer engine and low-level PUT/GET primitives. Package-private;
 * {@link ImagenClient} orchestrates link fetching and multipart API calls, this
 * class moves the bytes.
 */
final class Transfers {

    private Transfers() {
    }

    /** Uploads valid files concurrently via single PUTs, bounded by {@code concurrency}. */
    static UploadSummary runUploads(HttpClient http, List<Path> paths, Map<String, String> links,
                                    Map<String, String> md5s, int concurrency, ProgressListener progress) {
        int total = paths.size();
        UploadResult[] results = new UploadResult[total];
        Progress reporter = new Progress(total, progress);
        ExecutorService pool = Executors.newFixedThreadPool(Math.max(1, concurrency));
        try {
            List<Future<?>> futures = new ArrayList<>(total);
            for (int i = 0; i < total; i++) {
                final int idx = i;
                final Path path = paths.get(i);
                final String name = ImageFiles.baseName(path.toString());
                final String link = links.get(name);
                futures.add(pool.submit(() -> {
                    if (link == null) {
                        results[idx] = UploadResult.failed(name, "no upload link returned for " + name);
                    } else {
                        try {
                            putFile(http, path, link, md5s.get(name));
                            results[idx] = UploadResult.ok(name);
                        } catch (Exception e) {
                            results[idx] = UploadResult.failed(name, "upload failed: " + e.getMessage());
                        }
                    }
                    reporter.step(name);
                }));
            }
            joinAll(futures);
        } finally {
            // shutdownNow (not shutdown) so an interrupt or a throwing progress
            // callback cancels queued work and interrupts running PUT/GETs, rather
            // than letting them run on after the method has returned/thrown. On the
            // normal path joinAll has already awaited every task, so this is a no-op.
            pool.shutdownNow();
        }
        return summarize(results);
    }

    /**
     * Downloads each link into {@code dir} concurrently. The first error is thrown
     * after all in-flight downloads settle; files that did succeed are written.
     */
    static List<String> download(HttpClient http, List<DownloadLink> links, Path dir, int concurrency,
                                 ProgressListener progress) {
        int total = links.size();
        String[] paths = new String[total];
        Throwable[] errs = new Throwable[total];
        Progress reporter = new Progress(total, progress);
        ExecutorService pool = Executors.newFixedThreadPool(Math.max(1, concurrency));
        try {
            List<Future<?>> futures = new ArrayList<>(total);
            for (int i = 0; i < total; i++) {
                final int idx = i;
                final DownloadLink link = links.get(i);
                futures.add(pool.submit(() -> {
                    Path dest = dir.resolve(ImageFiles.baseName(link.fileName()));
                    try {
                        getToFile(http, link.downloadLink(), dest);
                        paths[idx] = dest.toString();
                    } catch (Exception e) {
                        errs[idx] = e;
                    }
                    reporter.step(link.fileName());
                }));
            }
            joinAll(futures);
        } finally {
            // shutdownNow (not shutdown) so an interrupt or a throwing progress
            // callback cancels queued work and interrupts running PUT/GETs, rather
            // than letting them run on after the method has returned/thrown. On the
            // normal path joinAll has already awaited every task, so this is a no-op.
            pool.shutdownNow();
        }

        List<String> written = new ArrayList<>();
        for (String p : paths) {
            if (p != null) {
                written.add(p);
            }
        }
        for (int i = 0; i < total; i++) {
            if (errs[i] != null) {
                throw new DownloadException("download failed: " + links.get(i).fileName()
                        + ": " + errs[i].getMessage(), errs[i]);
            }
        }
        return written;
    }

    /**
     * Validates the server-supplied part set before any bytes are uploaded: the
     * response must carry exactly {@code expectedCount} parts numbered
     * {@code 1..expectedCount} (unique, in range) each with a non-blank URL.
     * Offsets are derived from {@code partNumber}, so a malformed set would upload
     * wrong byte ranges or omit data and then finalize corrupt content on
     * {@code /complete}. Throws {@link IOException} on any violation.
     */
    static void validateParts(List<MultipartUploadPart> parts, int expectedCount) throws IOException {
        if (parts == null || parts.size() != expectedCount) {
            throw new IOException("multipart response returned " + (parts == null ? 0 : parts.size())
                    + " parts, expected " + expectedCount);
        }
        boolean[] seen = new boolean[expectedCount + 1];
        for (MultipartUploadPart p : parts) {
            int n = p.partNumber();
            if (n < 1 || n > expectedCount) {
                throw new IOException("multipart part number " + n + " out of range 1.." + expectedCount);
            }
            if (seen[n]) {
                throw new IOException("multipart response has duplicate part number " + n);
            }
            seen[n] = true;
            if (p.uploadUrl() == null || p.uploadUrl().isBlank()) {
                throw new IOException("multipart part " + n + " has no upload URL");
            }
        }
    }

    /**
     * Uploads each multipart part concurrently. Chunks are read inside the worker
     * so peak memory is bounded to {@code concurrency * partSize}. Throws on the
     * first part failure.
     */
    static void uploadParts(HttpClient http, Path path, long partSize, List<MultipartUploadPart> parts,
                            int concurrency) throws IOException {
        long fileSize = Files.size(path);
        AtomicReference<Throwable> firstError = new AtomicReference<>();
        ExecutorService pool = Executors.newFixedThreadPool(Math.max(1, concurrency));
        try {
            List<Future<?>> futures = new ArrayList<>(parts.size());
            for (MultipartUploadPart part : parts) {
                futures.add(pool.submit(() -> {
                    try {
                        long offset = (long) (part.partNumber() - 1) * partSize;
                        int expected = (int) Math.min(partSize, fileSize - offset);
                        byte[] chunk = readChunk(path, offset, expected);
                        putBytes(http, part.uploadUrl(), chunk);
                    } catch (Throwable t) {
                        firstError.compareAndSet(null, new IOException(
                                "part " + part.partNumber() + ": " + t.getMessage(), t));
                    }
                }));
            }
            joinAll(futures);
        } finally {
            // shutdownNow (not shutdown) so an interrupt or a throwing progress
            // callback cancels queued work and interrupts running PUT/GETs, rather
            // than letting them run on after the method has returned/thrown. On the
            // normal path joinAll has already awaited every task, so this is a no-op.
            pool.shutdownNow();
        }
        Throwable err = firstError.get();
        if (err != null) {
            throw (err instanceof IOException io) ? io : new IOException(err);
        }
    }

    // --- primitives ---------------------------------------------------------

    /** Streams a file's bytes to a presigned URL (bounded memory regardless of size). */
    static void putFile(HttpClient http, Path path, String uploadUrl, String md5) throws IOException, InterruptedException {
        HttpRequest.Builder b = HttpRequest.newBuilder(URI.create(uploadUrl))
                .PUT(HttpRequest.BodyPublishers.ofFile(path));
        if (md5 != null && !md5.isEmpty()) {
            b.header("Content-MD5", md5);
        }
        send(http, b.build());
    }

    /** PUTs an in-memory buffer to a presigned URL (used for multipart parts). */
    static void putBytes(HttpClient http, String uploadUrl, byte[] data) throws IOException, InterruptedException {
        send(http, HttpRequest.newBuilder(URI.create(uploadUrl))
                .PUT(HttpRequest.BodyPublishers.ofByteArray(data)).build());
    }

    private static void send(HttpClient http, HttpRequest req) throws IOException, InterruptedException {
        HttpResponse<byte[]> resp = http.send(req, HttpResponse.BodyHandlers.ofByteArray());
        if (resp.statusCode() < 200 || resp.statusCode() >= 300) {
            throw new IOException("S3 responded " + resp.statusCode() + ": " + new String(resp.body()));
        }
    }

    /** GETs a URL and writes the body to dest via a temp file + atomic rename. */
    static void getToFile(HttpClient http, String downloadUrl, Path dest) throws IOException, InterruptedException {
        HttpResponse<InputStream> resp = http.send(
                HttpRequest.newBuilder(URI.create(downloadUrl)).GET().build(),
                HttpResponse.BodyHandlers.ofInputStream());
        if (resp.statusCode() < 200 || resp.statusCode() >= 300) {
            try (InputStream in = resp.body()) {
                throw new IOException("storage responded " + resp.statusCode() + ": " + new String(in.readAllBytes()));
            }
        }
        Path parent = dest.toAbsolutePath().getParent();
        Path tmp = Files.createTempFile(parent, ".imagen-", ".part");
        try (InputStream in = resp.body()) {
            Files.copy(in, tmp, StandardCopyOption.REPLACE_EXISTING);
            Files.move(tmp, dest, StandardCopyOption.REPLACE_EXISTING);
        } catch (IOException e) {
            Files.deleteIfExists(tmp);
            throw e;
        }
    }

    private static byte[] readChunk(Path path, long offset, int length) throws IOException {
        byte[] buf = new byte[length];
        ByteBuffer bb = ByteBuffer.wrap(buf);
        try (SeekableByteChannel ch = Files.newByteChannel(path)) {
            ch.position(offset);
            while (bb.hasRemaining()) {
                if (ch.read(bb) < 0) {
                    // File shrank under us; a short part would complete with corrupt data.
                    throw new IOException("unexpected EOF reading " + length + " bytes at offset " + offset);
                }
            }
        }
        return buf;
    }

    // --- helpers ------------------------------------------------------------

    private static void joinAll(List<Future<?>> futures) {
        for (Future<?> f : futures) {
            try {
                f.get();
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                throw new ImagenException("interrupted while transferring", e);
            } catch (ExecutionException e) {
                // Task bodies swallow their own exceptions into result/error slots;
                // reaching here means an unexpected failure worth surfacing.
                throw new ImagenException("transfer task failed", e.getCause());
            }
        }
    }

    private static UploadSummary summarize(UploadResult[] results) {
        List<UploadResult> list = new ArrayList<>(List.of(results));
        list.sort(Comparator.comparing(UploadResult::fileName));
        int ok = 0;
        for (UploadResult r : list) {
            if (r.success()) {
                ok++;
            }
        }
        return new UploadSummary(list.size(), ok, list.size() - ok, List.copyOf(list));
    }

    /** Serial, monotonic progress reporter (matches the other SDKs' ordering). */
    private static final class Progress {
        private final int total;
        private final ProgressListener listener;
        private int done;

        Progress(int total, ProgressListener listener) {
            this.total = total;
            this.listener = listener;
        }

        synchronized void step(String fileName) {
            done++;
            if (listener != null) {
                listener.onProgress(done, total, fileName);
            }
        }
    }
}
