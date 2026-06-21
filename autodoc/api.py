"""HTTP API + responsive web UI.

CLI == GUI contract
-------------------
This module contains NO business logic and imports NO document libraries.
Every endpoint is a thin wrapper over ``autodoc.core`` (the same code the
CLI calls) and returns an ``equivalent_cli`` string describing the exact
CLI command that produces the same result. The web UI under ``web/`` only
talks to these endpoints. This is what makes "GUI == CLI" verifiable.

Cloud hardening
---------------
* Optional token auth: set ``AUTODOC_TOKEN`` to require the
  ``X-Autodoc-Token`` header on action endpoints (parse/edit/answer).
* Upload size limit via ``AUTODOC_MAX_UPLOAD_BYTES`` (default 25 MiB).
* Uploaded temp files are removed after the response is sent.
"""
from __future__ import annotations

import json
import os
import shlex
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.background import BackgroundTask

from . import __version__

app = FastAPI(title="autodoc", version=__version__)

_WEB_DIR = Path(__file__).parent / "web"
app.mount("/static", StaticFiles(directory=str(_WEB_DIR)), name="static")

_MAX_UPLOAD_BYTES = int(os.environ.get("AUTODOC_MAX_UPLOAD_BYTES", str(25 * 1024 * 1024)))


def _auth_required() -> bool:
    return bool(os.environ.get("AUTODOC_TOKEN"))


def require_token(x_autodoc_token: Optional[str] = Header(default=None)) -> None:
    expected = os.environ.get("AUTODOC_TOKEN")
    if expected and x_autodoc_token != expected:
        raise HTTPException(status_code=401, detail="invalid or missing access token")


def _save_upload(upload: UploadFile) -> str:
    data = upload.file.read(_MAX_UPLOAD_BYTES + 1)
    if len(data) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"file too large (limit {_MAX_UPLOAD_BYTES} bytes)",
        )
    suffix = os.path.splitext(upload.filename or "")[1] or ".bin"
    fd, tmp = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as fh:
        fh.write(data)
    return tmp


def _rm(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (_WEB_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/api/version")
def version():
    return {
        "version": __version__,
        "auth_required": _auth_required(),
        "equivalent_cli": "autodoc --version",
    }


@app.get("/api/formats")
def formats():
    from .core.formats import supported_extensions

    return {"formats": supported_extensions(), "equivalent_cli": "autodoc formats"}


@app.post("/api/parse", dependencies=[Depends(require_token)])
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
        _rm(tmp)


@app.post("/api/edit", dependencies=[Depends(require_token)])
async def edit(file: UploadFile = File(...), answers: str = Form(...)):
    """Deterministic edit: write provided answers in-place (no LLM)."""
    from .core.answers_io import parse_answers
    from .core.edit import write_answers
    from .core.parse import parse_document

    tmp = _save_upload(file)
    questions = parse_document(tmp).questions
    answer_list = parse_answers(json.loads(answers))
    result = write_answers(tmp, answer_list, questions, output=None)
    name = file.filename or "result"
    cli = f"autodoc edit {shlex.quote(name)} --answers answers.json"
    return FileResponse(
        tmp,
        filename=name,
        headers={
            "X-Equivalent-Cli": cli,
            "X-Answers-Written": str(result.answers_written),
        },
        background=BackgroundTask(_rm, tmp),
    )


@app.post("/api/answer", dependencies=[Depends(require_token)])
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
        _rm(tmp)
        return JSONResponse(
            status_code=502,
            content={
                "error": "model_api_error",
                "status": exc.response.status_code,
                "detail": exc.response.text[:300],
            },
        )
    except httpx.RequestError as exc:
        _rm(tmp)
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
        background=BackgroundTask(_rm, tmp),
    )
