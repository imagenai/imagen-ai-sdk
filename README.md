# Imagen AI SDK

Official SDKs and command-line tools for integrating [Imagen AI](https://imagen-ai.com)
photo editing into applications, automation workflows, and backend services.

Imagen applies your trained editing style — an **AI Profile** — to whole batches of
photos: upload RAW or JPEG images, apply a profile, monitor the editing job, and
download Lightroom-compatible **XMP** sidecars or exported JPEGs. Your original
files are never modified.

[![CI](https://github.com/imagenai/imagen-ai-sdk/actions/workflows/ci.yml/badge.svg)](https://github.com/imagenai/imagen-ai-sdk/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/imagen-ai-sdk?label=pypi)](https://pypi.org/project/imagen-ai-sdk/)
[![npm](https://img.shields.io/npm/v/imagen-ai-sdk?label=npm)](https://www.npmjs.com/package/imagen-ai-sdk)
[![Go Reference](https://pkg.go.dev/badge/github.com/imagenai/imagen-ai-sdk/sdks/go.svg)](https://pkg.go.dev/github.com/imagenai/imagen-ai-sdk/sdks/go)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](#license)

## Choose your interface

| Interface | Install | Best for |
|-----------|---------|----------|
| [Python](sdks/python/README.md) | `pip install imagen-ai-sdk` | Scripts, automation, and Python services |
| [Node.js / TypeScript](sdks/node/README.md) | `npm install imagen-ai-sdk` | JavaScript and TypeScript applications |
| [Go](sdks/go/README.md) | `go get github.com/imagenai/imagen-ai-sdk/sdks/go` | Compiled backend services |
| [CLI](docs/CLI.md) | [install script](docs/CLI.md#install) | Shell scripts, CI, and agent workflows |

All four target the same API and the shared [workflow contract](docs/WORKFLOWS.md).

## Prerequisites

- An **Imagen account with API access.** Sign up at [imagen-ai.com](https://imagen-ai.com),
  then request an API key via [support.imagen-ai.com](https://support.imagen-ai.com/hc).
- An **API key**, supplied to the SDK/CLI via the `IMAGEN_API_KEY` environment
  variable (the SDKs also accept it directly in code).
- A supported runtime for your chosen interface:

  | Interface | Runtime |
  |-----------|---------|
  | Python | Python ≥ 3.7 |
  | Node.js / TypeScript | Node.js ≥ 18 |
  | Go | Go ≥ 1.22 |
  | CLI | none — self-contained binary |

- **Input files:** RAW (`.dng`, `.nef`, `.cr2`, `.arw`, …) or JPEG (`.jpg`,
  `.jpeg`). A single project must be **all RAW or all JPEG — never mixed**, and the
  profile must match the file type.

### Authentication

```bash
export IMAGEN_API_KEY="your-api-key"
```

## Quick start

The smallest end-to-end run in Python — `quick_edit` creates a project, uploads,
edits, and downloads in one call:

```python
import asyncio
from imagen_sdk import quick_edit, EditOptions

async def main():
    result = await quick_edit(
        api_key="your-api-key",
        profile_key=5700,                       # your AI Profile, from the Imagen app
        image_paths=["photo1.nef", "photo2.dng"],
        edit_options=EditOptions(crop=True, straighten=True),
        download=True,                          # add export=True to also render JPEGs
    )
    print(f"Done — {len(result.downloaded_files)} edited photos")

asyncio.run(main())
```

For step-by-step control (progress callbacks, manual create/upload/edit/download)
and the Node, Go, and CLI equivalents, see each interface's guide under
[Documentation](#documentation).

## How it works

```text
Create project
      ↓
Upload photos        (RAW or JPEG — one type per project)
      ↓
Start AI editing     (apply an AI Profile)
      ↓
Wait for completion
      ↓
Download XMP sidecars   — or export to JPEG
```

- **Editing produces XMP sidecars** — Lightroom/Photoshop-compatible edit
  instructions. Your original images are never modified.
- **Export is optional** — render the edited images to delivery-ready JPEGs.
- **Image-to-Image (I2I)** projects are a separate family with their own upload
  and completion model (no status polling — results arrive via callback or by
  polling for download links).

Full behavioral details are in the [workflow guide](docs/WORKFLOWS.md).

## Common workflows

Each is documented language-neutrally in [`docs/WORKFLOWS.md`](docs/WORKFLOWS.md):

- **Standard AI editing (Workflow A)** — apply a profile, download XMP sidecars.
- **Export to JPEG (Workflow B)** — render edited images to final JPEGs.
- **AI Enhancement & Copilot (Workflow C)** — per-image quick tools and
  natural-language edits, then finalize (upscaled deliverables).
- **Image-to-Image / I2I (Workflow D)** — a distinct project family with its own
  upload routing and completion flow.
- **Project management (Workflow E)** — list, fetch, and paginate projects.

## Command-line interface

Reach for the `imagen` CLI when you want photo editing from a **shell, a CI
pipeline, or an AI agent** rather than embedding an SDK. It needs no runtime
(self-contained binary), supports `--json` on every command, and uses stable exit
codes (`0` success, `2` auth/config, `1` other error).

```bash
curl -fsSL https://raw.githubusercontent.com/imagenai/imagen-ai-sdk/master/sdks/python/packaging/install.sh | sh
imagen edit ./raws --profile 5700 --type wedding --crop
```

Full reference: [`docs/CLI.md`](docs/CLI.md). AI agents can self-install the CLI
skill with `imagen skill --claude --install` or `imagen skill --codex --install`
(see [`skills/imagen-cli/SKILL.md`](skills/imagen-cli/SKILL.md)).

## Documentation

- [Python SDK guide](sdks/python/README.md)
- [Node.js / TypeScript SDK guide](sdks/node/README.md)
- [Go SDK guide](sdks/go/README.md)
- [CLI guide](docs/CLI.md)
- [Workflow guide](docs/WORKFLOWS.md) — the language-neutral behavioral contract
- [OpenAPI specification](spec/openapi.yaml)
- [Contributing with a coding agent](AGENTS.md) · [Releasing](docs/RELEASING.md)

## Repository structure

```text
sdks/python/   Python SDK (PyPI) — also builds the `imagen` CLI
sdks/node/     Node / TypeScript SDK (npm)
sdks/go/       Go SDK (go get; no central registry)
docs/          WORKFLOWS.md, CLI.md, RELEASING.md
spec/          OpenAPI contract (openapi.yaml)
```

Each SDK versions and **releases independently** (Python and Node to their
registries, Go via a `sdks/go/vX.Y.Z` tag). They target the same API and shared
[workflow contract](docs/WORKFLOWS.md), so newer capabilities may land in one
language before another — check each SDK's own README for its current feature set.
Release mechanics are in [`docs/RELEASING.md`](docs/RELEASING.md).

## Support and contributing

- **Bugs and feature requests:** open a
  [GitHub issue](https://github.com/imagenai/imagen-ai-sdk/issues).
- **Account, API, or billing help:** [support.imagen-ai.com](https://support.imagen-ai.com/hc).
- **Contributing:** [`AGENTS.md`](AGENTS.md) documents the build/test/lint
  commands, the CLI design contract, versioning, and the branch/PR rules; release
  steps are in [`docs/RELEASING.md`](docs/RELEASING.md).

## License

MIT — see [LICENSE](LICENSE). Also declared in each SDK's package metadata
(`sdks/python/pyproject.toml`, `sdks/node/package.json`).
