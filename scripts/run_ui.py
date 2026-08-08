"""
run_ui.py — Launcher script for the Prasad Resumes GraphRAG Web UI.
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import uvicorn

if __name__ == "__main__":
    host = "127.0.0.1"
    port = 8000
    print(f"[UI] Launching Prasad Resumes GraphRAG UI on http://{host}:{port}")
    uvicorn.run("src.web.app:app", host=host, port=port, reload=True)
