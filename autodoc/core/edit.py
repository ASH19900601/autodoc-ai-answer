"""Edit dispatcher: write answers back into a document in-place."""
from __future__ import annotations

from typing import List, Optional

from .formats import detect_format
from .models import Answer, DocFormat, EditResult, Question


def write_answers(
    path: str,
    answers: List[Answer],
    questions: List[Question],
    output: Optional[str] = None,
) -> EditResult:
    fmt = detect_format(path)
    if fmt == DocFormat.docx:
        from .backends import docx_backend

        return docx_backend.write_answers(path, answers, questions, output=output)
    if fmt in (DocFormat.txt, DocFormat.md):
        from .backends import text_backend

        return text_backend.write_answers(
            path, answers, questions, fmt, output=output
        )
    if fmt == DocFormat.pdf:
        from .backends import pdf_backend

        return pdf_backend.write_answers(path, answers, questions, output=output)
    if fmt == DocFormat.xlsx:
        from .backends import xlsx_backend

        return xlsx_backend.write_answers(path, answers, questions, output=output)
    if fmt == DocFormat.pptx:
        from .backends import pptx_backend

        return pptx_backend.write_answers(path, answers, questions, output=output)
    raise NotImplementedError(f"Editing for {fmt.value!r} is not implemented yet.")
