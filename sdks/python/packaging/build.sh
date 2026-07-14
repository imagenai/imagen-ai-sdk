#!/bin/sh
# Build the standalone `imagen` binary from the current SDK source with PyInstaller.
# Single source of truth for the build — CI (release-cli.yml) and local devs both
# call this, so a locally built binary matches what CI ships.
#
# Usage:  sh packaging/build.sh        (run from sdks/python, or anywhere)
# Output: sdks/python/dist/imagen  (or dist/imagen.exe on Windows)
#
# Requires PyInstaller: pip install pyinstaller
set -eu

# Resolve to sdks/python regardless of caller's cwd.
cd "$(dirname "$0")/.."

if ! python -c "import PyInstaller" >/dev/null 2>&1; then
  echo "PyInstaller not found. Install it: pip install pyinstaller" >&2
  exit 1
fi

python -m PyInstaller \
  --onefile \
  --name imagen \
  --clean --noconfirm \
  --paths . \
  --collect-submodules imagen_sdk \
  packaging/imagen_entry.py

echo "Built: $(pwd)/dist/imagen"
