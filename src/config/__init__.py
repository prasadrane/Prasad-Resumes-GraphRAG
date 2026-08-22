"""
config — Centralized path configuration for Prasad Resumes GraphRAG.

Single source of truth for repository-root-relative paths, replacing the
scattered per-module recomputation of ROOT_DIR from __file__.

Bootstrap exceptions: api/index.py and src/cli.py compute their own ROOT_DIR
before any src.* import, because they need it on sys.path first.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ROOT_DIR calculation: this file is at src/config/__init__.py
# So: parent = src/config/, parent.parent = src/, parent.parent.parent = project root
ROOT_DIR = Path(__file__).resolve().parent.parent.parent

# Automatically load environment variables from .env if present
load_dotenv(ROOT_DIR / ".env")

INPUT_DIR = ROOT_DIR / "input"
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
_out_path = Path(OUTPUT_DIR)
OUTPUT_DIR_PATH = _out_path if _out_path.is_absolute() else (ROOT_DIR / OUTPUT_DIR)
CACHE_DIR_PATH = ROOT_DIR / "cache"
def _find_master_resume() -> Path:
    candidates = [
        INPUT_DIR / "MASTER_RESUME.txt",
        Path.cwd() / "input" / "MASTER_RESUME.txt",
        Path(__file__).resolve().parent.parent.parent / "input" / "MASTER_RESUME.txt",
        Path("/var/task/input/MASTER_RESUME.txt"),
    ]
    for c in candidates:
        if c.exists():
            return c
    return INPUT_DIR / "MASTER_RESUME.txt"

MASTER_RESUME_PATH = _find_master_resume()
WEB_STATIC_DIR = ROOT_DIR / "src" / "web" / "static"
