"""
config.py — Centralized path configuration for Prasad Resumes GraphRAG.

Single source of truth for repository-root-relative paths, replacing the
scattered per-module recomputation of ROOT_DIR from __file__.

Bootstrap exceptions: api/index.py and src/cli.py compute their own ROOT_DIR
before any src.* import, because they need it on sys.path first.
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
INPUT_DIR = ROOT_DIR / "input"
OUTPUT_DIR = ROOT_DIR / "output"
MASTER_RESUME_PATH = INPUT_DIR / "MASTER_RESUME.txt"
WEB_STATIC_DIR = ROOT_DIR / "src" / "web" / "static"
