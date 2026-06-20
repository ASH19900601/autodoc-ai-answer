"""Format detection helpers (no document-library imports here)."""
from __future__ import annotations

import os

from .models import DocFormat

_EXT_MAP = {
    ".docx": DocFormat.docx,
    ".xlsx": DocFormat.xlsx,
    ".pptx": DocFormat.pptx,
    ".pdf": DocFormat.pdf,
    ".txt": DocFormat.txt,
    ".md": DocFormat.md,
    ".markdown": DocFormat.md,
}


def detect_format(path: str) -> DocFormat:
    ext = os.path.splitext(path)[1].lower()
    if ext not in _EXT_MAP:
        raise ValueError(
            f"Unsupported file extension: {ext!r}. "
            f"Supported: {', '.join(sorted(_EXT_MAP))}"
        )
    return _EXT_MAP[ext]


def supported_extensions() -> list:
    return sorted(_EXT_MAP)
