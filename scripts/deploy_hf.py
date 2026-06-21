"""Deploy autodoc to a Hugging Face Docker Space.

Usage:
    pip install huggingface_hub
    HF_TOKEN=hf_xxx python scripts/deploy_hf.py --owner <user> --space autodoc-ai-answer

Creates (or reuses) a Docker Space and uploads the files the image needs:
Dockerfile, README.md (with HF front-matter), pyproject.toml and autodoc/.
HF then builds the image and serves it on port 7860 automatically.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UPLOAD = ["Dockerfile", "README.md", "pyproject.toml", ".dockerignore"]
UPLOAD_DIRS = ["autodoc"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--owner", required=True, help="Your Hugging Face username/org")
    ap.add_argument("--space", default="autodoc-ai-answer", help="Space name")
    ap.add_argument("--private", action="store_true", help="Create a private Space")
    args = ap.parse_args()

    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
    if not token:
        print("ERROR: set HF_TOKEN (a Write access token) in the environment.", file=sys.stderr)
        return 2

    try:
        from huggingface_hub import HfApi
    except ImportError:
        print("ERROR: pip install huggingface_hub", file=sys.stderr)
        return 2

    api = HfApi(token=token)
    repo_id = f"{args.owner}/{args.space}"

    api.create_repo(
        repo_id=repo_id,
        repo_type="space",
        space_sdk="docker",
        private=args.private,
        exist_ok=True,
    )
    print(f"Space ready: https://huggingface.co/spaces/{repo_id}")

    # stage a temp folder with only the files the image needs
    import shutil
    import tempfile

    staging = Path(tempfile.mkdtemp(prefix="hf_autodoc_"))
    try:
        for f in UPLOAD:
            src = ROOT / f
            if src.exists():
                shutil.copyfile(src, staging / f)
        for d in UPLOAD_DIRS:
            shutil.copytree(
                ROOT / d, staging / d,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
        api.upload_folder(
            folder_path=str(staging),
            repo_id=repo_id,
            repo_type="space",
            commit_message="Deploy autodoc (Docker Space)",
        )
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    print("Uploaded. HF will build the image now (1-3 min).")
    print(f"Open: https://huggingface.co/spaces/{repo_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
