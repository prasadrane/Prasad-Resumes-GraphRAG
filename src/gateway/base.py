"""Base provider abstraction for LLM / embedding API calls.

Each provider wraps a :class:`src.config.providers.ProviderConfig` and exposes:

- :meth:`chat`        — sync urllib call returning model text (Vercel hot path)
- :meth:`chat_stream` — async aiohttp generator yielding token strings
- :meth:`embed`       — optional async aiohttp call returning a float list

Sync chat stays on ``urllib`` so sync callers never need an asyncio bridge on
the Vercel hot path. Streaming + embedding share a lazily-initialized aiohttp
session.
"""

from __future__ import annotations

import json
import logging
import sys
import urllib.request
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, List, Optional

logger = logging.getLogger(__name__)

# ── Shared Constants (lazy-loaded from generators.constants to avoid
#    circular imports — base.py is imported very early by many modules) ─────

_DEFAULT_EMBEDDING_DIM: int = 2048
_RATE_LIMIT_TAGS: tuple[str, ...] = (
    "rate_limit",
    "rate limited",
    "429",
    "resource_exhausted",
    "quota",
)


def _embedding_dim():
    """Resolve the canonical embedding dimension, falling back to 2048."""
    try:
        mod = sys.modules.get("src.generators.constants")
        if mod is not None:
            return getattr(mod, "EMBEDDING_DIM", _DEFAULT_EMBEDDING_DIM)
    except Exception:
        pass
    return _DEFAULT_EMBEDDING_DIM


def _rate_limit_tags() -> tuple[str, ...]:
    """Return the unified rate-limit detection tags."""
    try:
        mod = sys.modules.get("src.generators.constants")
        if mod is not None and hasattr(mod, "RATE_LIMIT_TAGS"):
            return getattr(mod, "RATE_LIMIT_TAGS")
    except Exception:
        pass
    return _RATE_LIMIT_TAGS


# ── Shared Embedding Helpers ────────────────────────────────────────────────

def pad_embedding(emb: List[float], target_dim: int | None = None) -> List[float]:
    """Pad or truncate an embedding list to *target_dim*.

    Defaults to the value configured in :mod:`src.generators.constants`
    (falls back to ``2048`` when that module isn't available yet).

    Returns a *new* list so callers' original data is never mutated.
    """
    if target_dim is None:
        target_dim = _embedding_dim()
    length = len(emb)
    if length == target_dim:
        return list(emb)
    if length > target_dim:
        return list(emb[:target_dim])
    padded = list(emb)
    padded.extend([0.0] * (target_dim - length))
    return padded


def is_rate_limit_error(err: BaseException | Exception | str) -> bool:
    """Return ``True`` when *err* represents a rate-limit / throttling error.

    Works against :class:`Exception`, plain ``str``, and any object that
    converts sensibly via ``str()`` — handles HTTP status codes too.
    """
    err_str = str(err).lower()
    if any(tag in err_str for tag in _rate_limit_tags()):
        return True
    status = getattr(err, "status_code", None)
    if status is not None:
        try:
            return int(status) == 429
        except (ValueError, TypeError):
            pass
    return False


# Lazily-initialized aiohttp session shared by all providers.
_aiohttp_session: Optional["aiohttp.ClientSession"] = None


def _ensure_session():
    """Return a shared aiohttp ClientSession with connection pooling.

    Configures a :class:`aiohttp.TCPConnector` with sane defaults:
    * **limit=100**          – hard cap on total open connections
    * **limit_per_host=10**  – max concurrent connections per remote host
    * **ttl_dns_cache=300**  – DNS cache TTL in seconds
    * **use_dns_cache=True** – resolve once, reuse across requests
    * **force_close=False**  – let TCP keep-alive drain sockets naturally

    Timeout: 300 s total / 10 s connect / 60 s socket read -- generous enough
    for slow LLM streams without risking resource exhaustion.
    """
    global _aiohttp_session
    if _aiohttp_session is None or _aiohttp_session.closed:
        import aiohttp

        connector = aiohttp.TCPConnector(
            limit=100,
            limit_per_host=10,
            ttl_dns_cache=300,
            use_dns_cache=True,
            force_close=False,
        )
        _aiohttp_session = aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=300, connect=10, sock_read=60),
        )
    return _aiohttp_session


class BaseProvider(ABC):
    """Abstract provider. Subclasses implement chat / chat_stream / (optionally) embed."""

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config
        self.name = config.name

    # ── abstract methods ────────────────────────────────────────────────

    @abstractmethod
    def chat(
        self,
        prompt: str,
        system_prompt: Optional[str],
        model: str,
        temperature: float = 0.3,
        timeout: int = 30,
    ) -> str:
        """Sync chat completion. Returns the model text response."""
        ...

    @abstractmethod
    async def chat_stream(
        self,
        system_prompt: Optional[str],
        user_message: str,
        model: str,
        temperature: float = 0.3,
        timeout: int = 60,
    ) -> AsyncGenerator[str, None]:
        """Async streaming chat. Yields response tokens as strings."""
        ...

    async def embed(self, text: str) -> List[float]:
        """Async embedding. Not all providers support this."""
        raise NotImplementedError(f"{self.name} does not implement embed()")

    # ── shared helpers ──────────────────────────────────────────────────

    def _post_json(self, url: str, payload: dict, headers: dict, timeout: int) -> dict:
        """Sync POST via urllib; returns parsed JSON."""
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
