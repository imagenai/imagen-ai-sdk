# Imagen AI SDK

Multi-language SDK monorepo for the [Imagen AI](https://imagen-ai.com) photo-editing API.

| Language | Location | Install |
|----------|----------|---------|
| Python | [`sdks/python/`](sdks/python/) | `pip install imagen-ai-sdk` |
| Node / TypeScript | [`sdks/node/`](sdks/node/) | `npm install imagen-ai-sdk` |
| Go | [`sdks/go/`](sdks/go/) | `go get github.com/imagenai/imagen-ai-sdk/sdks/go` |

See each SDK's own README for full usage and examples.

## Command-line tool

Prefer the terminal (or driving Imagen from an AI agent)? The **`imagen` CLI** is
a single self-contained binary — no Python required — that wraps the full API
with `--json` output and stable exit codes. See [`docs/CLI.md`](docs/CLI.md).

```bash
curl -fsSL https://raw.githubusercontent.com/imagenai/imagen-ai-sdk/master/sdks/python/packaging/install.sh | sh
imagen edit ./raws --profile 328 --type wedding --crop
```

## Repository layout

```
sdks/python/     Python SDK (published to PyPI)
sdks/node/       Node / TypeScript SDK (published to npm)
sdks/go/         Go SDK (consumed directly via `go get`; no central registry)
docs/            Shared docs — incl. WORKFLOWS.md, the language-neutral
                 behavioral contract every SDK implements
spec/            Reference OpenAPI 3.1 contract (spec/openapi.yaml)
```

Each SDK is self-contained with its own version and bundled `LICENSE`. Python and
Node publish to their registries (PyPI, npm); Go has no central registry, so it is
imported straight from this repo — `go get github.com/imagenai/imagen-ai-sdk/sdks/go`,
with releases cut as `sdks/go/vX.Y.Z` tags.

The workflows every SDK implements (create → upload → edit → poll → download,
plus export, AI enhancement, and image-to-image) are defined language-neutrally in
[`docs/WORKFLOWS.md`](docs/WORKFLOWS.md).

## License

MIT — see [LICENSE](LICENSE). Each published package also bundles its own copy.
