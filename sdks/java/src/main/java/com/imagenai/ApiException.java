package com.imagenai;

/**
 * Raised for any non-2xx HTTP response from the Imagen API. Carries the parsed
 * error message when the server provides one, plus the raw body for debugging.
 * {@link #forStatus} maps 401/400 to the specific subclasses.
 */
public class ApiException extends ImagenException {
    private final int statusCode;
    private final String endpoint;
    private final String body;

    public ApiException(int statusCode, String endpoint, String message, String body) {
        super(String.format("Imagen API error %d on %s: %s", statusCode, endpoint,
                message != null && !message.isEmpty() ? message : body));
        this.statusCode = statusCode;
        this.endpoint = endpoint;
        this.body = body;
    }

    /** Builds the most specific ApiException subtype for the given status code. */
    public static ApiException forStatus(int statusCode, String endpoint, String message, String body) {
        return switch (statusCode) {
            case 401 -> new AuthenticationException(endpoint, message, body);
            case 400 -> new BadRequestException(endpoint, message, body);
            default -> new ApiException(statusCode, endpoint, message, body);
        };
    }

    public int statusCode() {
        return statusCode;
    }

    public String endpoint() {
        return endpoint;
    }

    public String body() {
        return body;
    }
}
