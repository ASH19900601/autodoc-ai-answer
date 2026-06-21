"""Answer router: auto-detect whether to use simple or worksheet strategy.

- ``simple``: numbered "1. ____" style questions (inline blanks / short
  answers appended). Fast and deterministic locating.
- ``worksheet``: LLM structure-aware mode for real worksheets (lettered
  sub-parts, blank-paragraph answers, True/False tick tables). docx only.

``auto`` inspects the document and picks the right strategy.
"""
from __future__ import annotations

import re
from typing import Optional, Tuple

from .formats import detect_format
from .llm import LLMClient
from .models import DocFormat, EditResult

_LETTERED_RE = re.compile(r"^\s*\(?[a-zA-Z]\)\s")
_MARKS_RE = re.compile(r"\[\d+\]\s*$")
_OPTION_RE = re.compile(r"^\s*[A-Da-d][.、)）]\s*\S")


def choose_mode(path: str) -> str:
    """Return 'simple' or 'worksheet' for the given document."""
    fmt = detect_format(path)
    if fmt != DocFormat.docx:
        return "simple"  # worksheet mode only supports docx for now

    from .backends import docx_backend

    structure = docx_backend.extract_structure(path)

    # Strong signal: tick-box / answer tables => worksheet.
    if structure["tables"]:
        return "worksheet"

    texts = [p["text"] for p in structure["paragraphs"]]
    lettered = sum(1 for t in texts if _LETTERED_RE.match(t))
    marks = sum(1 for t in texts if _MARKS_RE.search(t))
    options = sum(1 for t in texts if _OPTION_RE.match(t))

    simple_qs = docx_backend.parse_questions(path)
    simple_fill = sum(1 for q in simple_qs if q.qtype.value == "fill_blank")

    # Multiple-choice options present => structure-aware worksheet mode.
    if options >= 2:
        return "worksheet"
    # Lettered sub-parts or mark annotations => worksheet.
    if lettered >= 2 or marks >= 2:
        return "worksheet"
    # Clear numbered fill-in-the-blank worksheet with no worksheet signals.
    if simple_fill >= 1 and lettered == 0 and marks == 0:
        return "simple"
    # Nothing matched the simple pattern => let the LLM handle the structure.
    if not simple_qs:
        return "worksheet"
    return "simple"


def answer(
    path: str,
    client: LLMClient,
    mode: str = "auto",
    output: Optional[str] = None,
) -> EditResult:
    resolved = choose_mode(path) if mode == "auto" else mode
    if resolved == "worksheet":
        from .worksheet import answer_worksheet

        result = answer_worksheet(path, client, output=output)
    else:
        from .agent import answer_document

        result = answer_document(path, client, output=output)
    result.mode = resolved
    return result
