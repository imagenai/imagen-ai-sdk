"""Tests for new enums, EditOptions fields, request models, and the _unwrap helper."""

import pytest

from imagen_sdk import (
    CopilotRequest,
    DNGCompression,
    EditOptions,
    EnhanceImageRequest,
    I2IEditOptions,
    ImagenClient,
    PhotographyType,
    ProjectSource,
)


class TestUnwrap:
    """Envelope-tolerant _unwrap behavior."""

    def test_unwraps_sole_data_key(self):
        assert ImagenClient._unwrap({"data": {"project_uuid": "x"}}) == {"project_uuid": "x"}

    def test_passes_through_unwrapped_dict(self):
        payload = {"project_uuid": "x"}
        assert ImagenClient._unwrap(payload) == payload

    def test_does_not_unwrap_when_data_not_sole_key(self):
        payload = {"data": 1, "other": 2}
        assert ImagenClient._unwrap(payload) == payload

    def test_passes_through_list(self):
        payload = [{"a": 1}]
        assert ImagenClient._unwrap(payload) == payload

    def test_passes_through_scalar(self):
        assert ImagenClient._unwrap("uuid-str") == "uuid-str"


class TestEnumAdditions:
    def test_photography_type_school(self):
        assert PhotographyType.SCHOOL.value == "SCHOOL"

    def test_dng_compression_values(self):
        assert {c.value for c in DNGCompression} == {"LOSSY", "LOSSLESS"}

    def test_project_source_values(self):
        assert {s.value for s in ProjectSource} == {"REGULAR", "I2I"}


class TestEditOptionsNewFields:
    def test_hdr_output_compression_serializes_to_value(self):
        opts = EditOptions(hdr_merge=True, hdr_output_compression=DNGCompression.LOSSLESS)
        api = opts.to_api_dict()
        assert api["hdr_output_compression"] == "LOSSLESS"
        assert api["hdr_merge"] is True

    def test_callback_url_included(self):
        opts = EditOptions(callback_url="https://example.com/hook")
        assert opts.to_api_dict()["callback_url"] == "https://example.com/hook"

    def test_none_fields_excluded(self):
        opts = EditOptions(crop=True)
        api = opts.to_api_dict()
        assert "callback_url" not in api
        assert "hdr_output_compression" not in api

    def test_existing_mutual_exclusivity_still_enforced(self):
        with pytest.raises(ValueError):
            EditOptions(crop=True, headshot_crop=True)


class TestRequestModels:
    def test_enhance_request_excludes_none_parent(self):
        req = EnhanceImageRequest(tool_id="denoise")
        api = req.to_api_dict()
        assert api == {"tool_id": "denoise", "project_source": "REGULAR"}

    def test_copilot_request_validation_rejects_empty(self):
        with pytest.raises(ValueError):
            CopilotRequest(instruction="")

    def test_copilot_request_rejects_too_long(self):
        with pytest.raises(ValueError):
            CopilotRequest(instruction="x" * 256)

    def test_copilot_request_payload(self):
        req = CopilotRequest(instruction="brighten the sky", parent_version_id=3, project_source=ProjectSource.I2I)
        assert req.to_api_dict() == {
            "instruction": "brighten the sky",
            "parent_version_id": 3,
            "project_source": "I2I",
        }

    def test_i2i_edit_options_excludes_none(self):
        opts = I2IEditOptions(hdr_merge=True, callback_url="https://cb")
        assert opts.to_api_dict() == {"hdr_merge": True, "callback_url": "https://cb"}
