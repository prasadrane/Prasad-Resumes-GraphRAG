"""DEPRECATED: moved to ``src.gateway`` — re-exports keep old import paths working.

New code should import from ``src.gateway``. Delete this shim once all
references (including docs) point at ``src.gateway``.

Public surface re-exported:
    call_serverless_llm
    call_serverless_llm_stream
    get_embedding
    ALIBABA_RESUME_MODEL

Legacy constants (OPENROUTER_URL, GEMINI_URL_TEMPLATE, ALIBABA_ANTHROPIC_URL)
are intentionally dropped — no in-repo importers reference them.
"""

from src.gateway import (  # explicit list — no star import
    call_serverless_llm,
    call_serverless_llm_stream,
    get_embedding,
    ALIBABA_RESUME_MODEL,
)

__all__ = [
    "call_serverless_llm",
    "call_serverless_llm_stream",
    "get_embedding",
    "ALIBABA_RESUME_MODEL",
]
