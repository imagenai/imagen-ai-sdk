"""Agent-native command-line interface for the Imagen AI SDK.

Design goals (see docs/plans): a thin, non-interactive wrapper over the SDK that
is equally usable by humans and AI agents.

- Every command accepts ``--json`` for machine-readable output (a single JSON
  document on stdout); errors in JSON mode are ``{"error": ..., "message": ...}``
  on stderr with a non-zero exit code.
- No interactive prompts. Missing required input is a hard error, never a prompt.
- API key resolves from ``--api-key`` > ``IMAGEN_API_KEY`` env > ``~/.imagen/config.json``.

ponytail: one file. It's a flat command surface over an existing SDK; splitting
it buys nothing until it grows past ~800 lines.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable, NoReturn, TypeVar

import click
from pydantic import BaseModel, ValidationError

from . import __version__
from .enums import PhotographyType
from .exceptions import AuthenticationError, ImagenError, UploadError
from .imagen_sdk import (
    DEFAULT_BASE_URL,
    JPG_EXTENSIONS,
    RAW_EXTENSIONS,
    SUPPORTED_FILE_FORMATS,
    ImagenClient,
    get_ai_tools,
    get_profiles,
    get_sky_replacement_templates,
    list_projects,
    quick_edit,
)
from .models import EditOptions, I2IEditOptions

CONFIG_PATH = Path.home() / ".imagen" / "config.json"

# --------------------------------------------------------------------------- #
# config file                                                                 #
# --------------------------------------------------------------------------- #


def _load_config() -> dict[str, Any]:
    try:
        return json.loads(CONFIG_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_config(cfg: dict[str, Any]) -> None:
    # Write atomically so a crash or a concurrent `imagen config` can't leave a
    # truncated file that _load_config would then silently reset to {}.
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_PATH.with_name(CONFIG_PATH.name + ".tmp")
    tmp.write_text(json.dumps(cfg, indent=2) + "\n")
    os.replace(tmp, CONFIG_PATH)


# --------------------------------------------------------------------------- #
# output helpers                                                              #
# --------------------------------------------------------------------------- #


def _emit(ctx: dict[str, Any], data: Any, human: Callable[[Any], None]) -> None:
    """Render a result. JSON mode dumps a plain-data form; human mode gets the raw object."""
    if ctx["json"]:
        click.echo(json.dumps(_dump(data), indent=2, default=str))
    else:
        human(data)


def _emit_error(json_mode: bool, kind: str, message: str, code: int) -> NoReturn:
    if json_mode:
        click.echo(json.dumps({"error": kind, "message": message}), err=True)
    else:
        click.secho(f"Error: {message}", fg="red", err=True)
    raise SystemExit(code)


def _fail(ctx: dict[str, Any], kind: str, message: str, code: int) -> NoReturn:
    _emit_error(ctx["json"], kind, message, code)


def _run(ctx: dict[str, Any], coro: Any) -> Any:
    """Run an SDK coroutine, mapping SDK errors to stable exit codes.

    2 = authentication, 1 = any other failure.
    """
    try:
        return asyncio.run(coro)
    except AuthenticationError as exc:
        _fail(ctx, "authentication", str(exc), 2)
    except ImagenError as exc:
        _fail(ctx, "api", str(exc), 1)
    except click.ClickException:
        raise
    except Exception as exc:  # noqa: BLE001 - top-level guard for a CLI boundary
        _fail(ctx, "error", str(exc), 1)


def _dump(obj: Any) -> Any:
    """Best-effort conversion of pydantic models / lists to plain JSON data."""
    if isinstance(obj, list):
        return [_dump(o) for o in obj]
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    return obj


def _resolve_api_key(ctx: dict[str, Any]) -> str:
    raw = ctx["api_key"] or os.environ.get("IMAGEN_API_KEY") or _load_config().get("api_key") or ""
    key = raw.strip()
    if not key:
        _fail(ctx, "config", "No API key. Pass --api-key, set IMAGEN_API_KEY, or run `imagen config --api-key <key>`.", 2)
    return key


_M = TypeVar("_M", bound=BaseModel)


def _build_options(ctx: dict[str, Any], model: type[_M], flags: dict[str, Any]) -> _M:
    """Construct an option model, mapping validation errors to a JSON `input` error.

    Without this, e.g. `--crop --portrait-crop` (mutually exclusive) would raise an
    uncaught ValidationError instead of honoring the CLI's JSON/exit-code contract.
    """
    try:
        return model(**{k: v for k, v in flags.items() if v is not None})
    except ValidationError as exc:
        msg = "; ".join(e.get("msg", "") for e in exc.errors()) or str(exc)
        _fail(ctx, "input", msg, 1)


def _gather_images(ctx: dict[str, Any], path_str: str) -> list[Path]:
    """Expand a file or a top-level folder into a same-type list of image paths."""
    path = Path(path_str)
    if not path.exists():
        _fail(ctx, "input", f"Path does not exist: {path}", 1)
    if path.is_file():
        if path.suffix.lower() not in SUPPORTED_FILE_FORMATS:
            _fail(ctx, "input", f"Unsupported file type: {path.name}", 1)
        files = [path]
    else:
        files = sorted(f for f in path.iterdir() if f.is_file() and f.suffix.lower() in SUPPORTED_FILE_FORMATS)
    if not files:
        _fail(ctx, "input", f"No supported image files found in {path}", 1)

    raws = [f for f in files if f.suffix.lower() in RAW_EXTENSIONS]
    jpgs = [f for f in files if f.suffix.lower() in JPG_EXTENSIONS]
    if raws and jpgs:
        _fail(
            ctx,
            "input",
            "Folder mixes RAW and JPEG files, which cannot share a project. Run separately on RAW-only and JPEG-only folders.",
            1,
        )
    return files


# --------------------------------------------------------------------------- #
# root group                                                                  #
# --------------------------------------------------------------------------- #


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, "-V", "--version", prog_name="imagen")
@click.option("--api-key", default=None, help="Imagen API key (else IMAGEN_API_KEY or config).")
@click.option("--base-url", default=None, help=f"API base URL (default: {DEFAULT_BASE_URL}).")
@click.option("--json", "json_mode", is_flag=True, help="Emit machine-readable JSON on stdout.")
@click.pass_context
def cli(ctx: click.Context, api_key: str | None, base_url: str | None, json_mode: bool) -> None:
    """Imagen AI — agent-native photo editing CLI.

    Run any command with --json for machine-readable output. See `imagen COMMAND --help`.
    """
    cfg = _load_config()
    ctx.obj = {
        "api_key": api_key,
        "base_url": base_url or cfg.get("base_url") or DEFAULT_BASE_URL,
        "json": json_mode,
    }


# --------------------------------------------------------------------------- #
# read commands                                                               #
# --------------------------------------------------------------------------- #


@cli.command()
@click.pass_obj
def profiles(ctx: dict[str, Any]) -> None:
    """List your editing profiles (use profile_key with `edit`)."""
    key = _resolve_api_key(ctx)
    result = _run(ctx, get_profiles(key, ctx["base_url"]))

    def human(items: list[Any]) -> None:
        if not items:
            click.echo("No profiles found.")
            return
        for p in items:
            click.echo(f"{p.profile_key:>8}  {p.image_type:<6}  {p.profile_type:<10}  {p.profile_name}")

    _emit(ctx, result, human)


@cli.command()
@click.option("--size", default=20, show_default=True, help="Page size (1-100).")
@click.option("--page", default=0, show_default=True, help="Zero-based page index.")
@click.pass_obj
def projects(ctx: dict[str, Any], size: int, page: int) -> None:
    """List projects in your account."""
    key = _resolve_api_key(ctx)
    result = _run(ctx, list_projects(key, size=size, page=page, base_url=ctx["base_url"]))

    def human(resp: Any) -> None:
        for item in resp.projects:
            name = item.name or "(unnamed)"
            click.echo(f"{item.project_uuid}  {item.status:<12}  {item.number_of_images:>4} img  {name}")

    _emit(ctx, result, human)


@cli.command(name="sky-templates")
@click.pass_obj
def sky_templates(ctx: dict[str, Any]) -> None:
    """List sky replacement templates (id -> --sky-template-id)."""
    key = _resolve_api_key(ctx)
    result = _run(ctx, get_sky_replacement_templates(key, ctx["base_url"]))

    def human(items: list[Any]) -> None:
        for t in items:
            click.echo(f"{t.id:>6}  {'default' if t.is_default else ''}")

    _emit(ctx, result, human)


@cli.command(name="ai-tools")
@click.argument("project_uuid")
@click.pass_obj
def ai_tools(ctx: dict[str, Any], project_uuid: str) -> None:
    """List AI quick tools available for a project (enhancement_type -> --tool-id)."""
    key = _resolve_api_key(ctx)
    result = _run(ctx, get_ai_tools(key, project_uuid, ctx["base_url"]))
    _emit(ctx, result, lambda r: click.echo(json.dumps(_dump(r), indent=2)))


# --------------------------------------------------------------------------- #
# edit (quick_edit) — the headline command                                    #
# --------------------------------------------------------------------------- #

_PHOTO_TYPES = [t.value for t in PhotographyType]


@cli.command()
@click.argument("folder")
@click.option("--profile", "profile_key", type=int, default=None, help="Profile key (see `imagen profiles`).")
@click.option(
    "--type",
    "photo_type",
    type=click.Choice(_PHOTO_TYPES, case_sensitive=False),
    default=None,
    help="Photography type for AI optimization.",
)
@click.option("--name", "project_name", default=None, help="Project name (must be unique).")
@click.option("--out", "download_dir", default="downloads", show_default=True, help="Download directory.")
@click.option("--export/--no-export", default=False, help="Also export final JPEGs.")
@click.option("--download/--no-download", "download", default=True, show_default=True, help="Download results locally.")
# editing options (EditOptions)
@click.option("--crop", is_flag=True, default=None)
@click.option("--straighten", is_flag=True, default=None)
@click.option("--hdr-merge", is_flag=True, default=None)
@click.option("--portrait-crop", is_flag=True, default=None)
@click.option("--smooth-skin", is_flag=True, default=None)
@click.option("--subject-mask", is_flag=True, default=None)
@click.option("--headshot-crop", is_flag=True, default=None)
@click.option("--perspective-correction", is_flag=True, default=None)
@click.option("--sky-replacement", is_flag=True, default=None)
@click.option("--sky-template-id", "sky_replacement_template_id", type=int, default=None)
@click.option("--window-pull", is_flag=True, default=None)
@click.option("--crop-aspect-ratio", default=None, help="e.g. 2X3, 4X5, 5X7.")
@click.pass_obj
def edit(
    ctx: dict[str, Any],
    folder: str,
    profile_key: int | None,
    photo_type: str | None,
    project_name: str | None,
    download_dir: str,
    export: bool,
    download: bool,
    **edit_flags: Any,
) -> None:
    """Edit a folder (or single file) of RAW/JPEG photos with your AI profile.

    Runs the full workflow: create project, upload, edit, and optionally
    export + download. All files must be the same type (all RAW or all JPEG).
    """
    key = _resolve_api_key(ctx)
    profile_key = profile_key if profile_key is not None else _load_config().get("profile")
    if profile_key is None:
        _fail(ctx, "config", "No profile. Pass --profile or run `imagen config --profile <key>`.", 2)

    images = _gather_images(ctx, folder)
    edit_options = _build_options(ctx, EditOptions, edit_flags)
    ptype = PhotographyType(photo_type.upper()) if photo_type else None

    result = _run(
        ctx,
        quick_edit(
            api_key=key,
            profile_key=int(profile_key),
            image_paths=[str(p) for p in images],
            project_name=project_name,
            photography_type=ptype,
            export=export,
            edit_options=edit_options,
            download=download,
            download_dir=download_dir,
            base_url=ctx["base_url"],
        ),
    )

    def human(res: Any) -> None:
        s = res.upload_summary
        click.echo(f"Project: {res.project_uuid}")
        click.echo(f"Uploaded: {s.successful}/{s.total} (failed {s.failed})")
        click.echo(f"Edited links: {len(res.download_links)}")
        if res.downloaded_files:
            click.echo(f"Downloaded: {len(res.downloaded_files)} -> {download_dir}")
        if res.exported_files:
            click.echo(f"Exported: {len(res.exported_files)}")

    _emit(ctx, result, human)


# --------------------------------------------------------------------------- #
# enhance (AI quick tool on an edited image)                                  #
# --------------------------------------------------------------------------- #


@cli.command()
@click.argument("project_uuid")
@click.argument("filename")
@click.option("--tool-id", required=True, help="AI tool id (see `imagen ai-tools <project>`).")
@click.option("--parent-version-id", type=int, default=None, help="Version to base the enhancement on.")
@click.pass_obj
def enhance(ctx: dict[str, Any], project_uuid: str, filename: str, tool_id: str, parent_version_id: int | None) -> None:
    """Apply an AI quick tool to an already-edited image."""
    key = _resolve_api_key(ctx)

    async def _do() -> Any:
        async with ImagenClient(key, ctx["base_url"]) as client:
            return await client.enhance_image(project_uuid, filename, tool_id, parent_version_id=parent_version_id)

    result = _run(ctx, _do())
    _emit(ctx, result, lambda r: click.echo(json.dumps(_dump(r), indent=2)))


# --------------------------------------------------------------------------- #
# i2i (image-to-image) workflow                                               #
# --------------------------------------------------------------------------- #


@cli.command()
@click.argument("folder")
@click.option("--name", "project_name", default=None, help="Project name.")
@click.option("--out", "download_dir", default="downloads", show_default=True, help="Download directory.")
@click.option("--download/--no-download", "download", default=True, show_default=True)
@click.option("--hdr-merge", is_flag=True, default=None)
@click.option("--sky-replacement", is_flag=True, default=None)
@click.option("--sky-template-id", "sky_replacement_template_id", type=int, default=None)
@click.option("--perspective-correction", is_flag=True, default=None)
@click.pass_obj
def i2i(ctx: dict[str, Any], folder: str, project_name: str | None, download_dir: str, download: bool, **edit_flags: Any) -> None:
    """Run the image-to-image (i2i) editing workflow on a folder of photos."""
    key = _resolve_api_key(ctx)
    images = _gather_images(ctx, folder)
    edit_options = _build_options(ctx, I2IEditOptions, edit_flags)

    async def _do() -> dict[str, Any]:
        async with ImagenClient(key, ctx["base_url"]) as client:
            project_uuid = await client.create_i2i_project(project_name)
            summary = await client.upload_i2i_images(project_uuid, [str(p) for p in images])
            if summary.successful == 0:
                raise UploadError("No images uploaded successfully; not starting i2i editing.")
            await client.start_i2i_editing(project_uuid, edit_options)
            await client.wait_for_i2i_completion(project_uuid)
            links = await client.get_i2i_download_links(project_uuid)
            downloaded = None
            if download:
                downloaded = await client.download_files(links, download_dir)
            return {
                "project_uuid": project_uuid,
                "upload_summary": _dump(summary),
                "download_links": links,
                "downloaded_files": downloaded,
            }

    result = _run(ctx, _do())

    def human(res: dict[str, Any]) -> None:
        click.echo(f"Project: {res['project_uuid']}")
        click.echo(f"Edited links: {len(res['download_links'])}")
        if res["downloaded_files"]:
            click.echo(f"Downloaded: {len(res['downloaded_files'])} -> {download_dir}")

    _emit(ctx, result, human)  # i2i already returns plain JSON data


# --------------------------------------------------------------------------- #
# config                                                                      #
# --------------------------------------------------------------------------- #


@cli.command()
@click.option("--api-key", default=None, help="Store an API key.")
@click.option("--profile", type=int, default=None, help="Store a default profile key.")
@click.option("--base-url", default=None, help="Store a default base URL.")
@click.pass_obj
def config(ctx: dict[str, Any], api_key: str | None, profile: int | None, base_url: str | None) -> None:
    """Show or set persisted defaults (~/.imagen/config.json)."""
    cfg = _load_config()
    updates = {"api_key": api_key, "profile": profile, "base_url": base_url}
    updates = {k: v for k, v in updates.items() if v is not None}
    if updates:
        cfg.update(updates)
        _save_config(cfg)

    # Never echo the raw API key back; report presence only.
    view = dict(cfg)
    if "api_key" in view:
        view["api_key"] = "***set***"

    def human(v: dict[str, Any]) -> None:
        if not v:
            click.echo("No config set.")
            return
        for k, val in v.items():
            click.echo(f"{k} = {val}")

    _emit(ctx, view, human)


def main() -> None:
    """Entry point that keeps Click parse errors inside the CLI's contract.

    Click's own usage errors would otherwise print human text and exit 2 (which
    we reserve for auth/config). We run non-standalone and normalize: usage/parse
    errors become a JSON `input` error (in --json mode) with exit code 1. Errors
    raised by commands themselves already exit via `_fail` and propagate here.
    """
    json_mode = "--json" in sys.argv[1:]
    try:
        code = cli.main(standalone_mode=False)
    except (click.UsageError, click.ClickException) as exc:
        _emit_error(json_mode, "input", exc.format_message(), 1)
    except click.exceptions.Abort:
        _emit_error(json_mode, "error", "Aborted.", 1)
    else:
        sys.exit(code or 0)


if __name__ == "__main__":
    main()
