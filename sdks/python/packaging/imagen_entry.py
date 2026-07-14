"""PyInstaller entry point. Uses an absolute import so the package's own
relative imports resolve when frozen into a single binary."""

from imagen_sdk.cli import main

if __name__ == "__main__":
    main()
