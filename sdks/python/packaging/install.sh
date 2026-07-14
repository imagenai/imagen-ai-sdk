#!/bin/sh
# Install the `imagen` CLI: downloads the standalone binary for this platform
# from the latest GitHub release. No Python required.
#
#   curl -fsSL https://raw.githubusercontent.com/imagenai/imagen-ai-sdk/master/sdks/python/packaging/install.sh | sh
#
# Env overrides: IMAGEN_INSTALL_DIR (default: ~/.local/bin), IMAGEN_VERSION (default: latest).
set -eu

REPO="imagenai/imagen-ai-sdk"
INSTALL_DIR="${IMAGEN_INSTALL_DIR:-$HOME/.local/bin}"

os="$(uname -s)"
arch="$(uname -m)"
case "$os" in
  Darwin) plat="macos" ;;
  Linux)  plat="linux" ;;
  *) echo "Unsupported OS: $os (Windows: download imagen-windows-x64.exe from the release)" >&2; exit 1 ;;
esac
case "$arch" in
  x86_64|amd64) a="x64" ;;
  arm64|aarch64) a="arm64" ;;
  *) echo "Unsupported architecture: $arch" >&2; exit 1 ;;
esac

# Intel macOS has no prebuilt binary (no Blacksmith Intel-macOS runner).
if [ "$plat" = "macos" ] && [ "$a" = "x64" ]; then
  echo "Intel macOS has no prebuilt binary. Install from source instead:" >&2
  echo "  pip install imagen-ai-sdk    # provides the 'imagen' command" >&2
  exit 1
fi

asset="imagen-${plat}-${a}"
if [ "${IMAGEN_VERSION:-latest}" = "latest" ]; then
  url="https://github.com/${REPO}/releases/latest/download/${asset}"
else
  url="https://github.com/${REPO}/releases/download/${IMAGEN_VERSION}/${asset}"
fi

echo "Installing imagen (${asset}) -> ${INSTALL_DIR}/imagen"
mkdir -p "$INSTALL_DIR"
if ! curl -fsSL "$url" -o "$INSTALL_DIR/imagen"; then
  echo "Download failed: $url" >&2
  echo "Check available assets at https://github.com/${REPO}/releases" >&2
  exit 1
fi
chmod +x "$INSTALL_DIR/imagen"

if ! command -v imagen >/dev/null 2>&1; then
  echo "Installed, but $INSTALL_DIR is not on your PATH. Add it:"
  echo "  export PATH=\"$INSTALL_DIR:\$PATH\""
fi
echo "Done. Run: imagen --help"
