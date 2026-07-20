"""Tests for the `imagen` CLI (imagen_sdk.cli).

The CLI is a thin wrapper, so these tests mock the SDK layer and assert the CLI
contract: JSON vs human output, exit codes, argument -> SDK mapping, and config.
"""

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from imagen_sdk import cli as cli_mod
from imagen_sdk.cli import cli
from imagen_sdk.enums import PhotographyType
from imagen_sdk.models import (
    EnhanceResult,
    PaginationInfo,
    Profile,
    ProjectListItem,
    ProjectListResponse,
    QuickEditResult,
    SkyTemplate,
    UploadResult,
    UploadSummary,
)


def _client_cm(**method_returns):
    """Build a mock that behaves as `async with ImagenClient(...) as client`."""
    client = AsyncMock()
    for name, value in method_returns.items():
        getattr(client, name).return_value = value
    cm = AsyncMock()
    cm.__aenter__.return_value = client
    return cm, client


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


def test_edit_sky_template_id_maps_to_model_field(runner, tmp_path):
    """Regression: --sky-template-id must reach EditOptions.sky_replacement_template_id."""
    (tmp_path / "photo.jpg").touch()
    fake = QuickEditResult(
        project_uuid="u",
        upload_summary=UploadSummary(total=1, successful=1, failed=0, results=[]),
        download_links=[],
    )
    mock = AsyncMock(return_value=fake)
    with patch.object(cli_mod, "quick_edit", mock):
        result = runner.invoke(
            cli,
            ["--api-key", "k", "--json", "edit", str(tmp_path), "--profile", "1", "--sky-replacement", "--sky-template-id", "77"],
        )
    assert result.exit_code == 0, result.output
    opts = mock.call_args.kwargs["edit_options"]
    assert opts.sky_replacement_template_id == 77
    assert opts.to_api_dict().get("sky_replacement_template_id") == 77


def test_edit_mutually_exclusive_flags_json_error(runner, tmp_path):
    (tmp_path / "photo.jpg").touch()
    result = runner.invoke(
        cli,
        ["--api-key", "k", "--json", "edit", str(tmp_path), "--profile", "1", "--crop", "--portrait-crop"],
    )
    assert result.exit_code == 1
    assert json.loads(result.output)["error"] == "input"


def test_edit_unsupported_single_file(runner, tmp_path):
    f = tmp_path / "notes.txt"
    f.touch()
    result = runner.invoke(cli, ["--api-key", "k", "--json", "edit", str(f), "--profile", "1"])
    assert result.exit_code == 1
    assert json.loads(result.output)["error"] == "input"


def test_usage_error_is_json_and_exit_1(monkeypatch, capsys):
    """Click's own parse errors must honor the JSON/exit-code contract (not exit 2).

    Goes through main() (not CliRunner), since the normalization lives there.
    """
    monkeypatch.setattr(sys, "argv", ["imagen", "--api-key", "k", "--json", "enhance", "proj", "file"])
    with pytest.raises(SystemExit) as se:
        cli_mod.main()
    assert se.value.code == 1
    payload = json.loads(capsys.readouterr().err)
    assert payload["error"] == "input"
    assert "tool-id" in payload["message"]


def test_whitespace_api_key_treated_as_missing(runner):
    result = runner.invoke(cli, ["--api-key", "   ", "--json", "profiles"])
    assert result.exit_code == 2
    assert json.loads(result.output)["error"] == "config"


def test_projects_json(runner):
    resp = ProjectListResponse(
        projects=[ProjectListItem(project_uuid="abc", status="Completed", created_at="t", number_of_images=3, customer_reference_id=100)],
        pagination=PaginationInfo(total=1, size=20, page=0),
    )
    with patch.object(cli_mod, "list_projects", AsyncMock(return_value=resp)):
        result = runner.invoke(cli, ["--api-key", "k", "--json", "projects"])
    assert result.exit_code == 0
    assert json.loads(result.output)["projects"][0]["project_uuid"] == "abc"


def test_sky_templates_json(runner):
    with patch.object(cli_mod, "get_sky_replacement_templates", AsyncMock(return_value=[SkyTemplate(id=3, is_default=True)])):
        result = runner.invoke(cli, ["--api-key", "k", "--json", "sky-templates"])
    assert result.exit_code == 0
    assert json.loads(result.output)[0]["id"] == 3


def test_ai_tools_json(runner):
    from imagen_sdk.models import AIToolsResponse

    with patch.object(cli_mod, "get_ai_tools", AsyncMock(return_value=AIToolsResponse(prompts=[]))):
        result = runner.invoke(cli, ["--api-key", "k", "--json", "ai-tools", "proj-uuid"])
    assert result.exit_code == 0
    assert "prompts" in json.loads(result.output)


def test_enhance_calls_client(runner):
    cm, client = _client_cm(enhance_image=EnhanceResult(status="COMPLETED", enhanced_image_url="http://x/e.jpg"))
    with patch.object(cli_mod, "ImagenClient", return_value=cm):
        result = runner.invoke(cli, ["--api-key", "k", "--json", "enhance", "proj", "img.jpg", "--tool-id", "SHARPEN"])
    assert result.exit_code == 0, result.output
    client.enhance_image.assert_awaited_once()
    args, kwargs = client.enhance_image.call_args
    assert args[:3] == ("proj", "img.jpg", "SHARPEN")


def test_i2i_happy_path(runner, tmp_path):
    (tmp_path / "a.jpg").touch()
    cm, client = _client_cm(
        create_i2i_project="i2i-uuid",
        upload_i2i_images=UploadSummary(total=1, successful=1, failed=0, results=[]),
        get_i2i_download_links=["http://x/1"],
        download_files=["/out/a.jpg"],
    )
    with patch.object(cli_mod, "ImagenClient", return_value=cm):
        result = runner.invoke(cli, ["--api-key", "k", "--json", "i2i", str(tmp_path), "--out", "/out"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["project_uuid"] == "i2i-uuid"
    client.start_i2i_editing.assert_awaited_once()


def test_i2i_aborts_when_all_uploads_fail(runner, tmp_path):
    (tmp_path / "a.jpg").touch()
    cm, client = _client_cm(
        create_i2i_project="i2i-uuid",
        upload_i2i_images=UploadSummary(
            total=1,
            successful=0,
            failed=1,
            results=[UploadResult(file="a.jpg", success=False, error="boom")],
        ),
    )
    with patch.object(cli_mod, "ImagenClient", return_value=cm):
        result = runner.invoke(cli, ["--api-key", "k", "--json", "i2i", str(tmp_path)])
    assert result.exit_code == 1
    client.start_i2i_editing.assert_not_called()


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


# --------------------------------------------------------------------------- #
# skill command                                                               #
# --------------------------------------------------------------------------- #

_REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize("fmt", ["claude", "codex"])
def test_skill_prints_full_skill_with_frontmatter(runner, fmt):
    # Both agents use the same SKILL.md format; Codex needs the frontmatter
    # (name/description) for discovery too, so it must NOT be stripped.
    result = runner.invoke(cli, ["skill", f"--{fmt}"])
    assert result.exit_code == 0
    assert result.output.startswith("---\nname: imagen-cli")
    assert result.output == cli_mod.SKILLS[fmt]


def test_skill_defaults_to_claude(runner):
    assert runner.invoke(cli, ["skill"]).output == runner.invoke(cli, ["skill", "--claude"]).output


def test_skill_json_wraps_content(runner):
    result = runner.invoke(cli, ["--json", "skill", "--codex"])
    assert result.exit_code == 0
    doc = json.loads(result.output)
    assert doc["format"] == "codex"
    assert doc["content"] == cli_mod.SKILLS["codex"]


@pytest.mark.parametrize(
    "fmt,rel",
    [
        # Literal expected paths, so a wrong INSTALL_PATHS constant is caught here
        # rather than silently agreeing with itself.
        ("claude", ".claude/skills/imagen-cli/SKILL.md"),
        ("codex", ".codex/skills/imagen-cli/SKILL.md"),
    ],
)
def test_skill_install_writes_to_agent_dir(runner, tmp_path, monkeypatch, fmt, rel):
    monkeypatch.setattr(cli_mod.Path, "home", staticmethod(lambda: tmp_path))
    result = runner.invoke(cli, ["--json", "skill", f"--{fmt}", "--install"])
    assert result.exit_code == 0
    dest = tmp_path / rel
    assert dest.read_text(encoding="utf-8") == cli_mod.SKILLS[fmt]
    assert json.loads(result.output)["path"] == str(dest)


def test_skill_install_error_honors_json(runner, tmp_path, monkeypatch):
    monkeypatch.setattr(cli_mod.Path, "home", staticmethod(lambda: tmp_path))
    monkeypatch.setattr(cli_mod.Path, "write_text", lambda *a, **k: (_ for _ in ()).throw(OSError("disk full")))
    result = runner.invoke(cli, ["--json", "skill", "--install"])
    assert result.exit_code == 1
    assert json.loads(result.output)["error"] == "error"


def test_repo_skills_match_embedded_source():
    # The embedded string is the source of truth; the committed skill copies
    # (Claude + Codex) are generated from it and must not drift.
    from imagen_sdk.skill_text import REPO_SKILL_FILES

    for rel in REPO_SKILL_FILES:
        assert (_REPO_ROOT / rel).read_text() == cli_mod.SKILLS["claude"], rel
