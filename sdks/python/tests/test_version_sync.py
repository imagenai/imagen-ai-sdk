"""The published package version and the runtime __version__ must never drift."""

import re
from pathlib import Path

from imagen_sdk import __version__


def test_version_matches_pyproject():
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    match = re.search(r'^version = "([^"]+)"', pyproject.read_text(), re.MULTILINE)
    assert match, "version not found in pyproject.toml"
    assert __version__ == match.group(1)
