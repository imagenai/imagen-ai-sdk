"""The published package version and the runtime __version__ must never drift."""

import re
from pathlib import Path

from imagen_sdk import __version__


def test_version_matches_pyproject():
    text = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text()
    # tomllib needs Python 3.11+, but the package supports 3.7+ — scope the
    # regex to the [project] table instead of parsing the whole file.
    project = re.search(r"(?ms)^\[project\]$(.*?)(?=^\[|\Z)", text)
    assert project, "[project] table not found in pyproject.toml"
    match = re.search(r'^version = "([^"]+)"', project.group(1), re.MULTILINE)
    assert match, "version not found in [project] table"
    assert __version__ == match.group(1)
