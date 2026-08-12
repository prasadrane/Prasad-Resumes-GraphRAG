"""
serverless_gateway.py — Gateway for LLM API calls in serverless environments.
Fallback routing for serverless deployments where local LiteLLM proxy process is absent.
Routing: Alibaba Cloud Token Plan (primary, qwen3.6-flash) → OpenRouter (fallback) → Gemini (last resort).
"""

import os
import sys
import json
import asyncio
import urllib.request
from typing import AsyncGenerator, List, Optional, Dict, Any
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent if "src/query" in str(Path(__file__).resolve().parent.parent) else Path.cwd()
)
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Lazy-init aiohttp session so we never leak it across event loops.
_aiohttp_session: Optional["aiohttp.ClientSession"] = None


def _ensure_session():
    """Return a shared aiohttp ClientSession (one per event loop)."""
    global _aiohttp_session
    if _aiohttp_session is None or _aiohttp_session.closed:
        import aiohttp
        # Use longer timeout for LLM calls (up to 5 minutes for resume tailoring)
        conn = aiohttp.TCPConnector(limit=10, force_close=True)
        _aiohttp_session = aiohttp.ClientSession(
            connector=conn,
            timeout=aiohttp.ClientTimeout(total=300),
        )
    return _aiohttp_session

load_dotenv()

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
GEMINI_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
# Anthropic-compatible endpoint (same as Claude Code uses) - faster than OpenAI-compatible
ALIBABA_ANTHROPIC_URL = "https://token-plan.ap-southeast-1.maas.aliyuncs.com/apps/anthropic/v1/messages"
ALIBABA_MODEL = "qwen3.6-flash"  # Fast/cheap model for chatbot
ALIBABA_RESUME_MODEL = "qwen3.7-plus"  # More capable model for resume tailoring


def call_serverless_llm(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: str = ALIBABA_MODEL,
    temperature: float = 0.3,
    timeout: int = 30,
) -> str:
    """
    Call an external LLM API directly without relying on local LiteLLM proxy.
    Used during serverless deployment or when local proxy is unreachable.

    Routing: Alibaba Cloud Token Plan (primary, qwen3.6-flash) → OpenRouter (fallback) → Gemini (last resort).
    """
    alibaba_key = os.getenv("ALIBABA_API_KEY")
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GRAPHRAG_API_KEY")

    # Alibaba first — fast, cheap (qwen3.6-flash)
    if alibaba_key:
        try:
            return _call_alibaba(prompt, system_prompt, model, alibaba_key, temperature=temperature, timeout=timeout)
        except Exception as err:
            print(f"[WARN] Alibaba call failed ({err}). Falling back to OpenRouter...")

    # OpenRouter fallback
    if openrouter_key:
        try:
            return _call_openrouter(prompt, system_prompt, "nvidia/nemotron-3-super-120b-a12b:free", openrouter_key, temperature=temperature, timeout=timeout)
        except Exception as err:
            print(f"[WARN] OpenRouter call failed ({err}). Falling back to Gemini...")

    # Gemini last resort
    if gemini_key:
        return _call_gemini_direct(prompt, system_prompt, gemini_key, temperature=temperature, timeout=timeout)
    else:
        raise ValueError("Neither OPENROUTER_API_KEY nor GEMINI_API_KEY environment variable is set for serverless gateway.")


def _call_alibaba(
    prompt: str,
    system_prompt: Optional[str],
    model: str,
    api_key: str,
    temperature: float = 0.3,
    timeout: int = 30,
) -> str:
    """Call Alibaba Cloud Token Plan API via Anthropic-compatible endpoint (faster than OpenAI-compatible)."""
    payload = {
        "model": model,
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system_prompt:
        payload["system"] = system_prompt
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        ALIBABA_ANTHROPIC_URL,
        data=data,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        res_data = json.loads(resp.read().decode("utf-8"))
        # Extract text from content blocks (skip thinking blocks)
        for block in res_data.get("content", []):
            if block.get("type") == "text":
                return block.get("text", "")
        return ""


def _call_openrouter(
    prompt: str,
    system_prompt: Optional[str],
    model: str,
    api_key: str,
    temperature: float = 0.3,
    timeout: int = 30,
) -> str:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        OPENROUTER_URL,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        res_data = json.loads(resp.read().decode("utf-8"))
        return res_data["choices"][0]["message"]["content"]


def _call_gemini_direct(
    prompt: str,
    system_prompt: Optional[str],
    api_key: str,
    temperature: float = 0.3,
    timeout: int = 30,
) -> str:
    fallback_models = ["gemini-2.5-flash"]
    last_err = None

    for model in fallback_models:
        url = GEMINI_URL_TEMPLATE.format(model=model, api_key=api_key)
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature},
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}
        data = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                return res_data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            err_str = str(e)
            # Detect rate limiting (429) and fail fast instead of retrying
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
                raise RuntimeError(f"Gemini rate limited: {e}") from e
            last_err = e
            continue

    raise RuntimeError(f"All Gemini Direct API models failed. Last error: {last_err}")


# ── embedding & streaming helpers for GraphRAG engine ──────────────────────


async def _litellm_embed(text: str, api_key: str) -> List[float]:
    """Get embedding via the local LiteLLM proxy (OpenAI-compatible /v1/embeddings)."""
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
        emb = data["data"][0]["embedding"]
        # Enforce expected dimension by truncating/padding
        target_dim = 2048
        if len(emb) > target_dim:
            emb = list(emb[:target_dim])
        elif len(emb) < target_dim:
            emb = emb + [0.0] * (target_dim - len(emb))
        return emb


async def get_embedding(text: str) -> List[float]:
    """Get a text embedding via OpenRouter → LiteLLM proxy → Gemini Direct."""
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GRAPHRAG_API_KEY")

    # Primary: OpenRouter /v1/embeddings with llama-nemotron (2048-dim, matches LanceDB)
    if openrouter_key:
        try:
            return await _openrouter_embed(text, openrouter_key)
        except Exception as err:
            print(f"[WARN] OpenRouter embed failed ({err}). Trying fallback…")

    # Fallback: LiteLLM proxy (may produce different dimensions, handled internally)
    if gemini_key:
        try:
            return await _litellm_embed(text, gemini_key)
        except Exception as err:
            print(f"[WARN] LiteLLM proxy embed failed ({err}). Trying Gemini direct…")

    # Last resort: Gemini Direct
    if gemini_key:
        try:
            return await _gemini_embed(text, gemini_key)
        except Exception as err:
            raise RuntimeError(f"Gemini embedding failed: {err}") from err

    raise ValueError("Neither OPENROUTER_API_KEY nor GEMINI_API_KEY set.")


async def call_serverless_llm_stream(
    system_prompt: Optional[str],
    user_message: str,
    model: str = ALIBABA_MODEL,
    temperature: float = 0.3,
    timeout: int = 60,
) -> AsyncGenerator[str, None]:
    """Stream LLM response token-by-token (Alibaba primary → OpenRouter fallback → Gemini)."""
    alibaba_key = os.getenv("ALIBABA_API_KEY")
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GRAPHRAG_API_KEY")

    # Alibaba first — fast, cheap
    if alibaba_key:
        try:
            async for token in _stream_alibaba(system_prompt, user_message, model, alibaba_key, temperature, timeout):
                yield token
            return
        except Exception as err:
            print(f"[WARN] Alibaba streaming failed ({err}). Falling back to OpenRouter...")

    if openrouter_key:
        try:
            async for token in _stream_openrouter(system_prompt, user_message, "nvidia/nemotron-3-super-120b-a12b:free", openrouter_key, temperature, timeout):
                yield token
            return
        except Exception as err:
            print(f"[WARN] OpenRouter streaming failed ({err}). Falling back to Gemini...")

    if gemini_key:
        async for token in _stream_gemini(system_prompt, user_message, gemini_key, temperature, timeout):
            yield token
        return

    raise ValueError("No API keys set (ALIBABA_API_KEY, OPENROUTER_API_KEY, or GEMINI_API_KEY).")


# ── private embedding helpers ─────────────────────────────────────────────

async def _openrouter_embed(text: str, api_key: str) -> List[float]:
    import aiohttp
    session = _ensure_session()
    payload = {
        "model": "nvidia/nemotron-3-embed-1b:free",
        "input": [text],
        "encoding_format": "float",
    }
    async with session.post(
        "https://openrouter.ai/api/v1/embeddings",
        json=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    ) as resp:
        data = json.loads(await resp.text())
        return data["data"][0]["embedding"]


async def _gemini_embed(text: str, api_key: str) -> List[float]:
    """Fallback embedding via Gemini text-embedding-004 (768-dim, padded to 2048)."""
    import aiohttp
    session = _ensure_session()
    payload = {"contents": [{"parts": [{"text": text}]}]}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={api_key}"
    async with session.post(url, json=payload, headers={"Content-Type": "application/json"}) as resp:
        data = json.loads(await resp.text())
        emb = data["embedding"]["values"]
        # Pad/truncate to 2048 to match LanceDB index dimensions
        target_dim = 2048
        if len(emb) > target_dim:
            emb = list(emb[:target_dim])
        elif len(emb) < target_dim:
            emb = emb + [0.0] * (target_dim - len(emb))
        return emb


# ── private streaming helpers ─────────────────────────────────────────────

async def _stream_alibaba(
    system_prompt: Optional[str],
    user_message: str,
    model: str,
    api_key: str,
    temperature: float,
    timeout: int,
) -> AsyncGenerator[str, None]:
    """Stream from Alibaba Cloud Token Plan via Anthropic-compatible endpoint."""
    import aiohttp
    session = _ensure_session()
    payload = {
        "model": model,
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": user_message}],
        "stream": True,
    }
    if system_prompt:
        payload["system"] = system_prompt
    async with session.post(
        ALIBABA_ANTHROPIC_URL,
        json=payload,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
    ) as resp:
        if resp.status == 429:
            error_text = await resp.text()
            raise RuntimeError(f"Alibaba rate limited (429): {error_text}")
        # Anthropic SSE format: event:xxx followed by data:{json}
        current_event = None
        async for line_bytes in resp.content:
            line = line_bytes.decode().strip()
            if line.startswith("event:"):
                current_event = line[6:].strip()
            elif line.startswith("data:"):
                data = line[5:].strip()
                try:
                    chunk = json.loads(data)
                    # Extract text from content_block_delta events (skip thinking blocks)
                    if chunk.get("type") == "content_block_delta":
                        delta = chunk.get("delta", {})
                        # text_delta is for actual text output, thinking_delta is for thinking
                        if delta.get("type") == "text_delta":
                            yield delta.get("text", "")
                except json.JSONDecodeError:
                    pass


async def _stream_openrouter(
    system_prompt: Optional[str],
    user_message: str,
    model: str,
    api_key: str,
    temperature: float,
    timeout: int,
) -> AsyncGenerator[str, None]:
    import aiohttp
    session = _ensure_session()
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_message})
    payload = {"model": model, "messages": messages, "temperature": temperature, "stream": True}
    async with session.post(
        OPENROUTER_URL, json=payload, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    ) as resp:
        async for line_bytes in resp.content:
            line = line_bytes.decode().strip()
            if not line.startswith("data: "):
                continue
            payload_text = line[6:]
            if payload_text.strip() == "[DONE]":
                return
            try:
                chunk = json.loads(payload_text)
                tokens = chunk.get("choices", [])
                for choice in tokens:
                    delta = choice.get("delta", {})
                    token = delta.get("content", "")
                    if token:
                        yield token
            except json.JSONDecodeError:
                pass


async def _stream_gemini(
    system_prompt: Optional[str],
    user_message: str,
    api_key: str,
    temperature: float,
    timeout: int,
) -> AsyncGenerator[str, None]:
    import aiohttp
    session = _ensure_session()
    model_name = "gemini-2.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:streamGenerateContent?key={api_key}&alt=sse"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": user_message}]}],
        "generationConfig": {"temperature": temperature},
    }
    if system_prompt:
        payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

    async with session.post(url, json=payload) as resp:
        # Check for rate limiting in response
        if resp.status == 429:
            error_text = await resp.text()
            raise RuntimeError(f"Gemini rate limited (429): {error_text}")

        # Gemini SSE format — each `data:` line is a JSON chunk
        buffer = ""
        async for line_bytes in resp.content:
            line = line_bytes.decode()
            buffer += line
            if line.startswith("data: "):
                payload_text = line[6:].strip()
                if payload_text:
                    try:
                        chunk = json.loads(payload_text)
                        candidates = chunk.get("candidates", [])
                        for c in candidates:
                            parts = c.get("content", {}).get("parts", [])
                            for p in parts:
                                if "text" in p:
                                    yield p["text"]
                    except json.JSONDecodeError:
                        pass
