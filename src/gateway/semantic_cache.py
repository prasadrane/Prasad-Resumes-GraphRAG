"""
semantic_cache.py — In-memory vector semantic cache for LLM gateway queries.

Caches (query, embedding, response) tuples and performs fast cosine similarity checks
to serve near-instant responses for semantically equivalent questions without external API costs.
"""

from __future__ import annotations

import collections
from dataclasses import dataclass
import logging
import math
import threading
import time
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Calculate cosine similarity between two float vectors."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    n1 = math.sqrt(sum(a * a for a in v1))
    n2 = math.sqrt(sum(b * b for b in v2))
    if n1 <= 1e-9 or n2 <= 1e-9:
        return 0.0
    return dot / (n1 * n2)


@dataclass
class CachedItem:
    query: str
    response: str
    embedding: Optional[List[float]] = None
    timestamp: float = 0.0


class SemanticCache:
    """
    In-memory LRU Semantic Vector Cache.
    """

    def __init__(
        self,
        similarity_threshold: float = 0.95,
        max_size: int = 100,
        ttl_seconds: float = 3600.0,
    ) -> None:
        self.similarity_threshold = similarity_threshold
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: collections.OrderedDict[str, CachedItem] = collections.OrderedDict()
        self._lock = threading.Lock()

    def lookup(
        self,
        query: str,
        embedding: Optional[List[float]] = None,
    ) -> Optional[str]:
        """
        Check for exact match or semantic vector match above similarity_threshold.
        """
        if not query or not query.strip():
            return None

        norm_query = query.strip().lower()
        now = time.monotonic()

        with self._lock:
            # 1. Exact query match check
            if norm_query in self._cache:
                item = self._cache[norm_query]
                if (now - item.timestamp) <= self.ttl_seconds:
                    self._cache.move_to_end(norm_query)
                    logger.debug("[CACHE HIT - EXACT] %s", query)
                    return item.response
                else:
                    del self._cache[norm_query]

            # 2. Semantic vector cosine similarity check
            if embedding is not None:
                for key, item in list(self._cache.items()):
                    if (now - item.timestamp) > self.ttl_seconds:
                        del self._cache[key]
                        continue

                    if item.embedding is not None:
                        sim = cosine_similarity(embedding, item.embedding)
                        if sim >= self.similarity_threshold:
                            self._cache.move_to_end(key)
                            logger.info("[CACHE HIT - SEMANTIC (sim=%.3f)] %s -> %s", sim, query, item.query)
                            return item.response

        return None

    def store(
        self,
        query: str,
        response: str,
        embedding: Optional[List[float]] = None,
    ) -> None:
        """Store a query response in the semantic cache."""
        if not query or not response:
            return

        norm_query = query.strip().lower()
        now = time.monotonic()

        with self._lock:
            if norm_query in self._cache:
                del self._cache[norm_query]

            # Evict oldest if full
            while len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)

            self._cache[norm_query] = CachedItem(
                query=query,
                response=response,
                embedding=embedding,
                timestamp=now,
            )

    def clear(self) -> None:
        """Clear all cached entries."""
        with self._lock:
            self._cache.clear()
