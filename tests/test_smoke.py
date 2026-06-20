"""Phase 0 smoke tests: package imports, version, CLI surface."""
from __future__ import annotations

import subprocess
import sys

from typer.testing import CliRunner

from autodoc import __version__
from autodoc.cli import app
from autodoc.core import formats

runner = CliRunner()


def test_version_constant():
    assert __version__


def test_cli_version_command():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_cli_version_flag():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_cli_help_lists_all_subcommands():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ("parse", "edit", "answer", "serve", "formats", "version"):
        assert cmd in result.stdout


def test_supported_formats():
    exts = formats.supported_extensions()
    for ext in (".docx", ".xlsx", ".pptx", ".pdf", ".txt", ".md"):
        assert ext in exts


def test_cli_invoked_as_module():
    proc = subprocess.run(
        [sys.executable, "-m", "autodoc.cli", "version"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert __version__ in proc.stdout
