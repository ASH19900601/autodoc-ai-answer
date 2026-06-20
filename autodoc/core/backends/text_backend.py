"""Plain text / Markdown backend.

Questions are lines matching the question pattern. We edit the file
in-place, touching only the matched lines (every other byte/line is
preserved exactly), so formatting/layout is unchanged.
"""
from __future__ import annotations

import json
import re
from typing import Dict, List

from ..models import Anchor, Answer, DocFormat, EditResult, Question, QuestionType

_QUESTION_RE = re.compile(r"^\s*(\d+)\s*[.、)）]\s*(\S.*)$")
_BLANK_RE = re.compile(r"[_＿]{2,}")


def _read_lines(path: str) -> List[str]:
    with open(path, "r", encoding="utf-8", newline="") as fh:
        content = fh.read()
    # keep line endings via splitlines(keepends=True)
    return content.splitlines(keepends=True)


def parse_questions(path: str, fmt: DocFormat) -> List[Question]:
    lines = _read_lines(path)
    questions: List[Question] = []
    for idx, raw in enumerate(lines):
        line = raw.rstrip("\r\n")
        m = _QUESTION_RE.match(line)
        if not m:
            continue
        number = m.group(1)
        blank = _BLANK_RE.search(line)
        mode = "replace_blank" if blank else "append"
        qtype = QuestionType.fill_blank if blank else QuestionType.short_answer
        locator = json.dumps({"line_index": idx, "mode": mode})
        questions.append(
            Question(
                id=f"q{number}",
                number=number,
                text=line.strip(),
                qtype=qtype,
                anchor=Anchor(format=fmt, locator=locator, detail={"mode": mode}),
            )
        )
    return questions


def write_answers(
    path: str,
    answers: List[Answer],
    questions: List[Question],
    fmt: DocFormat,
    output: str = None,
) -> EditResult:
    lines = _read_lines(path)
    by_id: Dict[str, Answer] = {a.question_id: a for a in answers}
    written = 0

    for q in questions:
        ans = by_id.get(q.id)
        if ans is None:
            continue
        loc = json.loads(q.anchor.locator)
        i = loc["line_index"]
        raw = lines[i]
        # separate trailing newline so we don't move it
        newline = ""
        body = raw
        for ending in ("\r\n", "\n", "\r"):
            if raw.endswith(ending):
                newline = ending
                body = raw[: -len(ending)]
                break
        if loc["mode"] == "replace_blank" and _BLANK_RE.search(body):
            body = _BLANK_RE.sub(ans.text, body, count=1)
        else:
            sep = "" if body.endswith((" ", "：", ":")) else " "
            body = body + sep + ans.text
        lines[i] = body + newline
        written += 1

    target = output or path
    with open(target, "w", encoding="utf-8", newline="") as fh:
        fh.write("".join(lines))
    return EditResult(
        path=target, format=fmt, answers_written=written, in_place=(target == path)
    )
