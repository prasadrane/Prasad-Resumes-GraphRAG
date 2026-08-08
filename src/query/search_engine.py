"""
search_engine.py — Search execution and LRU caching for GraphRAG queries.
"""

import subprocess
import sys
from functools import lru_cache
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

def _run_graphrag_query_uncached(query: str, mode: str, root_dir: Path) -> str:
    """Execute raw GraphRAG query subprocess."""
    cmd = [
        sys.executable, "-m", "graphrag", "query",
        "--root", str(root_dir),
        "--method", mode,
        "--query", query,
    ]
    result = subprocess.run(cmd, cwd=str(root_dir), capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        err_msg = result.stderr.strip() or result.stdout.strip() or "Unknown GraphRAG execution error"
        raise RuntimeError(f"GraphRAG query execution failed (code {result.returncode}):\n{err_msg}")
    return result.stdout

@lru_cache(maxsize=100)
def execute_graphrag_query(query: str, mode: str, root_dir: Path = ROOT_DIR) -> str:
    """Execute a GraphRAG query with LRU caching for successful responses."""
    return _run_graphrag_query_uncached(query, mode, root_dir)
