"""Phase 5 tests: HTTP API correctness, CLI==GUI parity, no-doc-libs check."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import docx
from fastapi.testclient import TestClient

from autodoc import __version__
from autodoc.api import app

client = TestClient(app)


def _docx_text(path) -> str:
    return "\n".join(p.text for p in docx.Document(str(path)).paragraphs)


# ---------- endpoint correctness ----------

def test_index_served():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "autodoc" in resp.text


def test_version_endpoint():
    resp = client.get("/api/version")
    assert resp.status_code == 200
    body = resp.json()
    assert body["version"] == __version__
    assert body["equivalent_cli"] == "autodoc --version"


def test_formats_endpoint():
    body = client.get("/api/formats").json()
    assert ".docx" in body["formats"]
    assert body["equivalent_cli"] == "autodoc formats"


def test_parse_endpoint(sample_docx: Path):
    with open(sample_docx, "rb") as fh:
        resp = client.post(
            "/api/parse",
            files={"file": ("quiz.docx", fh, "application/octet-stream")},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["questions"]) == 3
    assert body["equivalent_cli"].startswith("autodoc parse")


# ---------- the core CLI == GUI parity test ----------

def test_cli_equals_gui_for_edit(sample_docx: Path, tmp_path: Path):
    answers = {"q1": "北京", "q2": "H2O", "q3": "月球"}

    # (a) CLI path: run the real `autodoc edit` via subprocess
    f_cli = tmp_path / "cli.docx"
    shutil.copyfile(str(sample_docx), str(f_cli))
    ans_file = tmp_path / "answers.json"
    ans_file.write_text(json.dumps(answers, ensure_ascii=False), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "-m", "autodoc.cli", "edit", str(f_cli),
         "--answers", str(ans_file)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr

    # (b) GUI path: POST the same input + answers to /api/edit
    f_api_out = tmp_path / "api_out.docx"
    with open(sample_docx, "rb") as fh:
        resp = client.post(
            "/api/edit",
            files={"file": ("quiz.docx", fh, "application/octet-stream")},
            data={"answers": json.dumps(answers, ensure_ascii=False)},
        )
    assert resp.status_code == 200
    assert resp.headers["x-equivalent-cli"].startswith("autodoc edit")
    assert resp.headers["x-answers-written"] == "3"
    f_api_out.write_bytes(resp.content)

    # (c) parity: GUI output text == CLI output text
    assert _docx_text(f_cli) == _docx_text(f_api_out)
    assert "北京" in _docx_text(f_api_out)


# ---------- static guarantee: GUI/CLI layers never import doc libs ----------

FORBIDDEN = ["import docx", "from docx", "import fitz", "from fitz",
             "import openpyxl", "from openpyxl", "import pptx", "from pptx"]


def test_api_layer_has_no_document_libraries():
    src = (Path(__file__).parent.parent / "autodoc" / "api.py").read_text(encoding="utf-8")
    for needle in FORBIDDEN:
        assert needle not in src, f"api.py must not contain {needle!r}"


def test_cli_layer_has_no_document_libraries():
    src = (Path(__file__).parent.parent / "autodoc" / "cli.py").read_text(encoding="utf-8")
    for needle in FORBIDDEN:
        assert needle not in src, f"cli.py must not contain {needle!r}"
