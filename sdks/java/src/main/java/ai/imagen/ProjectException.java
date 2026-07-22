package ai.imagen;

/** Raised when a project-level operation fails (e.g. editing reached a Failed status). */
public class ProjectException extends ImagenException {
    public ProjectException(String message) {
        super(message);
    }
}
