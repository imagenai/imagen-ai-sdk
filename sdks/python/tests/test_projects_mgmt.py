"""Tests for the project management mixin (listing, retrieval, sky templates, export links)."""

import pytest

from imagen_sdk import ImagenError, ProjectError


def _project_item(uuid="p-1", name="My Project"):
    return {
        "project_id": 1,
        "project_uuid": uuid,
        "name": name,
        "status": "Completed",
        "created_at": "2026-01-01T00:00:00Z",
        "number_of_images": 3,
        "profile": "Wedding",
        "ai_tools": ["denoise"],
        "customer_reference_id": 42,
        "thumbnail_src": None,
        "export_status": None,
    }


class TestListProjects:
    @pytest.mark.asyncio
    async def test_list_projects_unwrapped(self, client, mock_request_factory):
        response = {"projects": [_project_item()], "pagination": {"total": 1, "size": 20, "page": 0}}
        with mock_request_factory(response):
            result = await client.list_projects()
            assert result.pagination.total == 1
            assert result.projects[0].project_uuid == "p-1"
            client._make_request.assert_called_once()
            args, kwargs = client._make_request.call_args
            assert args[0] == "GET"
            assert args[1] == "/projects"
            assert kwargs["params"]["client_type"] == "API"

    @pytest.mark.asyncio
    async def test_list_projects_wrapped_envelope(self, client, mock_request_factory):
        response = {"data": {"projects": [_project_item()], "pagination": {"total": 1, "size": 20, "page": 0}}}
        with mock_request_factory(response):
            result = await client.list_projects()
            assert result.projects[0].name == "My Project"

    @pytest.mark.asyncio
    async def test_list_projects_invalid(self, client, mock_request_factory):
        with mock_request_factory({"unexpected": True}):
            with pytest.raises(ProjectError):
                await client.list_projects()


class TestGetProject:
    @pytest.mark.asyncio
    async def test_get_project(self, client, mock_request_factory):
        with mock_request_factory(_project_item(uuid="abc")):
            item = await client.get_project("abc")
            assert item.project_uuid == "abc"
            assert item.number_of_images == 3


class TestGetProjectUuid:
    @pytest.mark.asyncio
    async def test_dict_with_project_uuid(self, client, mock_request_factory):
        with mock_request_factory({"project_uuid": "u-123"}):
            assert await client.get_project_uuid("name") == "u-123"

    @pytest.mark.asyncio
    async def test_bare_string(self, client, mock_request_factory):
        with mock_request_factory("u-456"):
            assert await client.get_project_uuid("name") == "u-456"

    @pytest.mark.asyncio
    async def test_unresolvable_raises(self, client, mock_request_factory):
        with mock_request_factory({"nope": 1}):
            with pytest.raises(ProjectError):
                await client.get_project_uuid("name")


class TestSkyTemplates:
    @pytest.mark.asyncio
    async def test_get_sky_templates(self, client, mock_request_factory):
        response = {"templates": [{"id": 1, "is_default": True}, {"id": 2, "is_default": False}]}
        with mock_request_factory(response):
            templates = await client.get_sky_replacement_templates()
            assert [t.id for t in templates] == [1, 2]
            assert templates[0].is_default is True

    @pytest.mark.asyncio
    async def test_get_sky_templates_invalid(self, client, mock_request_factory):
        with mock_request_factory({"bad": 1}):
            with pytest.raises(ImagenError):
                await client.get_sky_replacement_templates()


class TestExportLinks:
    @pytest.mark.asyncio
    async def test_export_upload_link(self, client, mock_request_factory):
        with mock_request_factory({"file_name": "a.jpg", "upload_link": "https://up"}):
            data = await client.get_export_upload_link("p", "a.jpg")
            assert data.upload_link == "https://up"
            args, kwargs = client._make_request.call_args
            assert kwargs["params"] == {"file_name": "a.jpg"}

    @pytest.mark.asyncio
    async def test_export_download_link(self, client, mock_request_factory):
        with mock_request_factory({"file_name": "a.jpg", "download_link": "https://dl"}):
            data = await client.get_export_download_link("p", "a.jpg")
            assert data.download_link == "https://dl"
