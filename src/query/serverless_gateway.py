"""
serverless_gateway.py — Gateway for direct OpenRouter/Gemini API calls in serverless environments.
Fallback routing for serverless deployments where local LiteLLM proxy process is absent.
Routing: OpenRouter (primary) → Gemini Direct API (fallback).
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
        # Use longer timeout for streaming LLM calls
        conn = aiohttp.TCPConnector(limit=10, force_close=True)
        _aiohttp_session = aiohttp.ClientSession(
            connector=conn,
            timeout=aiohttp.ClientTimeout(total=60),
        )
    return _aiohttp_session

load_dotenv()

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
GEMINI_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"


def call_serverless_llm(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: str = "nvidia/nemotron-3-super-120b-a12b:free",
    temperature: float = 0.3,
    timeout: int = 30,
) -> str:
    """
    Call an external LLM API directly (OpenRouter or Gemini) without relying on local LiteLLM proxy.
    Used during serverless deployment or when local proxy is unreachable.

    Routing: OpenRouter (primary, Nemotron 120B) → Gemini Direct API (fallback, gemini-2.5-flash).
    """
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GRAPHRAG_API_KEY")

    if openrouter_key:
        try:
            return _call_openrouter(prompt, system_prompt, model, openrouter_key, temperature=temperature, timeout=timeout)
        except Exception as err:
            print(f"[WARN] OpenRouter call failed ({err}). Falling back to Gemini Direct API...")

    if gemini_key:
        return _call_gemini_direct(prompt, system_prompt, gemini_key, temperature=temperature, timeout=timeout)
    else:
        raise ValueError("Neither OPENROUTER_API_KEY nor GEMINI_API_KEY environment variable is set for serverless gateway.")


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
    fallback_models = ["gemini-2.5-flash", "gemini-2.0-flash"]
    last_err = None
    full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
    payload = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {"temperature": temperature},
    }
    data = json.dumps(payload).encode("utf-8")

    for model in fallback_models:
        url = GEMINI_URL_TEMPLATE.format(model=model, api_key=api_key)
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
    model: str = "nvidia/nemotron-3-super-120b-a12b:free",
    temperature: float = 0.3,
    timeout: int = 60,
) -> AsyncGenerator[str, None]:
    """Stream LLM response token-by-token (OpenRouter → Gemini fallback)."""
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GRAPHRAG_API_KEY")

    if openrouter_key:
        try:
            async for token in _stream_openrouter(system_prompt, user_message, model, openrouter_key, temperature, timeout):
                yield token
            return
        except Exception as err:
            print(f"[WARN] OpenRouter streaming failed ({err}). Falling back...")

    if gemini_key:
        try:
            async for token in _stream_gemini(system_prompt, user_message, gemini_key, temperature, timeout):
                yield token
            return
        except Exception as err:
            raise RuntimeError(f"Gemini streaming failed: {err}") from err

    raise ValueError("Neither OPENROUTER_API_KEY nor GEMINI_API_KEY set.")


# ── private embedding helpers ─────────────────────────────────────────────

async def _openrouter_embed(text: str, api_key: str) -> List[float]:
    import aiohttp
    session = _ensure_session()
    payload = {
        "model": "nvidia/nemotron-embed-vl-1b-v2",
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
    import aiohttp
    session = _ensure_session()
    payload = {"contents": [{"parts": [{"text": text}]}]}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/llama-nemotron-embed-vl-1b-v2:embedContent?key={api_key}"
    async with session.post(url, json=payload, headers={"Content-Type": "application/json"}) as resp:
        data = json.loads(await resp.text())
        return data["embedding"]["values"]


# ── private streaming helpers ─────────────────────────────────────────────

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
    full_prompt = f"{system_prompt}\n\n{user_message}" if system_prompt else user_message
    models = ["gemini-2.5-flash", "gemini-2.0-flash"]
    for model_name in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:streamGenerateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {"temperature": temperature},
        }
        async with session.post(url, json=payload) as resp:
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
            # If no streaming happened, fall back to non-streaming
            content = buffer.split("data: ")
            if all("candidates" not in b for b in content if b.strip().startswith("{")):
                # Retry non-streaming as fallback
                ns_payload = {
                    "contents": [{"parts": [{"text": full_prompt}]}],
                    "generationConfig": {"temperature": temperature},
                }
                url_nons = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
                async with session.post(url_nons, json=ns_payload) as r2:
                    data = json.loads(await r2.text())
                    texts = []
                    for c in data.get("candidates", []):
                        for p in c.get("content", {}).get("parts", []):
                            if "text" in p:
                                texts.append(p["text"])
                    yield "".join(texts)
            break  # succeeded on first model
