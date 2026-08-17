"""
llm_constants.py — Shared configuration constants for LLM and embedding gateways.

Centralized to adhere to Dependency Inversion Principle (DIP):
infrastructure gateways and application generators both reference this config
without circular or improper cross-layer dependencies.
"""

from typing import Tuple

EMBEDDING_DIM: int = 2048          # Target embedding dimension (LanceDB index)
DEFAULT_EMBEDDING_DIM: int = 2048  # Alias for backward compatibility
LLM_MAX_TOKENS: int = 4096         # Default max tokens per LLM response
LLM_DEFAULT_TIMEOUT: int = 300     # Default LLM request timeout (seconds)
GRAPHRAG_STORY_CAP: int = 20       # Maximum story lines injected into prompts

# Unified rate-limit detection tags
RATE_LIMIT_TAGS: Tuple[str, ...] = (
    "rate_limit",
    "rate limited",
    "429",
    "resource_exhausted",
    "quota",
)
