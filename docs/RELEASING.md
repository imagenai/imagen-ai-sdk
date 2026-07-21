# Releasing

Each SDK releases independently, and **nothing publishes on merge**. Every release
is gated on a deliberate, prefixed git tag pushed to `master`, and every publish
job `needs: test`, so a failing suite blocks the upload (fails closed).

| What | Tag prefix | Workflow | Target |
|------|-----------|----------|--------|
| Python SDK | `python-v*` | `.github/workflows/release-python.yml` | PyPI (`imagen-ai-sdk`) |
| Standalone CLI binary | `cli-v*` | `.github/workflows/release-cli.yml` | GitHub Releases (macOS/Linux/Windows binaries) |
| Node SDK | `node-v*` | `.github/workflows/release-node.yml` | npm |

The Python package and the CLI binary are **built from the same `sdks/python`
source**, so they share one version. Keep them in sync: when you cut one, cut the
other at the same version.

The **Go SDK** has no publish workflow — it's consumed directly via `go get` from a
`sdks/go/vX.Y.Z` tag, so "releasing" it is just pushing that tag.

## Releasing the Python SDK (PyPI)

1. **Bump the version in both places** (they must match — `imagen --version` reads
   `__version__`):
   - `sdks/python/pyproject.toml` → `version = "X.Y.Z"`
   - `sdks/python/imagen_sdk/__init__.py` → `__version__ = "X.Y.Z"`

   Use semver: a new command / backward-compatible feature is a **minor** bump.

2. Merge that to `master` via PR (branch protection — never push to `master`).

3. Tag the merged commit and push the tag:
   ```bash
   git checkout master && git pull --ff-only origin master
   git tag -a python-vX.Y.Z -m "imagen-ai-sdk X.Y.Z — <summary>"
   git push origin python-vX.Y.Z
   ```

4. Watch the run: `gh run list --limit 5`. The `publish` job uploads to PyPI once
   `test` passes.

### PyPI auth: Trusted Publishing (one-time setup)

The `publish` job authenticates with **PyPI Trusted Publishing (OIDC)** — no stored
token, nothing on any developer's machine. What's authorized is the *workflow
identity*, not a computer.

If the publish step fails with `invalid-publisher` ("no corresponding publisher"),
the trusted publisher hasn't been registered yet. Register it once, on
[pypi.org](https://pypi.org) → project `imagen-ai-sdk` →
**Settings → Publishing → Add a trusted publisher (GitHub)**:

| Field | Value |
|-------|-------|
| Owner | `imagenai` |
| Repository name | `imagen-ai-sdk` |
| Workflow name | `release-python.yml` |
| Environment name | `pypi` |

(If the project didn't exist on PyPI yet, add a **pending** publisher from the
account level instead.) Once added, re-run the failed job — no re-tag needed:

```bash
gh run rerun <run-id> --failed
```

Verify: `pip index versions imagen-ai-sdk`, or check
`https://pypi.org/project/imagen-ai-sdk/`.

## Releasing the CLI binary

Same version, `cli-v*` tag:

```bash
git tag -a cli-vX.Y.Z -m "imagen CLI X.Y.Z — <summary>"
git push origin cli-vX.Y.Z
```

`release-cli.yml` rebuilds binaries for macOS arm64, Linux x64/arm64, and Windows
x64 (via `sdks/python/packaging/build.sh`, the same script contributors run
locally) and attaches them to a GitHub Release. `packaging/install.sh` (the
`curl | sh` installer) downloads them.

The CLI binary is not published to any package registry — GitHub Releases is its
only distribution channel. See [CLI.md](CLI.md) for install/usage.
