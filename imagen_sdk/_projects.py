"""
Project management mixin for ImagenClient.

Adds read/listing endpoints and sky-replacement template discovery that were not
part of the original SDK surface:

- list_projects / get_project / get_project_uuid
- get_sky_replacement_templates
- get_export_upload_link / get_export_download_link
"""

from __future__ import annotations

from ._core import _CoreClientMixin
from .enums import ClientType
from .exceptions import ImagenError, ProjectError
from .models import (
    FileDownloadInfo,
    ProjectListItem,
    ProjectListResponse,
    SkyTemplate,
    SkyTemplatesResponse,
    TemporaryFileUploadData,
)


class ProjectManagementMixin(_CoreClientMixin):
    """Project listing/retrieval, sky templates, and per-image export links."""

    async def list_projects(
        self,
        size: int = 20,
        page: int = 0,
        client_type: ClientType = ClientType.API,
        is_archived: bool | None = False,
        get_thumbnail: bool = True,
    ) -> ProjectListResponse:
        """
        List projects in your account with pagination.

        Args:
            size: Page size (1-100, default 20).
            page: Zero-based page index (default 0).
            client_type: Client type filter (default API).
            is_archived: Filter by archived state, or None for all (default False).
            get_thumbnail: Whether to include thumbnail URLs (default True).

        Returns:
            ProjectListResponse with the page of projects and pagination metadata.
            Ordering is defined by the API, not the SDK; in practice projects come
            back newest-first, so page 0 holds your most recently created projects
            and higher pages walk back in time.

        Raises:
            ProjectError: If the response cannot be parsed.
            AuthenticationError: If the API key is invalid.
        """
        params: dict[str, object] = {
            "size": size,
            "page": page,
            "client_type": client_type.value,
            "get_thumbnail": get_thumbnail,
        }
        if is_archived is not None:
            params["is_archived"] = is_archived

        self._logger.debug(f"Listing projects (page={page}, size={size})")
        response_json = await self._make_request("GET", "/projects", params=params)
        return self._parse_model(response_json, ProjectListResponse, "project list response", ProjectError)

    async def get_project(self, project_uuid: str, get_thumbnail: bool = True) -> ProjectListItem:
        """
        Get a single project by its UUID.

        Args:
            project_uuid: UUID of the project.
            get_thumbnail: Whether to include the thumbnail URL (default True).

        Returns:
            ProjectListItem describing the project.

        Raises:
            ProjectError: If the response cannot be parsed.
        """
        self._logger.debug(f"Getting project {project_uuid}")
        response_json = await self._make_request("GET", f"/projects/{project_uuid}", params={"get_thumbnail": get_thumbnail})
        return self._parse_model(response_json, ProjectListItem, "project response", ProjectError)

    async def get_project_uuid(self, project_name: str) -> str:
        """
        Resolve a project name to its UUID.

        Args:
            project_name: The (unique) project name.

        Returns:
            The project's UUID.

        Raises:
            ProjectError: If the project cannot be found or the UUID cannot be extracted.
        """
        self._logger.debug(f"Resolving UUID for project name: {project_name}")
        response_json = await self._make_request("GET", f"/projects/{project_name}/uuid")
        data = self._unwrap(response_json)

        # The response schema is unspecified server-side; accept the common shapes.
        if isinstance(data, str):
            return data
        if isinstance(data, dict):
            for key in ("project_uuid", "uuid"):
                value = data.get(key)
                if isinstance(value, str) and value:
                    return value
        raise ProjectError(f"Could not extract project UUID for name '{project_name}' from response: {data!r}")

    async def get_sky_replacement_templates(self) -> list[SkyTemplate]:
        """
        List available sky replacement templates.

        Use the returned ``id`` values for ``EditOptions.sky_replacement_template_id``.

        Returns:
            List of SkyTemplate entries.

        Raises:
            ImagenError: If the response cannot be parsed.
        """
        self._logger.debug("Getting sky replacement templates")
        response_json = await self._make_request("GET", "/projects/sky_replacement/templates")
        return self._parse_model(response_json, SkyTemplatesResponse, "sky replacement templates response", ImagenError).templates

    async def get_export_upload_link(self, project_uuid: str, file_name: str) -> TemporaryFileUploadData:
        """
        Get a presigned upload link for a single exported image.

        Args:
            project_uuid: UUID of the project.
            file_name: The exported image file name.

        Returns:
            TemporaryFileUploadData with the file name and presigned upload link.

        Raises:
            ProjectError: If the response cannot be parsed.
        """
        self._logger.debug(f"Getting export upload link for {file_name} in {project_uuid}")
        response_json = await self._make_request("GET", f"/projects/{project_uuid}/export/get_upload_link", params={"file_name": file_name})
        return self._parse_model(response_json, TemporaryFileUploadData, "export upload link response", ProjectError)

    async def get_export_download_link(self, project_uuid: str, file_name: str) -> FileDownloadInfo:
        """
        Get a presigned download link for a single exported image.

        Args:
            project_uuid: UUID of the project.
            file_name: The exported image file name.

        Returns:
            FileDownloadInfo with the file name and download link.

        Raises:
            ProjectError: If the response cannot be parsed.
        """
        self._logger.debug(f"Getting export download link for {file_name} in {project_uuid}")
        response_json = await self._make_request(
            "GET", f"/projects/{project_uuid}/export/get_download_link", params={"file_name": file_name}
        )
        return self._parse_model(response_json, FileDownloadInfo, "export download link response", ProjectError)
