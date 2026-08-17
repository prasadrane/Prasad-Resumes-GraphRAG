"""Google Gemini Direct provider — Google REST protocol.

Auth is via query parameter (``?key=...``) — no Authorization header.
The ``base_url`` in :class:`ProviderConfig` is the OpenAI-compatible path
(reserved for future use); the endpoints below are the Direct REST paths.
"""

from typing import Any, AsyncGenerator, Dict, List, Optional

from src.config.providers import ProviderConfig
from .base import BaseProvider, _ensure_session, pad_embedding, is_rate_limit_error, parse_sse_stream


_GEMINI_GENERATE_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
)
_GEMINI_STREAM_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?key={key}&alt=sse"
)
_GEMINI_EMBED_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={key}"
)


class GeminiProvider(BaseProvider):
    """Google Gemini Direct — REST endpoints with auth in the query string."""

    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config)

    def _key(self) -> str:
        return self.config.get_api_key()

    def _generate_url(self, model: str) -> str:
        return _GEMINI_GENERATE_URL.format(model=model, key=self._key())

    def _stream_url(self, model: str) -> str:
        return _GEMINI_STREAM_URL.format(model=model, key=self._key())

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
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature},
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}
        try:
            res = self._post_json(
                self._generate_url(model),
                payload,
                headers={"Content-Type": "application/json"},
                timeout=timeout,
            )
            return res["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            if is_rate_limit_error(e):
                raise RuntimeError(f"Gemini rate limited: {e}") from e
            raise

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
            "contents": [{"role": "user", "parts": [{"text": user_message}]}],
            "generationConfig": {"temperature": temperature},
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}
        async with session.post(self._stream_url(model), json=payload) as resp:
            if resp.status == 429:
                err = await resp.text()
                raise RuntimeError(f"Gemini rate limited (429): {err}")

            def _extract(chunk: Dict[str, Any]) -> List[str]:
                tokens: List[str] = []
                for c in chunk.get("candidates", []):
                    for p in c.get("content", {}).get("parts", []):
                        if "text" in p and p["text"]:
                            tokens.append(p["text"])
                return tokens

            async for token in parse_sse_stream(resp.content, _extract):
                yield token

    # ── embedding ───────────────────────────────────────────────────────

    async def embed(self, text: str) -> List[float]:
        """Fallback embedding via text-embedding-004 (768-dim, padded to 2048 for LanceDB)."""
        session = _ensure_session()
        payload = {"contents": [{"parts": [{"text": text}]}]}
        async with session.post(
            _GEMINI_EMBED_URL.format(key=self._key()),
            json=payload,
            headers={"Content-Type": "application/json"},
        ) as resp:
            import json
            data = json.loads(await resp.text())
            return pad_embedding(data["embedding"]["values"])
