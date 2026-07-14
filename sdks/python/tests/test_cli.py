"""Tests for the `imagen` CLI (imagen_sdk.cli).

The CLI is a thin wrapper, so these tests mock the SDK layer and assert the CLI
contract: JSON vs human output, exit codes, argument -> SDK mapping, and config.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from imagen_sdk import cli as cli_mod
from imagen_sdk.cli import cli
from imagen_sdk.enums import PhotographyType
from imagen_sdk.models import Profile, QuickEditResult, UploadResult, UploadSummary

pytestmark = pytest.mark.unit


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    """Point the config file at a temp location so tests never touch ~/.imagen."""
    monkeypatch.setattr(cli_mod, "CONFIG_PATH", tmp_path / "config.json")
    monkeypatch.delenv("IMAGEN_API_KEY", raising=False)


def test_help(runner):
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "agent-native" in result.output


def test_missing_api_key_json(runner):
    result = runner.invoke(cli, ["--json", "profiles"])
    assert result.exit_code == 2
    payload = json.loads(result.output)
    assert payload["error"] == "config"


def test_profiles_json(runner):
    fake = [Profile(image_type="RAW", profile_key=7, profile_name="Warm", profile_type="STYLE")]
    with patch.object(cli_mod, "get_profiles", AsyncMock(return_value=fake)):
        result = runner.invoke(cli, ["--api-key", "k", "--json", "profiles"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data[0]["profile_key"] == 7


def test_profiles_human(runner):
    fake = [Profile(image_type="RAW", profile_key=7, profile_name="Warm", profile_type="STYLE")]
    with patch.object(cli_mod, "get_profiles", AsyncMock(return_value=fake)):
        result = runner.invoke(cli, ["--api-key", "k", "profiles"])
    assert result.exit_code == 0
    assert "Warm" in result.output
    assert not result.output.strip().startswith("[")  # not JSON


def test_edit_mixed_folder_errors(runner, tmp_path):
    (tmp_path / "a.cr2").touch()
    (tmp_path / "b.jpg").touch()
    result = runner.invoke(cli, ["--api-key", "k", "--json", "edit", str(tmp_path), "--profile", "1"])
    assert result.exit_code == 1
    assert json.loads(result.output)["error"] == "input"


def test_edit_maps_args_to_quick_edit(runner, tmp_path):
    (tmp_path / "photo.jpg").touch()
    fake_result = QuickEditResult(
        project_uuid="uuid-123",
        upload_summary=UploadSummary(
            total=1,
            successful=1,
            failed=0,
            results=[UploadResult(file="photo.jpg", success=True)],
        ),
        download_links=["http://x/1"],
    )
    mock = AsyncMock(return_value=fake_result)
    with patch.object(cli_mod, "quick_edit", mock):
        result = runner.invoke(
            cli,
            [
                "--api-key",
                "k",
                "--json",
                "edit",
                str(tmp_path),
                "--profile",
                "42",
                "--type",
                "wedding",
                "--crop",
                "--smooth-skin",
            ],
        )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["project_uuid"] == "uuid-123"

    kwargs = mock.call_args.kwargs
    assert kwargs["profile_key"] == 42
    assert kwargs["photography_type"] == PhotographyType.WEDDING
    assert kwargs["edit_options"].crop is True
    assert kwargs["edit_options"].smooth_skin is True
    # untouched flags stay unset (None), never coerced to False
    assert kwargs["edit_options"].straighten is None


def test_edit_missing_profile_errors(runner, tmp_path):
    (tmp_path / "photo.jpg").touch()
    result = runner.invoke(cli, ["--api-key", "k", "--json", "edit", str(tmp_path)])
    assert result.exit_code == 2
    assert json.loads(result.output)["error"] == "config"


def test_config_masks_api_key(runner):
    set_result = runner.invoke(cli, ["--json", "config", "--api-key", "SECRET", "--profile", "9"])
    assert set_result.exit_code == 0
    view = json.loads(set_result.output)
    assert view["api_key"] == "***set***"
    assert view["profile"] == 9
    # persisted on disk with the real value
    stored = json.loads(Path(cli_mod.CONFIG_PATH).read_text())
    assert stored["api_key"] == "SECRET"


def test_config_value_used_as_fallback(runner):
    runner.invoke(cli, ["config", "--api-key", "FROMFILE"])
    fake = []
    seen = {}

    async def _capture(api_key, base_url):
        seen["api_key"] = api_key
        return fake

    with patch.object(cli_mod, "get_profiles", _capture):
        result = runner.invoke(cli, ["--json", "profiles"])
    assert result.exit_code == 0
    assert seen["api_key"] == "FROMFILE"
