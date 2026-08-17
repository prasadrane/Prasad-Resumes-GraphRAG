"""
pii_redactor.py — PII Redaction & Privacy Guardrail.

Masks personally identifiable information (emails, phone numbers) before sending prompts
to third-party LLM providers and enables local roundtrip restoration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import re
from typing import Dict, List

logger = logging.getLogger(__name__)

_EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE_PATTERN = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b")


@dataclass
class PIIRedactionResult:
    """Result of PII redaction containing masked text and restoration mapping."""
    redacted_text: str
    mapping: Dict[str, str] = field(default_factory=dict)
    found_types: List[str] = field(default_factory=list)


class PIIRedactor:
    """
    Masks and restores personal identifiable information.
    """

    def redact(self, text: str) -> PIIRedactionResult:
        """Replace emails and phone numbers with deterministic placeholders."""
        if not text:
            return PIIRedactionResult(redacted_text="")

        mapping: Dict[str, str] = {}
        found_types: List[str] = []
        redacted = text

        # 1. Redact emails
        email_matches = _EMAIL_PATTERN.findall(redacted)
        if email_matches:
            found_types.append("email")
            for i, email in enumerate(dict.fromkeys(email_matches), start=1):
                placeholder = f"[EMAIL_{i}]"
                mapping[placeholder] = email
                redacted = redacted.replace(email, placeholder)

        # 2. Redact phone numbers
        phone_matches = _PHONE_PATTERN.findall(redacted)
        if phone_matches:
            found_types.append("phone")
            for i, phone in enumerate(dict.fromkeys(phone_matches), start=1):
                placeholder = f"[PHONE_{i}]"
                mapping[placeholder] = phone
                redacted = redacted.replace(phone, placeholder)

        return PIIRedactionResult(
            redacted_text=redacted,
            mapping=mapping,
            found_types=list(dict.fromkeys(found_types)),
        )

    def restore(self, text: str, mapping: Dict[str, str]) -> str:
        """Restore original values using the placeholder mapping."""
        if not text or not mapping:
            return text

        restored = text
        for placeholder, original in mapping.items():
            restored = restored.replace(placeholder, original)
        return restored
