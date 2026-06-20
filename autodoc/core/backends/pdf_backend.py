"""PDF backend.

Two supported, format-preserving strategies:

* **AcroForm fields** — fill existing text widgets in place. Page content
  streams and geometry are untouched; only field values change.
* **Text PDFs** — locate the question text and insert the answer next to it
  via an added text span. We only ADD content; existing text/layout stays.

True reflow editing of arbitrary/scanned PDFs is intentionally out of scope
and reported as unsupported rather than silently mangling the layout.
"""
from __future__ import annotations

import json
import re
from typing import Dict, List

import fitz  # PyMuPDF

from ..models import Anchor, Answer, DocFormat, EditResult, Question, QuestionType

_QUESTION_RE = re.compile(r"^\s*(\d+)\s*[.、)）]\s*(\S.*)$")
_BLANK_RE = re.compile(r"[_＿]{2,}")


def _form_fields(doc) -> List[tuple]:
    fields = []
    for pno in range(doc.page_count):
        page = doc[pno]
        for w in page.widgets() or []:
            if w.field_type_string in ("Text",):
                fields.append((pno, w.field_name))
    return fields


def parse_questions(path: str) -> List[Question]:
    doc = fitz.open(path)
    try:
        fields = _form_fields(doc)
        if fields:
            return _parse_form(fields)
        return _parse_text(doc)
    finally:
        doc.close()


def _parse_form(fields: List[tuple]) -> List[Question]:
    questions: List[Question] = []
    for i, (pno, name) in enumerate(fields, start=1):
        locator = json.dumps({"mode": "form_field", "field": name, "page": pno})
        questions.append(
            Question(
                id=name or f"field{i}",
                number=str(i),
                text=name or f"field{i}",
                qtype=QuestionType.fill_blank,
                anchor=Anchor(
                    format=DocFormat.pdf, locator=locator, page=pno,
                    detail={"mode": "form_field"},
                ),
            )
        )
    return questions


def _parse_text(doc) -> List[Question]:
    questions: List[Question] = []
    for pno in range(doc.page_count):
        page = doc[pno]
        for line in page.get_text("text").splitlines():
            m = _QUESTION_RE.match(line)
            if not m:
                continue
            number = m.group(1)
            blank = _BLANK_RE.search(line)
            qtype = QuestionType.fill_blank if blank else QuestionType.short_answer
            locator = json.dumps(
                {"mode": "text_insert", "page": pno, "search": line.strip()}
            )
            questions.append(
                Question(
                    id=f"q{number}",
                    number=number,
                    text=line.strip(),
                    qtype=qtype,
                    anchor=Anchor(
                        format=DocFormat.pdf, locator=locator, page=pno,
                        detail={"mode": "text_insert"},
                    ),
                )
            )
    return questions


def write_answers(
    path: str, answers: List[Answer], questions: List[Question], output: str = None
) -> EditResult:
    doc = fitz.open(path)
    by_id: Dict[str, Answer] = {a.question_id: a for a in answers}
    written = 0
    try:
        for q in questions:
            ans = by_id.get(q.id)
            if ans is None:
                continue
            loc = json.loads(q.anchor.locator)
            if loc["mode"] == "form_field":
                if _fill_field(doc, loc["field"], ans.text):
                    written += 1
            else:
                if _insert_text(doc, loc["page"], loc["search"], ans.text):
                    written += 1
        target = output or path
        if target == path:
            doc.saveIncr() if doc.can_save_incrementally() else doc.save(
                target, incremental=False
            )
        else:
            doc.save(target)
    finally:
        doc.close()
    return EditResult(
        path=(output or path),
        format=DocFormat.pdf,
        answers_written=written,
        in_place=(output is None or output == path),
    )


def _fill_field(doc, field_name: str, value: str) -> bool:
    for pno in range(doc.page_count):
        page = doc[pno]
        for w in page.widgets() or []:
            if w.field_name == field_name and w.field_type_string == "Text":
                w.field_value = value
                w.update()
                return True
    return False


def _insert_text(doc, pno: int, search: str, answer: str) -> bool:
    page = doc[pno]
    rects = page.search_for(search)
    if not rects:
        # fall back to searching just the blank-stripped question stem
        stem = _BLANK_RE.sub("", search).strip()
        if stem:
            rects = page.search_for(stem)
    if not rects:
        return False
    rect = rects[0]
    point = fitz.Point(rect.x1 + 4, rect.y1)  # just right of the matched text
    # "china-s" is PyMuPDF's built-in CJK font; it also covers Latin, so it
    # renders both Chinese and ASCII answers and stays extractable.
    page.insert_text(point, answer, fontsize=11, fontname="china-s")
    return True
