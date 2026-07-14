# `imagen` CLI

A standalone command-line tool for the Imagen AI photo-editing API. It wraps the
full API surface and is built to be driven by **both humans and AI agents**:
every command supports `--json`, uses stable exit codes, and never prompts
interactively.

**No Python required** — the CLI ships as a single self-contained binary.

---

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/imagenai/imagen-ai-sdk/master/sdks/python/packaging/install.sh | sh
```

The installer downloads the right binary for your platform (macOS arm64/x64,
Linux x64/arm64) into `~/.local/bin`. On Windows, download `imagen-windows-x64.exe`
from the [latest release](https://github.com/imagenai/imagen-ai-sdk/releases/latest).

Verify:

```bash
imagen --version
```

> **Developing from source?** `pip install -e sdks/python` also installs the
> `imagen` command (this is what the test suite uses).

---

## Authentication

The CLI looks for your API key in this order:

1. `--api-key <key>` flag
2. `IMAGEN_API_KEY` environment variable
3. `~/.imagen/config.json` (written by `imagen config`)

Set it once and forget it:

```bash
imagen config --api-key <YOUR_KEY>
imagen config --profile 328        # optional default editing profile
imagen config                      # show current config (key is masked)
```

---

## Commands

Run `imagen --help` or `imagen <command> --help` at any time — the CLI is
self-documenting.

| Command | What it does |
|---------|--------------|
| `imagen profiles` | List your editing profiles (each has a `profile_key`) |
| `imagen projects` | List projects in your account (`--size`, `--page`) |
| `imagen edit FOLDER --profile K` | Full workflow: create project → upload → edit → download |
| `imagen enhance PROJECT FILE --tool-id T` | Apply an AI quick tool to an already-edited image |
| `imagen i2i FOLDER` | Run the image-to-image editing workflow |
| `imagen sky-templates` | List sky-replacement template ids |
| `imagen ai-tools PROJECT` | List AI quick tools available for a project |
| `imagen config` | Show or set persisted defaults |

### Global options

| Option | Meaning |
|--------|---------|
| `--json` | Emit a single machine-readable JSON document on stdout |
| `--api-key TEXT` | Override the API key for this invocation |
| `--base-url TEXT` | Override the API base URL |
| `-V, --version` | Print the version |

Global options go **before** the command: `imagen --json profiles`.

---

## Editing photos

```bash
# 1. Find a profile key
imagen profiles

# 2. Edit a folder of RAW files with profile 328, as a wedding, with crop + skin smoothing
imagen edit ./raws --profile 328 --type wedding --crop --smooth-skin --out ./edited

# Also export final JPEGs
imagen edit ./raws --profile 328 --export
```

`edit` accepts a folder or a single file. Results download by default
(`--no-download` to skip). Editing options map 1:1 to the API:

`--crop` · `--straighten` · `--hdr-merge` · `--portrait-crop` · `--smooth-skin`
· `--subject-mask` · `--headshot-crop` · `--perspective-correction`
· `--sky-replacement` · `--sky-template-id N` · `--window-pull`
· `--crop-aspect-ratio 2X3|4X5|5X7`

Only pass the flags you want enabled; unset flags are left untouched.

### Photography types (`--type`)

`no_type`, `other`, `portraits`, `wedding`, `real_estate`, `landscape_nature`,
`events`, `family_newborn`, `boudoir`, `sports`, `school` (case-insensitive).
Passing the right type improves AI quality.

### File-type rules

- **RAW and JPEG cannot be mixed in one project.** If a folder contains both,
  `edit` fails — run RAW-only and JPEG-only folders separately, each with a
  matching profile (RAW profiles can't process JPEGs and vice versa).
- Only the **top level** of the folder is scanned; subfolders (e.g. a previous
  `edited/` output) are ignored.
- Supported RAW: `.dng .nef .cr2 .arw .nrw .crw .orf .raw .rw2 .raf .ptx .pef .rwl .srw .cr3 .3fr .fff`
- Supported JPEG: `.jpg .jpeg`. Other formats (HEIC, etc.) are skipped.

---

## JSON output and exit codes (for scripts and agents)

Add `--json` to get a single JSON document on stdout. On failure, the CLI prints
`{"error": "...", "message": "..."}` on **stderr** and returns a non-zero exit code:

| Exit code | Meaning |
|-----------|---------|
| `0` | Success |
| `2` | Authentication / configuration problem (missing or invalid key, missing profile) |
| `1` | Any other failure (API error, bad input, mixed RAW/JPEG, etc.) |

Example:

```bash
imagen --json profiles | jq '.[0].profile_key'
```

```bash
if imagen --json edit ./raws --profile 328 > result.json; then
  jq -r '.downloaded_files[]' result.json
else
  jq -r '.message' result.json >&2   # error detail on stderr
fi
```

---

## For AI agents

An installable skill (`skills/imagen-cli/SKILL.md`) teaches agents to drive this
CLI: always use `--json`, check exit codes, and discover capabilities via
`--help` rather than hardcoding commands.
