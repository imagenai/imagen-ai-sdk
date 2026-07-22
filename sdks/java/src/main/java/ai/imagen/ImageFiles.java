package ai.imagen;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Base64;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;

/**
 * File helpers shared with the reference Python/Node/Go SDKs. The extension sets
 * are kept byte-for-byte identical so every client accepts and skips exactly the
 * same files.
 */
public final class ImageFiles {

    private ImageFiles() {
    }

    /** Supported RAW extensions (lowercase, with dot). */
    public static final Set<String> RAW_EXTENSIONS = Set.of(
            ".dng", ".nef", ".cr2", ".arw", ".nrw", ".crw", ".srf", ".sr2", ".orf", ".raw",
            ".rw2", ".raf", ".ptx", ".pef", ".rwl", ".srw", ".cr3", ".3fr", ".fff");

    /** Supported JPEG extensions (lowercase, with dot). */
    public static final Set<String> JPG_EXTENSIONS = Set.of(".jpg", ".jpeg");

    /** Reports whether the path has a supported RAW or JPG extension. */
    public static boolean supportedExtension(String path) {
        String ext = extension(path);
        return RAW_EXTENSIONS.contains(ext) || JPG_EXTENSIONS.contains(ext);
    }

    /** Returns "RAW", "JPG", or "" for an unsupported extension. */
    static String imageTypeForExt(String path) {
        String ext = extension(path);
        if (RAW_EXTENSIONS.contains(ext)) {
            return "RAW";
        }
        if (JPG_EXTENSIONS.contains(ext)) {
            return "JPG";
        }
        return "";
    }

    private static String extension(String path) {
        String name = baseName(path);
        int dot = name.lastIndexOf('.');
        return dot < 0 ? "" : name.substring(dot).toLowerCase(Locale.ROOT);
    }

    static String baseName(String path) {
        return Path.of(path).getFileName().toString();
    }

    /**
     * Errors if two paths share a base name. Uploads are keyed by base name, so
     * same-named files from different directories would collide.
     */
    static void checkUniqueBaseNames(List<String> paths) {
        Set<String> seen = new HashSet<>();
        for (String p : paths) {
            String b = baseName(p);
            if (!seen.add(b)) {
                throw new ImagenException("duplicate file name \"" + b
                        + "\": files are uploaded by base name, so inputs with the same name from "
                        + "different directories collide");
            }
        }
    }

    /**
     * Verifies that every file's image type matches the profile's image type (RAW
     * or JPG). Profiles with an empty image type accept any supported file.
     */
    public static void checkFilesMatchProfileType(Profile profile, List<String> paths) {
        if (profile.imageType() == null || profile.imageType().isEmpty()) {
            return;
        }
        String want = profile.imageType().toUpperCase(Locale.ROOT);
        StringBuilder mismatched = new StringBuilder();
        for (String p : paths) {
            if (!imageTypeForExt(p).equals(want)) {
                if (mismatched.length() > 0) {
                    mismatched.append(", ");
                }
                mismatched.append(baseName(p));
            }
        }
        if (mismatched.length() > 0) {
            throw new ImagenException("profile expects " + want
                    + " files but these do not match: " + mismatched);
        }
    }

    /** Streams the file and returns its base64-encoded MD5 digest. */
    static String md5Base64(Path path) throws IOException {
        MessageDigest md;
        try {
            md = MessageDigest.getInstance("MD5");
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("MD5 not available", e); // ponytail: MD5 is mandated by the JDK spec, unreachable
        }
        byte[] buf = new byte[1 << 16];
        try (InputStream in = Files.newInputStream(path)) {
            int n;
            while ((n = in.read(buf)) != -1) {
                md.update(buf, 0, n);
            }
        }
        return Base64.getEncoder().encodeToString(md.digest());
    }
}
