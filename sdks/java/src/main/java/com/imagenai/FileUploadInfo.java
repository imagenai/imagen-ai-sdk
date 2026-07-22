package com.imagenai;

/** Names a file to be uploaded and, optionally, its base64 MD5. */
public record FileUploadInfo(String fileName, String md5) {
    public FileUploadInfo(String fileName) {
        this(fileName, null);
    }
}
