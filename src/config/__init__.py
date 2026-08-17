"""
config — Centralized path configuration for Prasad Resumes GraphRAG.

Single source of truth for repository-root-relative paths, replacing the
scattered per-module recomputation of ROOT_DIR from __file__.

Bootstrap exceptions: api/index.py and src/cli.py compute their own ROOT_DIR
before any src.* import, because they need it on sys.path first.
"""

import os
from pathlib import Path

# ROOT_DIR calculation: this file is at src/config/__init__.py
# So: parent = src/config/, parent.parent = src/, parent.parent.parent = project root
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
INPUT_DIR = ROOT_DIR / "input"
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
OUTPUT_DIR_PATH = ROOT_DIR / OUTPUT_DIR
CACHE_DIR_PATH = ROOT_DIR / "cache"
MASTER_RESUME_PATH = INPUT_DIR / "MASTER_RESUME.txt"
WEB_STATIC_DIR = ROOT_DIR / "src" / "web" / "static"
