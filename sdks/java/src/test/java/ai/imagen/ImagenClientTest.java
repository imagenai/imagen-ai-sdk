package ai.imagen;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.concurrent.atomic.AtomicReference;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** Unit + HTTP-integration tests using the JDK's built-in HttpServer (no external deps). */
class ImagenClientTest {

    private HttpServer server;
    private ImagenClient client;
    private final AtomicReference<String> lastEditBody = new AtomicReference<>();
    private final AtomicReference<String> lastEditContentType = new AtomicReference<>();

    @BeforeEach
    void setUp() throws IOException {
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/", this::dispatch);
        server.start();
        int port = server.getAddress().getPort();
        client = ImagenClient.builder("test-key").baseUrl("http://127.0.0.1:" + port).build();
    }

    @AfterEach
    void tearDown() {
        server.stop(0);
    }

    private void dispatch(HttpExchange ex) throws IOException {
        String path = ex.getRequestURI().getPath();
        String method = ex.getRequestMethod();
        String body;
        if (path.contains("bad400")) {
            byte[] err = "{\"error\":{\"message\":\"boom\"}}".getBytes(StandardCharsets.UTF_8);
            ex.sendResponseHeaders(400, err.length);
            ex.getResponseBody().write(err);
            ex.close();
            return;
        } else if ("POST".equals(method) && "/projects/".equals(path)) {
            // Envelope: single "data" key must be unwrapped.
            body = "{\"data\":{\"project_uuid\":\"abc123\"}}";
        } else if ("POST".equals(method) && path.endsWith("/edit")) {
            lastEditContentType.set(ex.getRequestHeaders().getFirst("Content-Type"));
            lastEditBody.set(new String(ex.getRequestBody().readAllBytes(), StandardCharsets.UTF_8));
            body = "{\"message\":\"ok\"}";
        } else if ("GET".equals(method) && path.endsWith("/edit/status")) {
            body = "{\"status\":\"Completed\",\"progress\":100}";
        } else if ("GET".equals(method) && "/profiles".equals(path)) {
            // Bare-list shape (no envelope, no wrapper).
            body = "[{\"profile_key\":7,\"image_type\":\"RAW\",\"profile_name\":\"Warm\"}]";
        } else {
            body = "{}";
        }
        byte[] out = body.getBytes(StandardCharsets.UTF_8);
        ex.sendResponseHeaders(200, out.length);
        ex.getResponseBody().write(out);
        ex.close();
    }

    @Test
    void createProjectUnwrapsDataEnvelope() {
        assertEquals("abc123", client.createProject("My Photos"));
    }

    @Test
    void getProfilesParsesBareList() {
        List<Profile> profiles = client.getProfiles();
        assertEquals(1, profiles.size());
        assertEquals(7, profiles.get(0).profileKey());
        assertEquals("RAW", profiles.get(0).imageType());
    }

    @Test
    void startEditingFlattensOptionsAsSnakeCaseAndDropsNulls() {
        EditRequest req = new EditRequest(7, PhotographyType.WEDDING,
                EditOptions.builder().crop(true).cropAspectRatio(CropAspectRatio.R4X5).build());
        client.startEditing("abc123", req);

        String sent = lastEditBody.get();
        assertTrue(sent.contains("\"profile_key\":7"), sent);
        assertTrue(sent.contains("\"crop\":true"), sent);
        assertTrue(sent.contains("\"crop_aspect_ratio\":\"4X5\""), sent);
        assertTrue(sent.contains("\"photography_type\":\"WEDDING\""), sent);
        // Unset options must be omitted, not sent as false.
        assertFalse(sent.contains("straighten"), sent);
        assertFalse(sent.contains("smooth_skin"), sent);
        // /edit must be sent with an explicit empty Content-Type (server quirk),
        // not application/json and not absent.
        assertEquals("", lastEditContentType.get());
    }

    @Test
    void non2xxMapsToTypedExceptionWithParsedMessage() {
        BadRequestException ex = assertThrows(BadRequestException.class, () -> client.editStatus("bad400"));
        assertEquals(400, ex.statusCode());
        assertTrue(ex.getMessage().contains("boom"), ex.getMessage());
    }

    @Test
    void validatePartsRejectsMalformedServerMetadata() throws Exception {
        // Happy path: exactly N parts, contiguous 1..N, non-blank URLs.
        Transfers.validateParts(List.of(
                new MultipartUploadPart(1, "u1"), new MultipartUploadPart(2, "u2")), 2);
        // Wrong count.
        assertThrows(IOException.class, () ->
                Transfers.validateParts(List.of(new MultipartUploadPart(1, "u1")), 2));
        // Duplicate part number.
        assertThrows(IOException.class, () -> Transfers.validateParts(List.of(
                new MultipartUploadPart(1, "u1"), new MultipartUploadPart(1, "u2")), 2));
        // Out-of-range part number.
        assertThrows(IOException.class, () ->
                Transfers.validateParts(List.of(new MultipartUploadPart(3, "u")), 1));
        // Blank URL.
        assertThrows(IOException.class, () ->
                Transfers.validateParts(List.of(new MultipartUploadPart(1, "  ")), 1));
    }

    @Test
    void editStatusParsesTerminalStatus() {
        StatusDetails s = client.editStatus("abc123");
        assertEquals("Completed", s.status());
        assertTrue(s.isTerminal());
    }

    @Test
    void editOptionsValidateRejectsMultipleCropModes() {
        EditOptions bad = EditOptions.builder().crop(true).headshotCrop(true).build();
        assertThrows(ImagenException.class, bad::validate);
    }

    @Test
    void editOptionsValidateRejectsMultipleStraightenModes() {
        EditOptions bad = EditOptions.builder().straighten(true).perspectiveCorrection(true).build();
        assertThrows(ImagenException.class, bad::validate);
    }

    @Test
    void supportedExtensionMatchesReferenceSets() {
        assertTrue(ImageFiles.supportedExtension("/tmp/a.CR3"));
        assertTrue(ImageFiles.supportedExtension("photo.jpeg"));
        assertFalse(ImageFiles.supportedExtension("notes.txt"));
    }

    @Test
    void checkFilesMatchProfileTypeRejectsMismatch() {
        Profile rawProfile = new Profile("RAW", 1, "P", "type");
        assertThrows(ImagenException.class,
                () -> ImageFiles.checkFilesMatchProfileType(rawProfile, List.of("a.jpg")));
        // A RAW file matches; empty-type profile accepts anything.
        ImageFiles.checkFilesMatchProfileType(rawProfile, List.of("a.dng"));
        ImageFiles.checkFilesMatchProfileType(new Profile("", 1, "P", "t"), List.of("a.jpg"));
    }

    @Test
    void emptyApiKeyRejected() {
        assertThrows(ImagenException.class, () -> ImagenClient.builder("  ").build());
    }
}
