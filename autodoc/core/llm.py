"""Model-agnostic LLM client (OpenAI-compatible chat completions).

Works with any endpoint that speaks the OpenAI ``/chat/completions``
contract: OpenAI, Anthropic-via-bridge, local servers, proxies, etc.
The client is a small Protocol so tests can inject a fake.
"""
from __future__ import annotations

import json
import os
import re
from typing import Dict, List, Protocol

import httpx

from .models import Answer, Question


class LLMClient(Protocol):
    def complete(self, system: str, user: str) -> str:  # pragma: no cover - interface
        ...


class OpenAICompatClient:
    def __init__(
        self,
        base_url: str = "",
        model: str = "",
        api_key: str = "",
        timeout: float = 120.0,
    ) -> None:
        self.base_url = (base_url or os.environ.get("ANTHROPIC_BASE_URL")
                         or os.environ.get("OPENAI_BASE_URL")
                         or "https://api.openai.com/v1").rstrip("/")
        self.model = model or os.environ.get("AUTODOC_MODEL") or "gpt-4o-mini"
        self.api_key = (api_key or os.environ.get("ANTHROPIC_AUTH_TOKEN")
                        or os.environ.get("OPENAI_API_KEY")
                        or os.environ.get("ANTHROPIC_API_KEY") or "")
        self.timeout = timeout

    def complete(self, system: str, user: str) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0,
        }
        resp = httpx.post(url, headers=headers, json=payload, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


_SYSTEM = (
    "你是一个严谨的答题助手。只输出一个 JSON 对象，键为题目 id，值为该题答案文本。"
    "填空题只给最简答案，简答题给简洁正确的答案。不要输出任何额外说明或代码块标记。"
)


def build_prompt(questions: List[Question]) -> str:
    items = [{"id": q.id, "type": q.qtype.value, "question": q.text} for q in questions]
    return (
        "请回答下列题目，返回 JSON：{\"题目id\": \"答案\"}\n\n"
        + json.dumps(items, ensure_ascii=False, indent=2)
    )


def extract_json_object(text: str) -> Dict[str, str]:
    """Best-effort JSON object extraction from an LLM response."""
    text = text.strip()
    # strip ```json fences if present
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match:
        return json.loads(match.group(0))
    raise ValueError(f"Could not parse JSON answers from LLM response: {text[:200]!r}")


def answer_questions(client: LLMClient, questions: List[Question]) -> List[Answer]:
    if not questions:
        return []
    raw = client.complete(_SYSTEM, build_prompt(questions))
    mapping = extract_json_object(raw)
    answers: List[Answer] = []
    for q in questions:
        if q.id in mapping:
            answers.append(Answer(question_id=q.id, text=str(mapping[q.id])))
    return answers
