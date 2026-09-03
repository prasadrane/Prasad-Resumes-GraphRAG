"""LLM gateway package — public API for LLM chat and embedding calls.

Public symbols:
    call_serverless_llm        — sync chat completion
    call_serverless_llm_stream — async streaming chat
    get_embedding              — async embedding
    ALIBABA_RESUME_MODEL       — registry-resolved resume model id

Legacy constants (OPENROUTER_URL, GEMINI_URL_TEMPLATE, ALIBABA_ANTHROPIC_URL)
are intentionally NOT re-exported — grep confirms zero external importers.
"""

from src.config.providers import get_model_for
from .facade import (
    call_serverless_llm,
    call_serverless_llm_stream,
    get_embedding,
    reset_circuit_breakers,
)

# Resolve from the registry so the value follows PROVIDERS changes. Never
# hardcode model strings here — they go stale when PROVIDERS changes.
ALIBABA_RESUME_MODEL = get_model_for("resume")[1]

__all__ = [
    "call_serverless_llm",
    "call_serverless_llm_stream",
    "get_embedding",
    "reset_circuit_breakers",
    "ALIBABA_RESUME_MODEL",
]
