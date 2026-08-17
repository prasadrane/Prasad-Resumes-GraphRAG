"""
sanitizer.py — Defensive input sanitization and prompt injection guardrails.

Protects LLM gateways and GraphRAG endpoints against prompt injection, jailbreak attempts,
system prompt leakage attacks, control character corruption, and payload overflow.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import re
from typing import List, Pattern

logger = logging.getLogger(__name__)

# Heuristic patterns associated with prompt injection and jailbreak payloads
_INJECTION_PATTERNS: List[Pattern[str]] = [
    re.compile(r"\b(ignore|disregard|forget)\b.*\b(previous|earlier|above)\b.*\b(instructions|commands|rules|prompts?)\b", re.IGNORECASE),
    re.compile(r"\b(you\s+are\s+now|act\s+as)\s+(DAN|unrestricted|jailbroken|unfiltered)\b", re.IGNORECASE),
    re.compile(r"\b(reveal|print|output|display|show|dump)\b.*\b(system\s*prompt|hidden\s*(rules|instructions)|api\s*keys?)\b", re.IGNORECASE),
    re.compile(r"```\s*(system|instruction|admin)\b", re.IGNORECASE),
    re.compile(r"<\s*\|\s*(im_start|im_end|system)\s*\|\s*>", re.IGNORECASE),
    re.compile(r"\[\s*SYSTEM\s*(PROMPT)?\s*OVERRIDE\s*\]", re.IGNORECASE),
]

# Control characters to strip (ASCII 0-8, 11-12, 14-31) preserving standard tabs (\t) and newlines (\n, \r)
_CONTROL_CHAR_REGEX = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


@dataclass(slots=True)
class SanitizedResult:
    """Result of input sanitization."""
    sanitized_text: str
    is_safe: bool = True
    is_truncated: bool = False
    flagged_patterns: List[str] = field(default_factory=list)


class InputSanitizer:
    """
    Defensive input sanitization filter.
    """

    def __init__(self, max_chars: int = 4000) -> None:
        self.max_chars = max_chars

    def sanitize(self, text: str) -> SanitizedResult:
        """
        Sanitizes text by stripping harmful control characters, enforcing maximum length,
        and scanning for adversarial prompt injection signatures.
        """
        if not text:
            return SanitizedResult(sanitized_text="", is_safe=True)

        # 1. Clean control characters
        cleaned = _CONTROL_CHAR_REGEX.sub("", text)
        cleaned = cleaned.strip()

        # 2. Length check & truncation
        is_truncated = False
        if len(cleaned) > self.max_chars:
            cleaned = cleaned[: self.max_chars]
            is_truncated = True

        # 3. Prompt injection detection
        flagged: List[str] = []
        for pattern in _INJECTION_PATTERNS:
            match = pattern.search(cleaned)
            if match:
                flagged.append(match.group(0))

        is_safe = len(flagged) == 0
        if not is_safe:
            logger.warning("[SECURITY] Potential prompt injection detected: %s", flagged)

        return SanitizedResult(
            sanitized_text=cleaned,
            is_safe=is_safe,
            is_truncated=is_truncated,
            flagged_patterns=flagged,
        )
