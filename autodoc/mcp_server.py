"""Standalone MCP server exposing autodoc's document tools.

This module is OPTIONAL and fully isolated: it is not imported by the CLI
(`cli.py`) or the web API (`api.py`), so it never affects the main program.
Install it with the optional extra (requires Python >= 3.10)::

    pip install -e ".[mcp]"

Run it (stdio transport, e.g. for Claude Code)::

    autodoc-mcp            # or: python -m autodoc.mcp_server

Register it with an MCP client (example ``.mcp.json``)::

    {
      "mcpServers": {
        "autodoc": { "command": "autodoc-mcp", "args": [] }
      }
    }

It gives any MCP-capable agent (Claude Code, etc.) the ability to read
questions from a document and write answers back in-place, preserving the
original formatting -- the same core the CLI/web use.
"""
from __future__ import annotations

import json
from typing import Dict, Optional


# ----- plain logic functions (testable without the `mcp` package) -----

def do_parse(path: str) -> dict:
    """Detect questions in a document; returns parse result as a dict."""
    from .core.parse import parse_document

    return json.loads(parse_document(path).model_dump_json())


def do_edit(path: str, answers: Dict[str, str], output: Optional[str] = None) -> dict:
    """Write answers (``{question_id: text}``) into the document in-place."""
    from .core.answers_io import parse_answers
    from .core.edit import write_answers
    from .core.parse import parse_document

    questions = parse_document(path).questions
    answer_list = parse_answers(answers)
    result = write_answers(path, answer_list, questions, output=output)
    return json.loads(result.model_dump_json())


def do_answer(
    path: str,
    base_url: str = "",
    model: str = "",
    api_key: str = "",
    output: Optional[str] = None,
) -> dict:
    """Read questions, ask an OpenAI-compatible model, write answers in-place."""
    from .core.agent import answer_document
    from .core.llm import OpenAICompatClient

    client = OpenAICompatClient(base_url=base_url, model=model, api_key=api_key)
    result = answer_document(path, client, output=output)
    return json.loads(result.model_dump_json())


# ----- MCP tool registrations (built lazily so the `mcp` package, which
# requires Python >=3.10, is only needed when actually running the server) -----

def build_server():
    """Construct the FastMCP server with the three document tools."""
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("autodoc")

    @server.tool()
    def parse_document(path: str) -> dict:
        """Detect questions in a document (docx/pdf/xlsx/pptx/txt/md)."""
        return do_parse(path)

    @server.tool()
    def edit_document(path: str, answers: Dict[str, str], output: str = "") -> dict:
        """Write answers into a document in-place, preserving the original format.

        ``answers`` maps question id (e.g. "q1") to the answer text.
        """
        return do_edit(path, answers, output=output or None)

    @server.tool()
    def answer_document(
        path: str, base_url: str = "", model: str = "", api_key: str = "", output: str = ""
    ) -> dict:
        """Read questions, ask the model, and write answers back in-place."""
        return do_answer(
            path, base_url=base_url, model=model, api_key=api_key, output=output or None
        )

    return server


def main() -> None:
    build_server().run()


if __name__ == "__main__":
    main()
