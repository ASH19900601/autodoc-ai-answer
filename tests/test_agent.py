"""Phase 3 tests: model-agnostic answer pipeline (no real API needed)."""
from __future__ import annotations

import json
from pathlib import Path

import docx
import pytest

from autodoc.core import llm as llm_mod
from autodoc.core.agent import answer_document
from autodoc.core.llm import (
    OpenAICompatClient,
    answer_questions,
    build_prompt,
    extract_json_object,
)
from autodoc.core.models import QuestionType
from autodoc.core.parse import parse_document


class FakeLLM:
    """Records the prompt and returns a canned JSON answer map."""

    def __init__(self, mapping):
        self.mapping = mapping
        self.last_user = None

    def complete(self, system: str, user: str) -> str:
        self.last_user = user
        return json.dumps(self.mapping, ensure_ascii=False)


def test_extract_json_plain():
    assert extract_json_object('{"q1": "北京"}') == {"q1": "北京"}


def test_extract_json_fenced():
    raw = "```json\n{\"q1\": \"北京\", \"q2\": \"H2O\"}\n```"
    assert extract_json_object(raw) == {"q1": "北京", "q2": "H2O"}


def test_extract_json_with_surrounding_text():
    raw = "好的，答案如下：{\"q1\": \"北京\"} 希望有帮助"
    assert extract_json_object(raw) == {"q1": "北京"}


def test_answer_questions_maps_ids(sample_docx: Path):
    questions = parse_document(str(sample_docx)).questions
    fake = FakeLLM({"q1": "北京", "q2": "H2O", "q3": "月球"})
    answers = answer_questions(fake, questions)
    ids = {a.question_id: a.text for a in answers}
    assert ids == {"q1": "北京", "q2": "H2O", "q3": "月球"}


def test_build_prompt_includes_questions(sample_docx: Path):
    questions = parse_document(str(sample_docx)).questions
    prompt = build_prompt(questions)
    assert "q1" in prompt and "首都" in prompt


def test_answer_document_end_to_end_in_place(sample_docx: Path):
    fake = FakeLLM({"q1": "北京", "q2": "H2O", "q3": "月球"})
    result = answer_document(str(sample_docx), fake)
    assert result.in_place is True
    assert result.answers_written == 3
    full = "\n".join(p.text for p in docx.Document(str(sample_docx)).paragraphs)
    assert "北京" in full and "H2O" in full and "月球" in full


def test_openai_compat_client_builds_request(monkeypatch):
    captured = {}

    class _Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": '{"q1": "北京"}'}}]}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return _Resp()

    monkeypatch.setattr(llm_mod.httpx, "post", fake_post)
    client = OpenAICompatClient(
        base_url="https://example.test/v1", model="my-model", api_key="sk-x"
    )
    out = client.complete("sys", "usr")
    assert out == '{"q1": "北京"}'
    assert captured["url"] == "https://example.test/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer sk-x"
    assert captured["json"]["model"] == "my-model"
    assert captured["json"]["messages"][0]["role"] == "system"
