package com.imagenai;

/** Raised for a 400 response (invalid request). */
public class BadRequestException extends ApiException {
    public BadRequestException(String endpoint, String message, String body) {
        super(400, endpoint, message, body);
    }
}
