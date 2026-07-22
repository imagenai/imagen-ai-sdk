package ai.imagen;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

/**
 * One project in a listing (open shape; extra fields ignored). For I2I projects,
 * {@code status} carries the editing state (Pending, In Progress, Completed,
 * Failed) that {@code waitForI2ICompletion} polls.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public record ProjectListItem(String projectUuid, String name, String status, int numberOfImages) {
}
