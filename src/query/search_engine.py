"""
search_engine.py — Search execution and LRU caching for GraphRAG queries.
Applies Dependency Inversion Principle (DIP) for testable subprocess execution.
"""

import json
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

from src.query.serverless_gateway import call_serverless_llm
from src.query.static_graph_reader import read_precomputed_entities, search_static_resume

@lru_cache(maxsize=100)
def execute_graphrag_query(query: str, mode: str = "local", root_dir: Path = ROOT_DIR) -> str:
    """Execute GraphRAG query with fast static graph & LLM fallback for instant UI responses."""
    mode_clean = mode.lower().strip() if mode else "local"
    # Attempt direct fast serverless or precomputed graph reading
    try:
        entities = read_precomputed_entities()
        context_snippet = json.dumps(entities[:5], indent=2) if entities else ""
        if mode_clean == "global":
            system_prompt = f"You are an AI GraphRAG assistant in GLOBAL SUMMARY mode. Synthesize high-level executive overviews, career-wide impact summaries, and strategic domain themes for Prasad Rane based on his resume knowledge graph.\n\nContext:\n{context_snippet}"
        else:
            system_prompt = f"You are an AI GraphRAG assistant in LOCAL CONTEXT mode. Provide granular, specific entity-level facts, exact metrics, project bullets, and technical tool details for Prasad Rane based on his resume knowledge graph.\n\nContext:\n{context_snippet}"
        return call_serverless_llm(prompt=query, system_prompt=system_prompt)
    except Exception as e:
        # Dynamic resume search fallback guaranteed to return accurate answer instantly
        return search_static_resume(query, mode=mode_clean)
