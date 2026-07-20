# `imagen` CLI

A standalone command-line tool for the Imagen AI photo-editing API. It wraps the
core editing workflows and is built to be driven by **both humans and AI agents**:
every command supports `--json`, uses stable exit codes, and never prompts
interactively. (A few low-level SDK operations aren't exposed as commands — see
the SDK for those.)

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
> `imagen` command tracking your live source (no rebuild needed) — this is what
> the test suite uses.
>
> **Rebuilding the standalone binary?** The binary is compiled from the SDK
> source, so it only reflects changes after a rebuild. Run the single build
> script (same one CI uses, so local and released binaries match):
>
> ```bash
> pip install pyinstaller
> sh sdks/python/packaging/build.sh   # -> sdks/python/dist/imagen
> ```
>
> Released binaries are rebuilt automatically by CI on every `cli-v*` tag.

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
| `imagen skill` | Print or install the agent skill that teaches an AI agent to drive this CLI |

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
- Supported RAW: `.dng .nef .cr2 .arw .nrw .crw .orf .raw .rw2 .raf .ptx .pef .rwl .srw .cr3 .3fr .fff .srf .sr2`
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
# Success JSON goes to stdout; error JSON goes to stderr — capture them separately.
if imagen --json edit ./raws --profile 328 >result.json 2>error.json; then
  jq -r '.downloaded_files[]' result.json
else
  jq -r '.message' error.json >&2   # error detail is on stderr
fi
```

---

## For AI agents

The CLI ships an **agent skill** — a `SKILL.md` with `name`/`description`
frontmatter (`skills/imagen-cli/SKILL.md`) — that teaches an agent to drive this
CLI: always use `--json`, check exit codes, and discover capabilities via
`--help` rather than hardcoding commands. Claude Code and OpenAI Codex use the
**same skill format**, so one skill serves both agents.

`imagen skill` makes it self-bootstrapping — no repo checkout needed, since the
skill text is embedded in the binary:

```bash
imagen skill                        # print the skill to stdout
imagen skill --codex                # identical text (flags only pick install dir)
imagen --json skill                 # {"format": "...", "content": "..."}  (--json is global, goes first)

# Install it where the agent auto-discovers skills by their frontmatter:
imagen skill --claude --install     # -> ~/.claude/skills/imagen-cli/SKILL.md
imagen skill --codex  --install     # -> ~/.codex/skills/imagen-cli/SKILL.md
```

`--claude` / `--codex` only choose the **install location** — the skill content
is identical. To feed it into an agent that reads instructions from stdin/context
instead of a skills dir, just pipe the printed output. Install honors `--json` and
the standard exit codes, so failures are machine-readable too.
