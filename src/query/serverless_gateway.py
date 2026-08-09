"""
serverless_gateway.py — Gateway for direct OpenRouter/Gemini API calls in serverless environments.
Fallback routing for serverless deployments where local LiteLLM proxy process is absent.
Routing: OpenRouter (primary) → Gemini Direct API (fallback).
"""

import os
import urllib.request
import json
from typing import Optional, Dict, Any
from dotenv import load_dotenv

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
