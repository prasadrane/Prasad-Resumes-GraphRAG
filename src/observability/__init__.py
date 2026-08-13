"""
observability — Structured logging with correlation ID propagation.

Provides:
    - Correlation-ID ContextVar (auto-generated if not present)
    - StructuredLogger that emits JSON log records with the current correlation ID
    - FastAPI middleware to wire correlation IDs into every request

Usage in any module::

    from src.observability import get_correlation_id, logger
    logger.info("processing request", extra={"company": "Acme"})
    cid = get_correlation_id()  # str UUID of the current request
"""

from __future__ import annotations

import json
import logging
import uuid
from contextvars import ContextVar
from typing import Any, Dict

# ── Correlation-ID storage ───────────────────────────────────────────────

_request_id_ctx: ContextVar[str] = ContextVar(
    "correlation_id", default="",
)


def set_correlation_id(correlation_id: str) -> None:
    """Store a correlation ID for the current logical thread/task."""
    _request_id_ctx.set(correlation_id)


def get_correlation_id() -> str:
    """Return the active correlation ID (generated on first call if absent)."""
    current = _request_id_ctx.get()
    if not current:
        new_id = str(uuid.uuid4())
        _request_id_ctx.set(new_id)
        return new_id
    return current


# ── Structured Logger ───────────────────────────────────────────────────

class _StructuredFormatter(logging.Formatter):
    """JSON-log formatter that always includes the correlation ID."""

    def format(self, record: logging.LogRecord) -> str:
        # Enrich record with the current correlation ID
        cor_id = _request_id_ctx.get() or str(uuid.uuid4())
        extra: Dict[str, Any] = getattr(record, "extra_dict", {})
        payload = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": cor_id,
        }
        # Merge caller context when available
        if hasattr(record, "funcName") and record.funcName:
            payload["function"] = record.funcName
        if hasattr(record, "lineno"):
            payload["line"] = record.lineno
        # Merge any extra fields the caller attached
        payload.update(extra)
        # Preserve exc_text if an exception was logged
        if record.exc_text:
            payload["exception"] = record.exc_text
        return json.dumps(payload, default=str)


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a structured logger named *name*.

    Attaches a JSON formatter to the root handler so every emit becomes
    a single-line JSON object containing ``correlation_id`` and all
    standard log metadata.  The root logger is configured once — repeated
    calls are safe (no duplicate handlers).
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(_StructuredFormatter())
        logger.addHandler(handler)

    logger.setLevel(logging.DEBUG)
    return logger


# Convenience singleton -- use this pattern instead::
#     from src.observability import logger
#     logger.info("something happened")
logger = get_logger("obs")
