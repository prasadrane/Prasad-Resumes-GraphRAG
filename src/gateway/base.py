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
import urllib.request
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, Union

from src.config.llm_constants import (
    DEFAULT_EMBEDDING_DIM,
    EMBEDDING_DIM,
    LLM_MAX_TOKENS,
    RATE_LIMIT_TAGS,
)
from src.config.providers import ProviderConfig

logger = logging.getLogger(__name__)


# ── Shared Embedding & Error Helpers ────────────────────────────────────────

def pad_embedding(emb: List[float], target_dim: int | None = None) -> List[float]:
    """Pad or truncate an embedding list to *target_dim* (default EMBEDDING_DIM).

    Returns a *new* list so callers' original data is never mutated.
    """
    dim = target_dim if target_dim is not None else EMBEDDING_DIM
    length = len(emb)
    if length == dim:
        return list(emb)
    if length > dim:
        return list(emb[:dim])
    padded = list(emb)
    padded.extend([0.0] * (dim - length))
    return padded


def is_rate_limit_error(err: BaseException | Exception | str) -> bool:
    """Return ``True`` when *err* represents a rate-limit / throttling error.

    Works against :class:`Exception`, plain ``str``, and any object that
    converts sensibly via ``str()`` — handles HTTP status codes too.
    """
    err_str = str(err).lower()
    if any(tag in err_str for tag in RATE_LIMIT_TAGS):
        return True
    status = getattr(err, "status_code", None)
    if status is not None:
        try:
            return int(status) == 429
        except (ValueError, TypeError):
            pass
    return False


# ── Shared SSE Stream Parser ────────────────────────────────────────────────

async def parse_sse_stream(
    content_stream: Any,
    extract_fn: Callable[[Dict[str, Any]], Optional[Union[str, List[str]]]],
) -> AsyncGenerator[str, None]:
    """Parse Server-Sent Events (SSE) from an async byte/string stream.

    Handles line decoding, 'data:' prefix stripping, [DONE] termination,
    and JSON parsing. Calls *extract_fn(chunk_dict)* to yield extracted tokens.
    """
    async for raw in content_stream:
        if isinstance(raw, (bytes, bytearray)):
            line = raw.decode("utf-8", errors="replace").strip()
        else:
            line = str(raw).strip()

        if not line.startswith("data:"):
            continue

        data = line[5:].strip()
        if not data or data == "[DONE]":
            if data == "[DONE]":
                return
            continue

        try:
            chunk = json.loads(data)
            tokens = extract_fn(chunk)
            if tokens is not None:
                if isinstance(tokens, list):
                    for tok in tokens:
                        if tok:
                            yield tok
                elif isinstance(tokens, str) and tokens:
                    yield tokens
        except (json.JSONDecodeError, KeyError, TypeError, IndexError):
            pass


# ── Shared Aiohttp Session Pool ─────────────────────────────────────────────

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
