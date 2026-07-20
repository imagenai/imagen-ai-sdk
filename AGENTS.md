# AGENTS.md

Guidance for AI coding agents (Codex, Claude, etc.) working **on** this repo.
Using the tools instead of contributing to them? See
[`skills/imagen-cli/SKILL.md`](skills/imagen-cli/SKILL.md) (drive the CLI) and
[`docs/CLI.md`](docs/CLI.md).

## What this is

A multi-language SDK monorepo for the Imagen AI photo-editing API. The Python SDK
(`sdks/python/`) also produces the standalone `imagen` CLI. Node (`sdks/node/`) and
Go (`sdks/go/`) are independent ports. **Most active development is in
`sdks/python/` — run the commands below from there.**

## Setup, test, lint

**Python** (`sdks/python/`) — the primary package + the `imagen` CLI:

```bash
cd sdks/python
pip install -e ".[dev]"           # installs the SDK + the `imagen` command from live source
python -m pytest tests/           # run tests (asyncio; ~200 tests)
python -m pytest tests/test_cli.py  # CLI-only tests
python -m imagen_sdk.cli --help   # run the CLI from source (no build needed)
python -m ruff check imagen_sdk/  # lint (line-length 140)
python -m ruff format imagen_sdk/
python -m mypy imagen_sdk/        # type check
sh packaging/build.sh             # build the standalone binary -> dist/imagen (rarely needed locally)
```

**Node** (`sdks/node/`): `npm ci` · `npm run lint` · `npm run typecheck` · `npm run build` · `npm test`
**Go** (`sdks/go/`): `go test -v -race ./...`

`pre-commit run --all-files` runs ruff check + format (config at repo root). The
hooks reformat on commit — if a commit aborts saying files were modified, re-stage
and commit again. CI (`.github/workflows/ci.yml`) is path-filtered, so it only runs
the language whose files changed.

## The `imagen` CLI

`imagen_sdk/cli.py` is a thin Click wrapper over the SDK. Keep its **design
contract** true when adding commands (details in
[CLAUDE.md](CLAUDE.md#command-line-interface-imagen) / [docs/CLI.md](docs/CLI.md)):

- Every command supports `--json`; never prompts. Success JSON goes to stdout,
  error JSON (`{"error","message"}`) goes to stderr.
- Stable exit codes: `0` success, `2` auth/config, `1` any other error.
- New editing flags must map to the exact SDK model field name (Pydantic drops
  unknown fields silently).
- The CLI ships as a **PyInstaller binary** built from SDK source — editing
  `imagen_sdk/` does not change an already-built binary; contributors run from
  source via `pip install -e`.
- The agent skill text is embedded in `imagen_sdk/skill_text.py` (single source of
  truth); the committed `skills/imagen-cli/SKILL.md` is generated from it and a
  test (`test_repo_skills_match_embedded_source`) fails if they drift. Edit the
  module, then regenerate the committed copy — don't hand-edit `SKILL.md`.

## Domain gotcha

RAW and JPEG files **cannot be mixed in one project/edit** — RAW profiles can't
process JPEGs and vice versa. Split into RAW-only and JPEG-only runs. See
[docs/WORKFLOWS.md](docs/WORKFLOWS.md) for the full behavioral contract every SDK
implements.

## Versioning & releasing

- **Version bump lives in two places that must match**:
  `sdks/python/pyproject.toml` (`version`) and
  `sdks/python/imagen_sdk/__init__.py` (`__version__`, which `imagen --version`
  reads). A new backward-compatible command/feature is a **minor** bump.
- **Nothing publishes on merge.** Releases are gated on prefixed tags:
  `python-v*` → PyPI, `cli-v*` → binaries, `node-v*` → npm. Go has no publish
  workflow — it's `go get` from an `sdks/go/vX.Y.Z` tag. Full process (including
  PyPI Trusted-Publishing setup) in [docs/RELEASING.md](docs/RELEASING.md).

## Git rules (hard)

- **Never push to `master`.** All changes go through a PR (`gh pr create --base master`).
- Branch off master with its own upstream; don't create branches that track
  `origin/master`.
- Don't commit unless asked. No secrets in tracked files.
