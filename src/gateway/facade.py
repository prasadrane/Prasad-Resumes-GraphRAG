"""Gateway facade — provider cache, failover orchestration, public API.

This module is the single entry-point for callers that want to talk to an LLM
or get an embedding. It owns:

- A lazily-populated cache of provider instances (:func:`_client`)
- The sync failover chain (:func:`_try_chain`, moved verbatim from
  serverless_gateway.py: skip empty-string results, forward rate-limit errors
  immediately, RuntimeError only when all providers fail)
- Streaming / embedding failover wrappers (streaming uses a consumed-flag
  loop; embedding is sequential try/except with WARN logging)
- The legacy public API: ``call_serverless_llm``, ``call_serverless_llm_stream``,
  ``get_embedding``

Sync chat calls stay on ``urllib`` (no asyncio bridge on the Vercel hot path).
Streaming + embedding use ``aiohttp`` via the shared session in ``base.py``.
"""

import functools
import json
import logging
import os
import time
from typing import Any, AsyncGenerator, Callable, List, Optional

from src.config.providers import get_model_for, get_provider
from .base import BaseProvider, _ensure_session, pad_embedding, is_rate_limit_error
from .alibaba import AlibabaProvider
from .circuit_breaker import CircuitBreaker, ProviderCircuitOpen
from .openrouter import OpenRouterProvider
from .gemini import GeminiProvider


log = logging.getLogger(__name__)


# ── Provider cache ─────────────────────────────────────────────────────────

_PROVIDER_CLASSES = {
    "alibaba": AlibabaProvider,
    "openrouter": OpenRouterProvider,
    "gemini": GeminiProvider,
}
# Failover order for chat / streaming — matches the original chain.
_CHAT_CHAIN_ORDER = ("alibaba", "openrouter", "gemini")

# Circuit-breaker registry keyed by provider name — lazily initialized.
_circuit_breakers: dict[str, CircuitBreaker] = {}

_client_cache: dict[str, BaseProvider] = {}


def _client(name: str) -> BaseProvider:
    """Return a cached provider instance by name."""
    if name not in _client_cache:
        if name not in _PROVIDER_CLASSES:
            raise ValueError(f"Unknown provider '{name}'")
        _client_cache[name] = _PROVIDER_CLASSES[name](get_provider(name))
    return _client_cache[name]


def _breaker(name: str) -> CircuitBreaker:
    """Return (or create) the circuit breaker for *name*."""
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(
            name=name,
            failure_threshold=3,
            recovery_timeout=30,
        )
    return _circuit_breakers[name]


def _has_key(name: str) -> bool:
    try:
        get_provider(name).get_api_key()
        return True
    except ValueError:
        return False


# ── Sync failover (moved verbatim from serverless_gateway.py) ──────────────

def _is_empty_response(res) -> bool:
    return isinstance(res, str) and res.strip() == ""


def _try_chain(primary_fn, *fallback_fns, max_retries: int = 1):
    """Try a sequence of callables, returning the first success.

    Empty-string results are treated as wrong-endpoint signals and trigger
    continuation to the next provider. Rate-limit errors are forwarded
    immediately via :func:`base.is_rate_limit_error`.
    ``RuntimeError`` only when every callable fails every time.
    """
    for fn in (primary_fn,) + fallback_fns:
        for _ in range(max_retries + 1):
            try:
                res = fn()
                if _is_empty_response(res):
                    continue
                return res
            except Exception as err:
                if is_rate_limit_error(err):
                    raise
    raise RuntimeError("All providers in the fallback chain failed.")


# ── Retry with Exponential Backoff ──────────────────────────────────────────

def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
):
    """Decorator that retries a callable on transient errors with exponential backoff.

    Applies to *network* and *timeout* errors (not rate-limit or semantic failures).
    Delay doubles each attempt: ``base_delay * 2^attempt``.
    Rate-limit errors pass through immediately.
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: BaseException | None = None
            for attempt in range(max_retries + 1):
                try:
                    return fn(*args, **kwargs)
                except Exception as err:
                    # Never retry rate-limit errors — caller needs them now
                    if is_rate_limit_error(err):
                        raise
                    # Never retry circuit-breaker rejections — provider is tripped, move to next
                    if isinstance(err, ProviderCircuitOpen):
                        raise
                    last_exc = err
                    if attempt < max_retries:
                        delay = base_delay * (2 ** attempt)
                        log.warning(
                            "[RETRY] %s failed (attempt %d/%d): %s — backing off %.1fs",
                            fn.__qualname__,
                            attempt + 1,
                            max_retries,
                            err,
                            delay,
                        )
                        time.sleep(delay)
            raise RuntimeError(
                f"{fn.__qualname__} failed after {max_retries} retries: {last_exc}"
            ) from last_exc

        return wrapper

    return decorator


# ── LiteLLM proxy embed (kept for chain parity; not a provider call) ──────

async def _litellm_embed(text: str, api_key: str) -> List[float]:
    """Embed via local LiteLLM proxy (OpenAI-compatible /v1/embeddings).

    Retained for backward compatibility with the existing embedding chain.
    In serverless (Vercel) deployments the local proxy is unreachable, so this
    call will fail and the chain will continue to the Gemini fallback.
    """
    import aiohttp
    session = _ensure_session()
    payload = {
        "model": "llama-nemotron-embed-vl-1b-v2",
        "input": [text],
        "encoding_format": "float",
    }
    async with session.post(
        "http://localhost:8002/v1/embeddings",
        json=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    ) as resp:
        data = json.loads(await resp.text())
        if "data" not in data or len(data["data"]) == 0:
            raise ValueError(f"Unexpected LiteLLM embedding response: {data}")
        return pad_embedding(data["data"][0]["embedding"])


def _get_ordered_chat_providers() -> List[str]:
    """Return available chat providers sorted by circuit health and moving average latency."""
    available = [n for n in _CHAT_CHAIN_ORDER if _has_key(n)]
    def sort_key(name: str):
        cb = _breaker(name)
        state_order = 0 if cb.state.value == "closed" else (1 if cb.state.value == "half_open" else 2)
        latency = cb.avg_latency if cb.avg_latency > 0 else 1.0
        return (state_order, latency)
    return sorted(available, key=sort_key)


# ── Public API ─────────────────────────────────────────────────────────────

def call_serverless_llm(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.3,
    timeout: int = 30,
) -> str:
    """Sync chat completion — health & latency aware failover across providers.

    Each provider is governed by a :class:`CircuitBreaker` so that
    persistently failing providers are skipped automatically.  Transient
    network errors within a single provider are retried with exponential
    backoff (up to 3 retries).
    """
    if not any(_has_key(n) for n in _CHAT_CHAIN_ORDER):
        raise ValueError(
            "Neither OPENROUTER_API_KEY nor GEMINI_API_KEY environment variable "
            "is set for serverless gateway."
        )

    def make_safe_fn(name: str):
        provider = _client(name)
        # Each provider uses its own chat model (or explicit model if provided)
        if model:
            provider_model = model
        else:
            provider_config = get_provider(name)
            provider_model = provider_config.models.get("chat")
            if not provider_model:
                raise ValueError(f"Provider '{name}' has no chat model configured")

        @retry_with_backoff(max_retries=3, base_delay=1.0)
        def call_with_retry():
            return _do_chat(provider, prompt, system_prompt, provider_model, temperature, timeout)

        return call_with_retry

    fns = [make_safe_fn(n) for n in _get_ordered_chat_providers()]
    if not fns:
        raise RuntimeError("No providers configured with valid API keys.")
    return _try_chain(*fns)


def _do_chat(provider, prompt, system_prompt, model, temperature, timeout):
    """Execute a chat call through the current provider's circuit breaker."""
    cb = _breaker(provider.name)
    return cb.call(
        lambda: provider.chat(prompt, system_prompt, model, temperature, timeout),
    )


async def call_serverless_llm_stream(
    system_prompt: Optional[str],
    user_message: str,
    model: Optional[str] = None,
    temperature: float = 0.3,
    timeout: int = 60,
) -> AsyncGenerator[str, None]:
    """Streaming chat — yields tokens from the first healthy provider that returns any."""
    any_attempted = False
    last_error: Optional[Exception] = None

    for name in _get_ordered_chat_providers():
        if not _has_key(name):
            continue
        any_attempted = True
        provider = _client(name)
        # Each provider uses its own chat model (or explicit model if provided)
        if model:
            provider_model = model
        else:
            provider_config = get_provider(name)
            provider_model = provider_config.models.get("chat")
            if not provider_model:
                last_error = ValueError(f"Provider '{name}' has no chat model configured")
                continue

        try:
            gen = provider.chat_stream(system_prompt, user_message, provider_model, temperature, timeout)
            consumed = False
            try:
                while True:
                    tok = await gen.__anext__()
                    yield tok
                    consumed = True
            except StopAsyncIteration:
                if consumed:
                    return  # successfully yielded at least one token
                # Provider yielded 0 tokens — treat as empty response, try next
                last_error = RuntimeError(f"Provider '{name}' returned empty response")
                continue
        except Exception as err:
            # If we already yielded tokens, re-raise — don't garble output with next provider
            if consumed:
                raise
            # Provider raised an error before yielding — track it and try next
            last_error = err
            continue
        break

    if not any_attempted:
        raise ValueError(
            "No API keys set (ALIBABA_API_KEY, OPENROUTER_API_KEY, or GEMINI_API_KEY)."
        )
    # All providers failed — raise the last error with context
    if last_error:
        raise RuntimeError(f"All streaming providers failed. Last error: {last_error}") from last_error
    raise RuntimeError("All streaming providers in the chain failed.")


async def get_embedding(text: str) -> List[float]:
    """Get a text embedding via openrouter → litellm proxy → gemini direct."""
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GRAPHRAG_API_KEY")

    if openrouter_key:
        try:
            return await _client("openrouter").embed(text)
        except Exception as err:
            log.warning("[WARN] OpenRouter embed failed (%s). Trying fallback…", err)

    if gemini_key:
        try:
            return await _litellm_embed(text, gemini_key)
        except Exception as err:
            log.warning("[WARN] LiteLLM proxy embed failed (%s). Trying Gemini direct…", err)

    if gemini_key:
        try:
            return await _client("gemini").embed(text)
        except Exception as err:
            raise RuntimeError(f"Gemini embedding failed: {err}") from err

    raise ValueError("Neither OPENROUTER_API_KEY nor GEMINI_API_KEY set.")
