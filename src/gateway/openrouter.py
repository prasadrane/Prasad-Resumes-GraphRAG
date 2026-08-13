"""OpenRouter provider — OpenAI-compatible protocol."""

import json
from typing import AsyncGenerator, List, Optional

from src.config.providers import ProviderConfig
from .base import BaseProvider, _ensure_session


class OpenRouterProvider(BaseProvider):
    """OpenRouter: OpenAI-compatible /chat/completions + /embeddings."""

    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config)

    def _chat_url(self) -> str:
        base = self.config.base_url.rstrip("/")
        return f"{base}/chat/completions"

    def _embed_url(self) -> str:
        return f"{self.config.base_url.rstrip('/')}/embeddings"

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.config.get_api_key()}",
            "Content-Type": "application/json",
        }

    # ── sync chat ───────────────────────────────────────────────────────

    def chat(
        self,
        prompt: str,
        system_prompt: Optional[str],
        model: str,
        temperature: float = 0.3,
        timeout: int = 30,
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        payload = {"model": model, "messages": messages, "temperature": temperature}
        res = self._post_json(self._chat_url(), payload, self._headers(), timeout)
        return res["choices"][0]["message"]["content"]

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
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})
        payload = {"model": model, "messages": messages, "temperature": temperature, "stream": True}
        async with session.post(
            self._chat_url(), json=payload, headers=self._headers(),
        ) as resp:
            async for raw in resp.content:
                line = raw.decode().strip()
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                if data.strip() == "[DONE]":
                    return
                try:
                    chunk = json.loads(data)
                    for choice in chunk.get("choices", []):
                        token = choice.get("delta", {}).get("content", "")
                        if token:
                            yield token
                except json.JSONDecodeError:
                    pass

    # ── embedding ───────────────────────────────────────────────────────

    async def embed(self, text: str) -> List[float]:
        """nvidia/nemotron-3-embed-1b:free via /v1/embeddings."""
        session = _ensure_session()
        payload = {
            "model": "nvidia/nemotron-3-embed-1b:free",
            "input": [text],
            "encoding_format": "float",
        }
        async with session.post(
            self._embed_url(), json=payload, headers=self._headers(),
        ) as resp:
            data = json.loads(await resp.text())
            return data["data"][0]["embedding"]
