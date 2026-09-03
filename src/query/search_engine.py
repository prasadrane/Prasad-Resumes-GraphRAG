"""
search_engine.py -- Search execution and TTL-cached GraphRAG queries.

Applies Dependency Inversion Principle (DIP) for testable subprocess execution.
Includes a TTL-based in-memory cache with configurable size/TTL and simple
metrics counters that can be integrated with W4's MetricsCollector later.
"""

import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Optional

from src.config import ROOT_DIR
from src.gateway import call_serverless_llm
from src.query.static_graph_reader import read_precomputed_entities, search_static_resume

logger = logging.getLogger(__name__)


class TTLCache:
    """Thread-safe, in-memory TTL cache with LRU eviction.

    Configurable max_size and TTL (in seconds).  Transparent drop-in
    replacement for ``@lru_cache`` -- exposes ``get``, ``set``, and
    ``cache_clear`` methods so existing test patterns continue working.
    """

    def __init__(self, max_size: int = 100, ttl: int = 300):
        self.max_size = max_size
        self.ttl = ttl
        self._cache: dict[str, tuple[str, float]] = {}
        self._lock = threading.Lock()
        # Simple metrics counters (integratable with W4 MetricsCollector)
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    # -- public API -------------------------------------------------------

    def get(self, key: str) -> Optional[str]:
        """Return cached value or None (miss / expired)."""
        with self._lock:
            if key in self._cache:
                value, timestamp = self._cache[key]
                if time.time() - timestamp < self.ttl:
                    self.hits += 1
                    return value
                # Expired -- remove it
                del self._cache[key]
            self.misses += 1
            return None

    def set(self, key: str, value: str) -> None:
        """Insert into cache, evicting oldest entry on overflow."""
        with self._lock:
            if len(self._cache) >= self.max_size:
                oldest_key = min(self._cache, key=lambda k: self._cache[k][1])
                del self._cache[oldest_key]
                self.evictions += 1
            self._cache[key] = (value, time.time())

    def cache_clear(self) -> None:
        """Remove all entries and reset metrics. Test-friendly alias."""
        with self._lock:
            self._cache.clear()
            self.hits = 0
            self.misses = 0
            self.evictions = 0

    @property
    def size(self) -> int:
        """Current number of entries (thread-safe snapshot)."""
        with self._lock:
            return len(self._cache)




# ---------------------------------------------------------------------------
# Shared TTL Cache (configurable, transparent drop-in)
# ---------------------------------------------------------------------------
# Default: 100 entries, 300s TTL; override via environment variables.
_QUERY_CACHE_MAX_SIZE = int(os.environ.get("CACHE_MAX_SIZE", "100"))
_QUERY_CACHE_TTL = int(os.environ.get("CACHE_TTL", "300"))
query_cache = TTLCache(max_size=_QUERY_CACHE_MAX_SIZE, ttl=_QUERY_CACHE_TTL)


def _execute_query(query: str, mode: str, root_dir: Path) -> str:
    """Internal: perform the actual GraphRAG query with GraphRAGEngine prioritization and static fallback."""
    mode_clean = mode.lower().strip() if mode else "local"
    graph_context = ""

    # 1. Attempt retrieval via GraphRAGEngine (Hybrid BM25 + Vector + DRIFT)
    try:
        from src.query.graphrag_engine import get_engine, GraphRAGEngine
        import asyncio
        import concurrent.futures

        async def _retrieve_engine():
            engine = await get_engine(root_dir)
            return await engine.retrieve(query, mode=mode_clean)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                ctx_dict = pool.submit(asyncio.run, _retrieve_engine()).result(timeout=4.0)
        else:
            ctx_dict = asyncio.run(_retrieve_engine())

        graph_context = GraphRAGEngine.format_context(ctx_dict)
    except Exception as eng_err:
        logger.debug("GraphRAGEngine retrieval skipped/failed: %s", eng_err)
        graph_context = ""

    # 2. Fallback to static resume reader if graph engine returned empty context or failed
    if not graph_context.strip():
        graph_context = search_static_resume(query, mode=mode_clean)

    # 3. Assemble prompt and synthesize response via serverless LLM
    try:
        if mode_clean == "global":
            system_prompt = (
                "You are Prasad Rane's AI career assistant, communicating in GLOBAL SUMMARY mode. "
                "Your role is to synthesize high-level executive narratives about Prasad's career trajectory, "
                "strategic impact, cross-domain themes, and engineering leadership -- drawing from his resume knowledge graph. "
                "\n\nResponse Guidelines:\n"
                "- Write in clear, professional, first-person-friendly prose (refer to 'Prasad' or 'he')\n"
                "- Structure your response with markdown: bold key themes, use bullet points for lists\n"
                "- Lead with a crisp 1-2 sentence executive summary answering the question directly\n"
                "- Support with 3-5 specific evidence points (technologies, metrics, outcomes)\n"
                "- Close with a synthesizing insight about career-level patterns or strategic strengths\n"
                "- Keep responses focused and under 400 words\n"
                "- Do NOT make up facts not present in the context\n"
                f"\n\nResume Knowledge Graph Context:\n{graph_context}"
            )
        else:
            system_prompt = (
                "You are Prasad Rane's AI career assistant, communicating in LOCAL CONTEXT mode. "
                "Your role is to provide specific, fact-rich, entity-level answers about Prasad's skills, "
                "technologies, projects, metrics, and work history -- drawing from his resume knowledge graph. "
                "\n\nResponse Guidelines:\n"
                "- Be precise and specific -- cite exact technologies, metrics, company names, dates where known\n"
                "- Structure your response with markdown: bold key terms, use bullet points for lists\n"
                "- Start with a direct, 1-sentence answer to the question\n"
                "- Follow with specific supporting details (tools used, outcomes achieved, scale/metrics)\n"
                "- If the exact information is not in the context, clearly say so rather than guessing\n"
                "- Keep responses focused and under 300 words\n"
                "- Do NOT invent facts not present in the context\n"
                f"\n\nResume Knowledge Graph Context:\n{graph_context}"
            )

        return call_serverless_llm(prompt=query, system_prompt=system_prompt)

    except Exception as e:
        logger.warning("LLM chatbot polish failed: %s. Falling back to static search.", e)
        return search_static_resume(query, mode=mode_clean)


def execute_graphrag_query(
    query: str, mode: str = "local", root_dir: Path = ROOT_DIR
) -> str:
    """Execute GraphRAG query -- transparently cached via TTLCache.

    Cache key is ``"{query}:{mode}"``.  Subsequent identical queries within
    the TTL window return the cached value instantly (no subprocess/LLM call).

    Test helpers exposed on :data:`query_cache`:
        * ``query_cache.cache_clear()``  -- wipe cache & reset counters
        * ``query_cache.hits``, ``.misses``, ``.evictions``
    """
    cache_key = f"{query}:{mode}"
    cached = query_cache.get(cache_key)
    if cached is not None:
        return cached
    result = _execute_query(query, mode, root_dir)
    query_cache.set(cache_key, result)
    return result


# Backwards-compatible alias for tests that used @lru_cache's .cache_clear()
execute_graphrag_query.cache_clear = query_cache.cache_clear  # type: ignore[assignment]
