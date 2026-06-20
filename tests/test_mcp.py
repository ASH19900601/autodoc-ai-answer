"""MCP server tests.

The plain tool logic (do_parse/do_edit/do_answer) is testable without the
`mcp` package (which needs Python >=3.10). The FastMCP construction test is
skipped automatically when `mcp` is not installed.
"""
from __future__ import annotations

import json
from pathlib import Path

import docx
import pytest

from autodoc.core import llm as llm_mod
from autodoc.mcp_server import do_answer, do_edit, do_parse


def test_do_parse(sample_docx: Path):
    result = do_parse(str(sample_docx))
    assert result["format"] == "docx"
    assert len(result["questions"]) == 3


def test_do_edit_in_place(sample_docx: Path):
    result = do_edit(str(sample_docx), {"q1": "北京", "q2": "H2O", "q3": "月球"})
    assert result["in_place"] is True
    assert result["answers_written"] == 3
    full = "\n".join(p.text for p in docx.Document(str(sample_docx)).paragraphs)
    assert "北京" in full and "H2O" in full and "月球" in full


def test_do_answer_with_fake_client(sample_docx: Path, monkeypatch):
    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def complete(self, system, user):
            return json.dumps({"q1": "北京", "q2": "H2O", "q3": "月球"})

    monkeypatch.setattr(llm_mod, "OpenAICompatClient", FakeClient)
    result = do_answer(str(sample_docx), base_url="x", model="y", api_key="z")
    assert result["answers_written"] == 3


def test_build_server_registers_tools():
    pytest.importorskip("mcp")
    from autodoc.mcp_server import build_server

    server = build_server()
    tools = server._tool_manager.list_tools()
    names = {t.name for t in tools}
    assert {"parse_document", "edit_document", "answer_document"} <= names
