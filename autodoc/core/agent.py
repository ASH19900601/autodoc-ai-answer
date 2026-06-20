"""The answer pipeline: parse -> ask LLM -> write answers in-place.

This is the product's core flow and what the MCP ``answer_document`` tool
and the ``autodoc answer`` CLI command both call.
"""
from __future__ import annotations

from typing import Optional

from .edit import write_answers
from .llm import LLMClient, answer_questions
from .models import EditResult
from .parse import parse_document


def answer_document(
    path: str,
    client: LLMClient,
    output: Optional[str] = None,
) -> EditResult:
    questions = parse_document(path).questions
    answers = answer_questions(client, questions)
    return write_answers(path, answers, questions, output=output)
