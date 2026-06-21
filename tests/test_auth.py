"""Cloud-hardening tests: token auth, auth_required flag, upload size limit."""
from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from autodoc import api


def test_version_reports_auth_required(monkeypatch):
    monkeypatch.delenv("AUTODOC_TOKEN", raising=False)
    client = TestClient(api.app)
    assert client.get("/api/version").json()["auth_required"] is False
    monkeypatch.setenv("AUTODOC_TOKEN", "secret")
    assert client.get("/api/version").json()["auth_required"] is True


def test_parse_blocked_without_token(monkeypatch, sample_docx: Path):
    monkeypatch.setenv("AUTODOC_TOKEN", "secret")
    client = TestClient(api.app)
    with open(sample_docx, "rb") as fh:
        r = client.post(
            "/api/parse", files={"file": ("q.docx", fh, "application/octet-stream")}
        )
    assert r.status_code == 401


def test_parse_allowed_with_token(monkeypatch, sample_docx: Path):
    monkeypatch.setenv("AUTODOC_TOKEN", "secret")
    client = TestClient(api.app)
    with open(sample_docx, "rb") as fh:
        r = client.post(
            "/api/parse",
            files={"file": ("q.docx", fh, "application/octet-stream")},
            headers={"X-Autodoc-Token": "secret"},
        )
    assert r.status_code == 200
    assert len(r.json()["questions"]) == 3


def test_open_when_no_token_configured(monkeypatch, sample_docx: Path):
    monkeypatch.delenv("AUTODOC_TOKEN", raising=False)
    client = TestClient(api.app)
    with open(sample_docx, "rb") as fh:
        r = client.post(
            "/api/parse", files={"file": ("q.docx", fh, "application/octet-stream")}
        )
    assert r.status_code == 200


def test_upload_size_limit(monkeypatch, sample_docx: Path):
    monkeypatch.delenv("AUTODOC_TOKEN", raising=False)
    monkeypatch.setattr(api, "_MAX_UPLOAD_BYTES", 10)
    client = TestClient(api.app)
    with open(sample_docx, "rb") as fh:
        r = client.post(
            "/api/parse", files={"file": ("q.docx", fh, "application/octet-stream")}
        )
    assert r.status_code == 413
