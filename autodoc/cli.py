"""autodoc command-line interface. This is the single source of truth.

Every capability of the product is a subcommand here. The HTTP API and
web UI must map 1:1 onto these commands.
"""
from __future__ import annotations

import json

import typer

from . import __version__
from .core import formats

app = typer.Typer(
    add_completion=False,
    help="AI document Q&A automation (read questions, write answers in-place).",
    no_args_is_help=True,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def _root(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """autodoc root command."""


@app.command()
def version() -> None:
    """Print the autodoc version."""
    typer.echo(__version__)


@app.command("formats")
def list_formats() -> None:
    """List supported document formats."""
    typer.echo(json.dumps(formats.supported_extensions()))


@app.command()
def parse(
    path: str = typer.Argument(..., help="Path to the document to parse."),
    json_out: bool = typer.Option(False, "--json", help="Emit JSON."),
) -> None:
    """Detect questions in a document."""
    from .core.parse import parse_document

    result = parse_document(path)
    if json_out:
        typer.echo(result.model_dump_json())
    else:
        typer.echo(f"{result.path} [{result.format.value}] {len(result.questions)} question(s)")
        for q in result.questions:
            typer.echo(f"  {q.number}. ({q.qtype.value}) {q.text}")


@app.command()
def edit(
    path: str = typer.Argument(..., help="Path to the document to edit in-place."),
    answers: str = typer.Option(..., "--answers", help="Path to answers JSON ({id: text} or [{question_id, text}])."),
    output: str = typer.Option("", "--output", help="Write to this path instead of in-place."),
) -> None:
    """Write answers back into a document in-place (preserving formatting)."""
    from .core.answers_io import load_answers
    from .core.edit import write_answers
    from .core.parse import parse_document

    questions = parse_document(path).questions
    answer_list = load_answers(answers)
    result = write_answers(path, answer_list, questions, output=output or None)
    typer.echo(result.model_dump_json())


@app.command()
def answer(
    path: str = typer.Argument(..., help="Path to the document."),
    model: str = typer.Option("", "--model", help="LLM model name."),
    base_url: str = typer.Option("", "--base-url", help="OpenAI-compatible base URL."),
    api_key: str = typer.Option("", "--api-key", help="API key (else read from env)."),
    output: str = typer.Option("", "--output", help="Write to this path instead of in-place."),
    mode: str = typer.Option(
        "auto",
        "--mode",
        help="auto (default): detect; simple: numbered '1. ____'; worksheet: LLM structure-aware (docx).",
    ),
) -> None:
    """Read questions, ask the LLM, and write answers in-place."""
    import httpx

    from .core.answer_router import answer as route_answer
    from .core.llm import OpenAICompatClient

    client = OpenAICompatClient(base_url=base_url, model=model, api_key=api_key)
    try:
        result = route_answer(path, client, mode=mode, output=output or None)
    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:300]
        typer.echo(
            f"模型接口返回错误 {exc.response.status_code}：{body}", err=True
        )
        raise typer.Exit(code=1)
    except httpx.RequestError as exc:
        typer.echo(f"无法连接模型接口：{exc}", err=True)
        raise typer.Exit(code=1)
    typer.echo(result.model_dump_json())


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8000, "--port"),
) -> None:
    """Run the HTTP API + responsive web UI."""
    import uvicorn

    uvicorn.run("autodoc.api:app", host=host, port=port, log_level="info")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
