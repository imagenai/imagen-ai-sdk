"""
Internal typing stubs shared by the ImagenClient feature mixins.

At runtime this class is intentionally empty — the real implementations live on
``ImagenClient`` in ``imagen_sdk.py``. The declarations below exist only for static
type checking so that the feature mixins can reference the core client internals
(``_make_request``, ``_unwrap``, upload helpers, etc.) without mypy errors.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar

from pydantic import BaseModel

from .exceptions import ImagenError
from .models import FileUploadInfo, UploadSummary

_ModelT = TypeVar("_ModelT", bound=BaseModel)


class _CoreClientMixin:
    """Declares core client internals that feature mixins rely on (type-check only)."""

    if TYPE_CHECKING:
        _logger: logging.Logger
        base_url: str

        async def _make_request(self, method: str, endpoint: str, **kwargs: Any) -> dict[str, Any]: ...

        @staticmethod
        def _unwrap(payload: Any) -> Any: ...

        def _parse_model(
            self,
            payload: Any,
            model: type[_ModelT],
            what: str,
            error_type: type[ImagenError] = ImagenError,
        ) -> _ModelT: ...

        async def _prepare_upload_infos(
            self, image_paths: list[str | Path], calculate_md5: bool
        ) -> tuple[list[FileUploadInfo], list[Path]]: ...

        async def _run_concurrent_uploads(
            self,
            valid_paths: list[Path],
            upload_links_map: dict[str, str],
            max_concurrent: int,
            progress_callback: Callable[[int, int, str], None] | None = None,
        ) -> UploadSummary: ...

        @staticmethod
        async def _upload_to_s3(file_path: Path, upload_url: str) -> None: ...
