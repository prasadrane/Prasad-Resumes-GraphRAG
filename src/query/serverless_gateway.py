"""
serverless_gateway.py — Gateway for direct OpenRouter/Gemini API calls in serverless environments.
Fallback routing for serverless deployments where local LiteLLM proxy process is absent.
"""

import os
import urllib.request
import json
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
GEMINI_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

def call_serverless_llm(prompt: str, system_prompt: Optional[str] = None, model: str = "google/gemini-2.5-flash-lite") -> str:
    """
    Call an external LLM API directly (OpenRouter or Gemini) without relying on local LiteLLM proxy.
    Used during serverless deployment or when local proxy is unreachable.
    """
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GRAPHRAG_API_KEY")

    if openrouter_key:
        try:
            return _call_openrouter(prompt, system_prompt, model, openrouter_key)
        except Exception as err:
            print(f"[WARN] OpenRouter call failed ({err}). Falling back to Gemini Direct API...")

    if gemini_key:
        return _call_gemini_direct(prompt, system_prompt, gemini_key)
    else:
        raise ValueError("Neither OPENROUTER_API_KEY nor GEMINI_API_KEY environment variable is set for serverless gateway.")

def _call_openrouter(prompt: str, system_prompt: Optional[str], model: str, api_key: str) -> str:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        OPENROUTER_URL,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        res_data = json.loads(resp.read().decode("utf-8"))
        return res_data["choices"][0]["message"]["content"]

def _call_gemini_direct(prompt: str, system_prompt: Optional[str], api_key: str) -> str:
    url = GEMINI_URL_TEMPLATE.format(model="gemini-2.5-flash-lite", api_key=api_key)
    full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
    payload = {
        "contents": [{"parts": [{"text": full_prompt}]}]
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        res_data = json.loads(resp.read().decode("utf-8"))
        return res_data["candidates"][0]["content"]["parts"][0]["text"]
