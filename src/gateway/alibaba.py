"""Alibaba Cloud Token Plan provider — Anthropic-compatible Messages protocol."""

import json
import sys
from typing import AsyncGenerator, Optional

from src.config.providers import ProviderConfig
from .base import BaseProvider, _ensure_session

# Lazy constant resolution to avoid circular imports at module load time.
_DEFAULT_MAX_TOKENS = 4096

def _max_tokens():
    try:
        mod = sys.modules.get("src.generators.constants")
        if mod is not None:
            return getattr(mod, "LLM_MAX_TOKENS", _DEFAULT_MAX_TOKENS)
    except Exception:
        pass
    return _DEFAULT_MAX_TOKENS


class AlibabaProvider(BaseProvider):
    """Alibaba via the Anthropic-compatible endpoint (not the OpenAI-compatible base_url)."""

    # Fixed Anthropic-compatible path — differs from config.base_url.
    URL = "https://token-plan.ap-southeast-1.maas.aliyuncs.com/apps/anthropic/v1/messages"

    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config)

    # ── sync chat ───────────────────────────────────────────────────────

    def chat(
        self,
        prompt: str,
        system_prompt: Optional[str],
        model: str,
        temperature: float = 0.3,
        timeout: int = 30,
    ) -> str:
        payload = {
            "model": model,
            "max_tokens": _max_tokens(),
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            payload["system"] = system_prompt
        res = self._post_json(
            self.URL,
            payload,
            headers={
                "x-api-key": self.config.get_api_key(),
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )
        # Iterate content blocks; skip "thinking" blocks, return first "text" block.
        for block in res.get("content", []):
            if block.get("type") == "text":
                return block.get("text", "")
        return ""

    # ── streaming ───────────────────────────────────────────────────────

    async def chat_stream(
        self,
        system_prompt: Optional[str],
        user_message: str,
        model: str,
        temperature: float = 0.3,
        timeout: int = 60,
    ) -> AsyncGenerator[str, None]:
        session = _ensure_session()
        payload = {
            "model": model,
            "max_tokens": _max_tokens(),
            "messages": [{"role": "user", "content": user_message}],
            "stream": True,
        }
        if system_prompt:
            payload["system"] = system_prompt
        async with session.post(
            self.URL,
            json=payload,
            headers={
                "x-api-key": self.config.get_api_key(),
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
        ) as resp:
            if resp.status == 429:
                err = await resp.text()
                raise RuntimeError(f"Alibaba rate limited (429): {err}")
            async for raw in resp.content:
                line = raw.decode().strip()
                if not line.startswith("data:"):
                    continue
                try:
                    chunk = json.loads(line[5:].strip())
                    if chunk.get("type") == "content_block_delta":
                        delta = chunk.get("delta", {})
                        if delta.get("type") == "text_delta":
                            yield delta.get("text", "")
                except json.JSONDecodeError:
                    pass
