package com.imagenai;

/** Optional query parameters for listing projects. Null fields are omitted. */
public record ListProjectsOptions(
        Integer size, Integer page, String clientType, Boolean isArchived, Boolean getThumbnail) {

    public static Builder builder() {
        return new Builder();
    }

    public static final class Builder {
        private Integer size, page;
        private String clientType;
        private Boolean isArchived, getThumbnail;

        public Builder size(int v) { this.size = v; return this; }
        public Builder page(int v) { this.page = v; return this; }
        public Builder clientType(String v) { this.clientType = v; return this; }
        public Builder isArchived(boolean v) { this.isArchived = v; return this; }
        public Builder getThumbnail(boolean v) { this.getThumbnail = v; return this; }

        public ListProjectsOptions build() {
            return new ListProjectsOptions(size, page, clientType, isArchived, getThumbnail);
        }
    }
}
