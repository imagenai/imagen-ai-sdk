package com.imagenai;

/** Base type for all errors raised by the SDK. Unchecked to keep call sites clean. */
public class ImagenException extends RuntimeException {
    public ImagenException(String message) {
        super(message);
    }

    public ImagenException(String message, Throwable cause) {
        super(message, cause);
    }
}
