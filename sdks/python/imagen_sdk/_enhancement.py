"""
AI enhancement / copilot / finalize mixin for ImagenClient.

Adds the per-image AI enhancement workflow:

- get_ai_tools: list AI quick tools available for a project
- enhance_image: apply an AI quick tool to an already-edited image
- apply_copilot: apply a natural-language instruction via the AI copilot
- reset_copilot: reset the copilot conversation history for an image
- finalize_project: generate final download URLs, upscaling enhanced images

Important behavior (verified against the API gateway):

- **The whole enhancement pipeline requires an EXPORTED project.** ``get_ai_tools``,
  ``enhance_image``, ``apply_copilot``, and ``finalize_project`` all reject projects
  that have not finished exporting with ``400 "Project has not been exported yet."``
  Run the standard edit-then-export flow first.
- **Realistic-only accounts.** Some accounts/instructions are restricted to "realistic"
  edits; generative requests (and copilot instructions classified as generative) are
  rejected downstream with ``400 "Only realistic editing requests are supported."``
  This gating is enforced by the editing service, not the gateway, so the SDK surfaces
  it as an ``ImagenError``.
"""

from __future__ import annotations

from ._core import _CoreClientMixin
from .enums import ProjectSource
from .models import (
    AIToolsResponse,
    CopilotRequest,
    DownloadLinksList,
    EnhanceImageRequest,
    EnhanceResult,
    FinalizeProjectRequest,
    ResetCopilotRequest,
)


class EnhancementMixin(_CoreClientMixin):
    """AI quick tools, copilot, and finalize operations."""

    async def get_ai_tools(
        self,
        project_uuid: str,
        project_source: ProjectSource = ProjectSource.REGULAR,
    ) -> AIToolsResponse:
        """
        List the AI enhancement (quick) tools available for a project.

        Args:
            project_uuid: UUID of the project.
            project_source: Project source (REGULAR or I2I, default REGULAR).

        Returns:
            AIToolsResponse whose ``prompts`` list contains the available tools. Use a
            tool's ``enhancement_type`` as the ``tool_id`` for ``enhance_image``.

        Note:
            The project must already be exported, otherwise the API responds with
            ``400 "Project has not been exported yet."``

        Raises:
            ImagenError: If the response cannot be parsed.
        """
        self._logger.debug(f"Listing AI tools for project {project_uuid} (source={project_source.value})")
        response_json = await self._make_request(
            "GET",
            f"/projects/{project_uuid}/ai-tools",
            params={"project_source": project_source.value},
        )
        return self._parse_model(response_json, AIToolsResponse, "AI tools response")

    async def enhance_image(
        self,
        project_uuid: str,
        filename: str,
        tool_id: str,
        parent_version_id: int | None = None,
        project_source: ProjectSource = ProjectSource.REGULAR,
    ) -> EnhanceResult:
        """
        Apply an AI quick tool to an already-edited image.

        Args:
            project_uuid: UUID of the project.
            filename: Name of the image to enhance.
            tool_id: Identifier of the AI quick tool (see ``get_ai_tools``).
            parent_version_id: Optional version ID to base this enhancement on.
            project_source: Project source (REGULAR or I2I, default REGULAR).

        Returns:
            EnhanceResult with the operation ``status``, ``version_id``, and
            ``enhanced_image_url``.

        Note:
            Requires an exported project. Non-realistic edits may be rejected on
            realistic-only accounts (see module docstring).

        Raises:
            ImagenError: If the response cannot be parsed.
        """
        request = EnhanceImageRequest(
            tool_id=tool_id,
            parent_version_id=parent_version_id,
            project_source=project_source,
        )
        self._logger.info(f"Enhancing {filename} in project {project_uuid} with tool {tool_id}")
        response_json = await self._make_request(
            "POST",
            f"/projects/{project_uuid}/images/{filename}/enhance",
            json=request.to_api_dict(),
        )
        return self._parse_model(response_json, EnhanceResult, "enhance image response")

    async def apply_copilot(
        self,
        project_uuid: str,
        filename: str,
        instruction: str,
        parent_version_id: int | None = None,
        project_source: ProjectSource = ProjectSource.REGULAR,
    ) -> EnhanceResult:
        """
        Apply a natural-language editing instruction to an image via the AI copilot.

        Args:
            project_uuid: UUID of the project.
            filename: Name of the image to edit.
            instruction: Natural-language instruction (1-255 characters).
            parent_version_id: Optional version ID to base this instruction on.
            project_source: Project source (REGULAR or I2I, default REGULAR).

        Returns:
            EnhanceResult with the operation ``status``, ``version_id``, and
            ``enhanced_image_url`` (same shape as ``enhance_image``).

        Note:
            Requires an exported project. Instructions classified as generative are
            rejected on realistic-only accounts (see module docstring).

        Raises:
            ImagenError: If the response cannot be parsed.
        """
        request = CopilotRequest(
            instruction=instruction,
            parent_version_id=parent_version_id,
            project_source=project_source,
        )
        self._logger.info(f"Applying copilot instruction to {filename} in project {project_uuid}")
        response_json = await self._make_request(
            "POST",
            f"/projects/{project_uuid}/images/{filename}/copilot",
            json=request.to_api_dict(),
        )
        return self._parse_model(response_json, EnhanceResult, "copilot response")

    async def reset_copilot(
        self,
        project_uuid: str,
        filename: str,
        project_source: ProjectSource = ProjectSource.REGULAR,
    ) -> None:
        """
        Reset the copilot conversation history for an image.

        Args:
            project_uuid: UUID of the project.
            filename: Name of the image whose copilot history should be reset.
            project_source: Project source (REGULAR or I2I, default REGULAR).
        """
        request = ResetCopilotRequest(project_source=project_source)
        self._logger.info(f"Resetting copilot history for {filename} in project {project_uuid}")
        await self._make_request(
            "DELETE",
            f"/projects/{project_uuid}/images/{filename}/copilot",
            json=request.to_api_dict(),
        )

    async def finalize_project(
        self,
        project_uuid: str,
        project_source: ProjectSource = ProjectSource.REGULAR,
    ) -> DownloadLinksList:
        """
        Generate final download URLs for all images, upscaling enhanced ones.

        Args:
            project_uuid: UUID of the project.
            project_source: Project source (REGULAR or I2I, default REGULAR).

        Returns:
            DownloadLinksList whose ``files_list`` holds the final per-file download links.

        Note:
            Requires an exported project, otherwise the API responds with
            ``400 "Project has not been exported yet."``

        Raises:
            ImagenError: If the response cannot be parsed.
        """
        request = FinalizeProjectRequest(project_source=project_source)
        self._logger.info(f"Finalizing project {project_uuid} (source={project_source.value})")
        response_json = await self._make_request(
            "POST",
            f"/projects/{project_uuid}/finalize",
            json=request.to_api_dict(),
        )
        return self._parse_model(response_json, DownloadLinksList, "finalize project response")
