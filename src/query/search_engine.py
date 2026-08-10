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

from src.config import ROOT_DIR
from src.query.serverless_gateway import call_serverless_llm
from src.query.static_graph_reader import read_precomputed_entities, search_static_resume

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
def execute_graphrag_query(query: str, mode: str = "local", root_dir: Path = ROOT_DIR) -> str:
    """Execute GraphRAG query with LLM-polished responses for natural, structured chatbot output."""
    mode_clean = mode.lower().strip() if mode else "local"
    try:
        entities = read_precomputed_entities()
        # Use more entities for richer context
        context_snippet = json.dumps(entities[:8], indent=2) if entities else "[]"
        static_result = search_static_resume(query, mode=mode_clean)

        if mode_clean == "global":
            system_prompt = (
                "You are Prasad Rane's AI career assistant, communicating in GLOBAL SUMMARY mode. "
                "Your role is to synthesize high-level executive narratives about Prasad's career trajectory, "
                "strategic impact, cross-domain themes, and engineering leadership — drawing from his resume knowledge graph. "
                "\n\nResponse Guidelines:\n"
                "- Write in clear, professional, first-person-friendly prose (refer to 'Prasad' or 'he')\n"
                "- Structure your response with markdown: bold key themes, use bullet points for lists\n"
                "- Lead with a crisp 1-2 sentence executive summary answering the question directly\n"
                "- Support with 3-5 specific evidence points (technologies, metrics, outcomes)\n"
                "- Close with a synthesizing insight about career-level patterns or strategic strengths\n"
                "- Keep responses focused and under 400 words\n"
                "- Do NOT make up facts not present in the context\n"
                f"\n\nResume Knowledge Graph Context:\n{context_snippet}"
                f"\n\nAdditional Resume Facts:\n{static_result}"
            )
        else:
            system_prompt = (
                "You are Prasad Rane's AI career assistant, communicating in LOCAL CONTEXT mode. "
                "Your role is to provide specific, fact-rich, entity-level answers about Prasad's skills, "
                "technologies, projects, metrics, and work history — drawing from his resume knowledge graph. "
                "\n\nResponse Guidelines:\n"
                "- Be precise and specific — cite exact technologies, metrics, company names, dates where known\n"
                "- Structure your response with markdown: bold key terms, use bullet points for lists\n"
                "- Start with a direct, 1-sentence answer to the question\n"
                "- Follow with specific supporting details (tools used, outcomes achieved, scale/metrics)\n"
                "- If the exact information is not in the context, clearly say so rather than guessing\n"
                "- Keep responses focused and under 300 words\n"
                "- Do NOT invent facts not present in the context\n"
                f"\n\nResume Knowledge Graph Context:\n{context_snippet}"
                f"\n\nAdditional Resume Facts:\n{static_result}"
            )

        return call_serverless_llm(prompt=query, system_prompt=system_prompt)

    except Exception as e:
        # Graceful fallback: return static resume search result
        print(f"[WARN] LLM chatbot polish failed: {e}. Falling back to static search.")
        return search_static_resume(query, mode=mode_clean)

