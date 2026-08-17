"""
telemetry.py — Lightweight Distributed Tracing & Latency Telemetry for GraphRAG & Gateway.

Captures span latencies, percentile distributions (P50, P90, P99), error states, and operation metadata.
"""

from __future__ import annotations

import collections
from contextlib import contextmanager
from dataclasses import dataclass, field
import logging
import threading
import time
from typing import Any, Dict, Generator, List, Optional, Deque

logger = logging.getLogger(__name__)


@dataclass
class SpanRecord:
    """Record of a completed execution span."""
    name: str
    start_time: float
    duration_ms: float
    status: str = "ok"
    attributes: Dict[str, Any] = field(default_factory=dict)
    error_message: str = ""


class ActiveSpan:
    """Handle to a currently active span."""

    def __init__(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        self.name = name
        self.attributes = attributes.copy() if attributes else {}
        self.start_time = time.monotonic()
        self.status = "ok"
        self.error_message = ""

    def set_attribute(self, key: str, value: Any) -> None:
        """Add or update an attribute on the active span."""
        self.attributes[key] = value

    def set_error(self, exc: Exception) -> None:
        """Mark span as errored and capture error message."""
        self.status = "error"
        self.error_message = str(exc)


class TelemetryTracer:
    """
    Lightweight in-memory OpenTelemetry-compatible span tracer with O(1) ring-buffer deques.
    """

    def __init__(self, max_spans_per_name: int = 200) -> None:
        self.max_spans = max_spans_per_name
        self._spans: Dict[str, Deque[SpanRecord]] = {}
        self._lock = threading.Lock()

    @contextmanager
    def start_span(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Generator[ActiveSpan, None, None]:
        """Context manager to trace execution of a code block."""
        active = ActiveSpan(name, attributes)
        try:
            yield active
        except Exception as exc:
            active.set_error(exc)
            raise
        finally:
            duration_ms = (time.monotonic() - active.start_time) * 1000.0
            record = SpanRecord(
                name=name,
                start_time=active.start_time,
                duration_ms=duration_ms,
                status=active.status,
                attributes=active.attributes,
                error_message=active.error_message,
            )
            with self._lock:
                if name not in self._spans:
                    self._spans[name] = collections.deque(maxlen=self.max_spans)
                self._spans[name].append(record)

    def get_spans(self, name: str) -> List[SpanRecord]:
        """Return all recorded spans for a given name."""
        with self._lock:
            return list(self._spans.get(name, []))

    def get_summary(self, name: str) -> Dict[str, float]:
        """Calculate count, average, P50, P90, and P99 latency statistics in milliseconds."""
        spans = self.get_spans(name)
        if not spans:
            return {"count": 0, "avg_ms": 0.0, "p50_ms": 0.0, "p90_ms": 0.0, "p99_ms": 0.0}

        durations = sorted([s.duration_ms for s in spans])
        n = len(durations)

        avg_ms = sum(durations) / n
        p50_idx = int(0.50 * (n - 1))
        p90_idx = int(0.90 * (n - 1))
        p99_idx = int(0.99 * (n - 1))

        return {
            "count": n,
            "avg_ms": round(avg_ms, 2),
            "p50_ms": round(durations[p50_idx], 2),
            "p90_ms": round(durations[p90_idx], 2),
            "p99_ms": round(durations[p99_idx], 2),
        }

    def clear(self) -> None:
        """Clear all recorded spans."""
        with self._lock:
            self._spans.clear()


# Global singleton tracer
_global_tracer: Optional[TelemetryTracer] = None


def get_tracer() -> TelemetryTracer:
    """Return shared TelemetryTracer singleton."""
    global _global_tracer
    if _global_tracer is None:
        _global_tracer = TelemetryTracer()
    return _global_tracer
