# Imagen AI SDK

Multi-language SDK monorepo for the [Imagen AI](https://imagen-ai.com) photo-editing API.

| Language | Location | Install |
|----------|----------|---------|
| Python | [`sdks/python/`](sdks/python/) | `pip install imagen-ai-sdk` |
| Node / TypeScript | [`sdks/node/`](sdks/node/) | `npm install imagen-ai-sdk` |

See each SDK's own README for full usage and examples.

## Repository layout

```
sdks/python/     Python SDK (published to PyPI)
sdks/node/       Node / TypeScript SDK (published to npm)
docs/            Shared docs — incl. WORKFLOWS.md, the language-neutral
                 behavioral contract every SDK implements
spec/            Reference OpenAPI 3.1 contract (spec/openapi.yaml)
```

Each SDK is self-contained and released independently to its own registry
(PyPI for Python, npm for Node, …) with its own version and bundled `LICENSE`.

The workflows every SDK implements (create → upload → edit → poll → download,
plus export, AI enhancement, and image-to-image) are defined language-neutrally in
[`docs/WORKFLOWS.md`](docs/WORKFLOWS.md).

## License

MIT — see [LICENSE](LICENSE). Each published package also bundles its own copy.
