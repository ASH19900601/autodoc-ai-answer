"""Parse dispatcher: route a document to its format-specific backend."""
from __future__ import annotations

from .formats import detect_format
from .models import DocFormat, ParseResult


def parse_document(path: str) -> ParseResult:
    fmt = detect_format(path)
    if fmt == DocFormat.docx:
        from .backends import docx_backend

        questions = docx_backend.parse_questions(path)
    elif fmt in (DocFormat.txt, DocFormat.md):
        from .backends import text_backend

        questions = text_backend.parse_questions(path, fmt)
    elif fmt == DocFormat.pdf:
        from .backends import pdf_backend

        questions = pdf_backend.parse_questions(path)
    elif fmt == DocFormat.xlsx:
        from .backends import xlsx_backend

        questions = xlsx_backend.parse_questions(path)
    elif fmt == DocFormat.pptx:
        from .backends import pptx_backend

        questions = pptx_backend.parse_questions(path)
    else:
        raise NotImplementedError(f"Parsing for {fmt.value!r} is not implemented yet.")
    return ParseResult(path=path, format=fmt, questions=questions)
