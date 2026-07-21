---
name: imagen-cli
description: "Use whenever an agent or user needs to edit, cull, or process photos with Imagen AI from the command line. Triggers on: 'edit my photos', 'run imagen', 'use the imagen CLI', 'AI edit these RAW/JPEG files', 'batch process wedding/portrait/real-estate photos', 'list my imagen profiles/projects', 'enhance an edited image', 'image-to-image edit'. The `imagen` CLI is a single self-contained binary (no Python required) that wraps the core Imagen AI editing workflows. Prefer it over hand-writing SDK code."
---

# Imagen CLI (agent-native)

`imagen` is a standalone binary wrapping the core Imagen AI editing workflows. It
is built to be driven by agents: non-interactive, `--json` output, stable exit
codes, and fully self-describing via `--help`. **You do not need to memorize the
command surface — discover it at runtime.** (A few low-level SDK operations aren't
exposed as commands — if `imagen <cmd> --help` doesn't list what you need, use the
SDK directly.)

## First: make sure it's installed

```bash
imagen --version || curl -fsSL https://raw.githubusercontent.com/imagenai/imagen-ai-sdk/master/sdks/python/packaging/install.sh | sh
```

No Python is required — the binary bundles its own runtime.

## Golden rules for agents

1. **Always pass `--json`** for anything you parse. Output is a single JSON
   document on stdout. Human tables are only for interactive users.
2. **Check the exit code**: `0` success, `2` auth/config problem (bad or missing
   key), `1` any other failure. In `--json` mode, failures print
   `{"error": "...", "message": "..."}` on stderr.
3. **Discover, don't guess.** Run `imagen --help` and `imagen <command> --help`
   to see every command and flag. New capabilities appear here automatically.
4. **Never invent flags.** If unsure, read `--help`.

## Authentication

API key resolution order: `--api-key` > `IMAGEN_API_KEY` env var > `~/.imagen/config.json`.

```bash
imagen config --api-key <KEY>       # persist it once
imagen config --profile <KEY>       # optional default profile
```

## The command surface (run `--help` for the source of truth)

| Command | Purpose |
|---------|---------|
| `imagen profiles` | List editing profiles → `profile_key` for `edit` |
| `imagen projects` | List projects (`--size`, `--page`) |
| `imagen edit FOLDER --profile K` | Full workflow: create → upload → edit → download |
| `imagen enhance PROJECT FILE --tool-id T` | Apply an AI quick tool to an edited image |
| `imagen i2i FOLDER` | Image-to-image editing workflow |
| `imagen sky-templates` | Sky replacement template ids |
| `imagen ai-tools PROJECT` | AI quick tools available for a project |
| `imagen config` | Show/set persisted defaults |
| `imagen skill` | Print or install this skill (`--claude` / `--codex`, `--install`) |

## Editing workflow

```bash
# 1. find a profile key
imagen --json profiles

# 2. edit a folder (downloads results by default)
imagen --json edit ./raws --profile 328 --type wedding --crop --smooth-skin --out ./edited

# with export to final JPEGs
imagen --json edit ./raws --profile 328 --export
```

`edit` accepts a folder or a single file. Edit-option flags map 1:1 to the SDK
`EditOptions` (`--crop`, `--straighten`, `--hdr-merge`, `--portrait-crop`,
`--smooth-skin`, `--subject-mask`, `--headshot-crop`, `--perspective-correction`,
`--sky-replacement`, `--sky-template-id`, `--window-pull`, `--crop-aspect-ratio`).
Only pass the flags you want on — unset flags are left unset, not forced off.

## Hard rules about input files

- **RAW and JPEG cannot be in the same project.** If a folder mixes them, `edit`
  fails with `error: input`. Split into a RAW-only run and a JPEG-only run, each
  with a matching profile (RAW profiles can't process JPEGs and vice versa).
- The folder scan is **top-level only** — subdirectories (e.g. a previous
  `edited/` output) are ignored.
- Supported RAW: `.dng .nef .cr2 .arw .nrw .crw .orf .raw .rw2 .raf .ptx .pef .rwl .srw .cr3 .3fr .fff .srf .sr2`
- Supported JPEG: `.jpg .jpeg`. Other formats (HEIC, etc.) are silently skipped.

## Photography types (`--type`)

`no_type other portraits wedding real_estate landscape_nature events family_newborn boudoir sports school`
(case-insensitive). Passing the right type improves AI quality.

## Tips

- For long edits, the CLI blocks until editing completes; run it directly so the
  user sees progress rather than burying it in a subagent.
- To wire Imagen into a script, `--json` + exit codes are all you need — no SDK
  import required.
