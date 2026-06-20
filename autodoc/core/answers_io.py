"""Load answers from JSON into the shared Answer model."""
from __future__ import annotations

import json
from typing import List

from .models import Answer


def load_answers(path: str) -> List[Answer]:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return parse_answers(data)


def parse_answers(data) -> List[Answer]:
    """Accept either {id: text} or [{question_id, text}, ...]."""
    answers: List[Answer] = []
    if isinstance(data, dict):
        for qid, text in data.items():
            answers.append(Answer(question_id=str(qid), text=str(text)))
    elif isinstance(data, list):
        for item in data:
            answers.append(
                Answer(question_id=str(item["question_id"]), text=str(item["text"]))
            )
    else:
        raise ValueError("answers must be a JSON object or list")
    return answers
