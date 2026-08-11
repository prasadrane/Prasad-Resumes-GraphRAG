"""
api/index.py — Vercel Serverless Entrypoint.

Imports the canonical FastAPI app from src/web/app.py and re-exports it.
Vercel Python Functions (@vercel/python) accept ASGI apps directly,
so no wrapper is needed. All endpoint logic lives in src/web/app.py
and src/shared/api_routes.py.
"""

import sys
from pathlib import Path

# Add project root to sys.path so src.* imports resolve on Vercel
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.web.app import app  # noqa: E402, F401
