"""Tests for the AI enhancement / copilot / finalize mixin."""

import pytest
from pydantic import ValidationError

from imagen_sdk import ImagenError, ProjectSource


class TestAITools:
    @pytest.mark.asyncio
    async def test_get_ai_tools_parsed(self, client, mock_request_factory):
        response = {
            "prompts": [
                {"enhancement_type": "virtual_staging", "label": "Virtual staging", "enabled_for_batch": False},
                {"enhancement_type": "remove_cameraman", "label": "Remove camera", "enabled_for_batch": True},
            ]
        }
        with mock_request_factory(response):
            tools = await client.get_ai_tools("proj")
            assert [t.enhancement_type for t in tools.prompts] == ["virtual_staging", "remove_cameraman"]
            assert tools.prompts[1].enabled_for_batch is True
            args, kwargs = client._make_request.call_args
            assert args == ("GET", "/projects/proj/ai-tools")
            assert kwargs["params"] == {"project_source": "REGULAR"}

    @pytest.mark.asyncio
    async def test_get_ai_tools_envelope_wrapped(self, client, mock_request_factory):
        with mock_request_factory({"data": {"prompts": [{"enhancement_type": "green_grass"}]}}):
            tools = await client.get_ai_tools("proj")
            assert tools.prompts[0].enhancement_type == "green_grass"


ENHANCE_RESPONSE = {"status": "SUCCESS", "version_id": 3, "enhanced_image_url": "https://img/enhanced.jpg"}


class TestEnhanceImage:
    @pytest.mark.asyncio
    async def test_enhance_image_payload(self, client, mock_request_factory):
        with mock_request_factory(ENHANCE_RESPONSE):
            result = await client.enhance_image("proj", "img.jpg", "denoise", parent_version_id=5)
            assert result.status == "SUCCESS"
            assert result.version_id == 3
            assert result.enhanced_image_url == "https://img/enhanced.jpg"
            args, kwargs = client._make_request.call_args
            assert args == ("POST", "/projects/proj/images/img.jpg/enhance")
            assert kwargs["json"] == {
                "tool_id": "denoise",
                "parent_version_id": 5,
                "project_source": "REGULAR",
            }

    @pytest.mark.asyncio
    async def test_enhance_image_omits_none_parent(self, client, mock_request_factory):
        with mock_request_factory(ENHANCE_RESPONSE):
            await client.enhance_image("proj", "img.jpg", "denoise")
            _, kwargs = client._make_request.call_args
            assert "parent_version_id" not in kwargs["json"]

    @pytest.mark.asyncio
    async def test_enhance_image_envelope_wrapped(self, client, mock_request_factory):
        with mock_request_factory({"data": ENHANCE_RESPONSE}):
            result = await client.enhance_image("proj", "img.jpg", "denoise")
            assert result.enhanced_image_url == "https://img/enhanced.jpg"


class TestCopilot:
    @pytest.mark.asyncio
    async def test_apply_copilot_payload(self, client, mock_request_factory):
        with mock_request_factory(ENHANCE_RESPONSE):
            result = await client.apply_copilot("proj", "img.jpg", "make it warmer", project_source=ProjectSource.I2I)
            assert result.status == "SUCCESS"
            args, kwargs = client._make_request.call_args
            assert args == ("POST", "/projects/proj/images/img.jpg/copilot")
            assert kwargs["json"]["instruction"] == "make it warmer"
            assert kwargs["json"]["project_source"] == "I2I"

    @pytest.mark.asyncio
    async def test_reset_copilot_uses_delete(self, client, mock_request_factory):
        with mock_request_factory({}):
            result = await client.reset_copilot("proj", "img.jpg")
            assert result is None
            args, kwargs = client._make_request.call_args
            assert args == ("DELETE", "/projects/proj/images/img.jpg/copilot")
            assert kwargs["json"] == {"project_source": "REGULAR"}


class TestEnhancementBreakFlows:
    @pytest.mark.asyncio
    async def test_enhance_image_rejects_empty_tool_id(self, client):
        # Boundary validation: tool_id must be non-empty (no request is made).
        with pytest.raises(ValidationError):
            await client.enhance_image("proj", "img.jpg", tool_id="")

    @pytest.mark.asyncio
    async def test_apply_copilot_rejects_overlong_instruction(self, client):
        # Boundary validation: instruction is capped at 255 characters.
        with pytest.raises(ValidationError):
            await client.apply_copilot("proj", "img.jpg", "x" * 256)

    @pytest.mark.asyncio
    async def test_enhance_image_propagates_api_error(self, client):
        # E.g. enhancing a not-yet-exported project surfaces the API error.
        from unittest.mock import AsyncMock, patch

        err = ImagenError("API Error (400): Project has not been exported yet.")
        with patch.object(client, "_make_request", new=AsyncMock(side_effect=err)):
            with pytest.raises(ImagenError, match="Project has not been exported yet."):
                await client.enhance_image("bad-uuid", "img.jpg", tool_id="remove_cameraman")


class TestFinalize:
    @pytest.mark.asyncio
    async def test_finalize_project(self, client, mock_request_factory):
        response = {"files_list": [{"file_name": "a.jpg", "download_link": "https://dl/a.jpg"}]}
        with mock_request_factory(response):
            result = await client.finalize_project("proj", project_source=ProjectSource.I2I)
            assert [f.file_name for f in result.files_list] == ["a.jpg"]
            assert result.files_list[0].download_link == "https://dl/a.jpg"
            args, kwargs = client._make_request.call_args
            assert args == ("POST", "/projects/proj/finalize")
            assert kwargs["json"] == {"project_source": "I2I"}
