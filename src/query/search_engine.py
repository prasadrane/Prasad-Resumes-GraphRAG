"""
search_engine.py — Search execution and LRU caching for GraphRAG queries.
Applies Dependency Inversion Principle (DIP) for testable subprocess execution.
"""

import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import Callable, Optional

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

# Command Runner Protocol type hint
CommandRunner = Callable[[list, str], subprocess.CompletedProcess]

def default_command_runner(cmd: list, cwd_path: str) -> subprocess.CompletedProcess:
    """Default process runner using subprocess.run."""
    return subprocess.run(cmd, cwd=cwd_path, capture_output=True, text=True, encoding="utf-8")

def _run_graphrag_query_uncached(query: str, mode: str, root_dir: Path, runner: CommandRunner = default_command_runner) -> str:
    """Execute raw GraphRAG query subprocess adhering to Dependency Inversion."""
    cmd = [
        sys.executable, "-m", "graphrag", "query",
        "--root", str(root_dir),
        "--method", mode,
        "--query", query,
    ]
    result = runner(cmd, str(root_dir))
    if result.returncode != 0:
        err_msg = result.stderr.strip() if result.stderr else (result.stdout.strip() if result.stdout else "Unknown GraphRAG execution error")
        raise RuntimeError(f"GraphRAG query execution failed (code {result.returncode}):\n{err_msg}")
    return result.stdout

@lru_cache(maxsize=100)
def execute_graphrag_query(query: str, mode: str, root_dir: Path = ROOT_DIR) -> str:
    """Execute a GraphRAG query with LRU caching for successful responses."""
    return _run_graphrag_query_uncached(query, mode, root_dir, default_command_runner)
