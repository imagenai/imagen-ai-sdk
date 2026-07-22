package ai.imagen;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;

/** Lists the AI tools available for a project (open shape). */
@JsonIgnoreProperties(ignoreUnknown = true)
public record AIToolsResponse(List<AITool> prompts) {
}
