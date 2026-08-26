package com.imagenai;

/** Raised for a 401 response (missing or invalid API key). */
public class AuthenticationException extends ApiException {
    public AuthenticationException(String endpoint, String message, String body) {
        super(401, endpoint, message, body);
    }
}
