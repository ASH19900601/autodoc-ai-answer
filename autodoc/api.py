"""HTTP API + responsive web UI.

CLI == GUI contract
-------------------
This module contains NO business logic and imports NO document libraries.
Every endpoint is a thin wrapper over ``autodoc.core`` (the same code the
CLI calls) and returns an ``equivalent_cli`` string describing the exact
CLI command that produces the same result. The web UI under ``web/`` only
talks to these endpoints. This is what makes "GUI == CLI" verifiable.
"""
from __future__ import annotations

import json
import os
import shlex
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import __version__

app = FastAPI(title="autodoc", version=__version__)

_WEB_DIR = Path(__file__).parent / "web"
app.mount("/static", StaticFiles(directory=str(_WEB_DIR)), name="static")


def _save_upload(upload: UploadFile) -> str:
    suffix = os.path.splitext(upload.filename or "")[1] or ".bin"
    fd, tmp = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as fh:
        fh.write(upload.file.read())
    return tmp


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (_WEB_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/api/version")
def version():
    return {"version": __version__, "equivalent_cli": "autodoc --version"}


@app.get("/api/formats")
def formats():
    from .core.formats import supported_extensions

    return {"formats": supported_extensions(), "equivalent_cli": "autodoc formats"}


@app.post("/api/parse")
async def parse(file: UploadFile = File(...)):
    from .core.parse import parse_document

    tmp = _save_upload(file)
    try:
        result = parse_document(tmp)
        payload = json.loads(result.model_dump_json())
        payload["path"] = file.filename
        payload["equivalent_cli"] = f"autodoc parse {shlex.quote(file.filename or 'doc')} --json"
        return JSONResponse(payload)
    finally:
        os.unlink(tmp)


@app.post("/api/edit")
async def edit(file: UploadFile = File(...), answers: str = Form(...)):
    """Deterministic edit: write provided answers in-place (no LLM)."""
    from .core.answers_io import parse_answers
    from .core.edit import write_answers
    from .core.parse import parse_document

    tmp = _save_upload(file)
    try:
        questions = parse_document(tmp).questions
        answer_list = parse_answers(json.loads(answers))
        result = write_answers(tmp, answer_list, questions, output=None)
        name = file.filename or "result"
        cli = (
            f"autodoc edit {shlex.quote(name)} "
            f"--answers answers.json"
        )
        return FileResponse(
            tmp,
            filename=name,
            headers={
                "X-Equivalent-Cli": cli,
                "X-Answers-Written": str(result.answers_written),
            },
        )
    finally:
        pass  # FileResponse streams the file; OS temp cleaned by OS/tests


@app.post("/api/answer")
async def answer(
    file: UploadFile = File(...),
    model: str = Form(""),
    base_url: str = Form(""),
    api_key: str = Form(""),
    mode: str = Form("auto"),
):
    """LLM-driven: parse -> ask model -> write answers in-place.

    ``mode`` is auto (default) / simple / worksheet.
    """
    import httpx

    from .core.answer_router import answer as route_answer
    from .core.llm import OpenAICompatClient

    tmp = _save_upload(file)
    client = OpenAICompatClient(base_url=base_url, model=model, api_key=api_key)
    try:
        result = route_answer(tmp, client, mode=mode, output=None)
    except httpx.HTTPStatusError as exc:
        return JSONResponse(
            status_code=502,
            content={
                "error": "model_api_error",
                "status": exc.response.status_code,
                "detail": exc.response.text[:300],
            },
        )
    except httpx.RequestError as exc:
        return JSONResponse(
            status_code=502,
            content={"error": "model_unreachable", "detail": str(exc)},
        )
    name = file.filename or "result"
    parts = ["autodoc", "answer", shlex.quote(name)]
    if (result.mode or mode) and (result.mode or mode) != "auto":
        parts += ["--mode", result.mode or mode]
    if model:
        parts += ["--model", shlex.quote(model)]
    if base_url:
        parts += ["--base-url", shlex.quote(base_url)]
    cli = " ".join(parts)
    return FileResponse(
        tmp,
        filename=name,
        headers={
            "X-Equivalent-Cli": cli,
            "X-Answers-Written": str(result.answers_written),
            "X-Mode": result.mode or mode,
        },
    )
