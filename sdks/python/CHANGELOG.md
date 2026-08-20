# Changelog

All notable changes to the `imagen-ai-sdk` Python package (and the `imagen` CLI
built from it) are documented here. This project follows
[Semantic Versioning](https://semver.org/) and the
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format.

## [1.2.1] - 2026-08-20

### Changed

- Package metadata: `Homepage` project URL now points at the developer docs
  (https://api-docs.imagen-ai.com) so registries and agents can verify this is
  the official Imagen AI SDK; the marketing site moved to a `Website` URL.
  No code changes.

## [1.2.0] - 2026-07-20

### Added

- **`imagen skill` CLI command** — prints or installs an agent skill that teaches
  an AI coding agent to drive the CLI. `--claude` / `--codex` choose the install
  location (`~/.claude/skills/imagen-cli/SKILL.md` or
  `~/.codex/skills/imagen-cli/SKILL.md`); both agents use the same `SKILL.md`
  format, so the content is identical. Honors the global `--json` flag and the
  CLI's stable exit codes.
- Embedded skill text as a single source of truth (`imagen_sdk/skill_text.py`);
  the committed `skills/imagen-cli/SKILL.md` is generated from it and guarded
  against drift by a test.

### Documentation

- Added a root `AGENTS.md` (contributor guide for coding agents) and
  `docs/RELEASING.md` (per-SDK tag-gated release process, incl. PyPI
  Trusted-Publishing setup).
- Rewrote the root `README.md` into a developer-focused landing page and
  documented `imagen skill` in `docs/CLI.md`.
- Corrected doc drift: the CLI wraps the *core editing workflows* (not the full
  API); added the `.srf`/`.sr2` RAW extensions to the supported-format lists.

## Earlier releases

For 1.1.0 and earlier, see the version-tagged notes in
[`README.md`](README.md) (e.g. the "New in v1.1.0" section covering AI
enhancement/copilot, image-to-image, project management, sky-replacement
templates, and per-image export links).
