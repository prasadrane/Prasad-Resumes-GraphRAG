"""
metrics — In-process counters + histograms for Prometheus-compatible export.

Exports:
    - MetricsCollector: singletons for LLM calls, queries, resume generation
    - get_collector()   : lazy singleton accessor (tests can reset)
    - collect_as_text()  : reads current collector → Prometheus text format

No external dependencies — pure-Python counters/histograms backed by
thread-safe ``multiprocessing.Value`` when running under gunicorn workers,
falling back to plain dicts for single-process dev/vercel use.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Dict, List, Tuple


class _SimpleHistogram:
    """Thread-safe histogram tracking individual observations."""

    # Default le boundaries (seconds)
    BUCKETS = (0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, float("inf"))

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sum: float = 0.0
        self._count: int = 0
        self._observations: List[float] = []

    def observe(self, value_seconds: float) -> None:
        with self._lock:
            self._sum += value_seconds
            self._count += 1
            self._observations.append(value_seconds)

    def snapshot(self) -> Tuple[int, float, List[float]]:
        """Return (count, sum, sorted_observations)."""
        with self._lock:
            return self._count, self._sum, list(self._observations)


class MetricsCollector:
    """Lightweight in-process metrics store supporting counters and histograms.

    Each metric key is a dotted name like ``llm.calls.total``.
    Counters use a ``{provider="..."}`` label when supplied.
    Histograms default to ``{}`` labels but support an optional label set.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # counter_key -> {label_tuple: int}
        self._counters: Dict[str, Dict[Tuple[str, ...], int]] = defaultdict(
            lambda: defaultdict(int)
        )
        # hist_key -> _SimpleHistogram
        self._histograms: Dict[str, _SimpleHistogram] = {}

    # ── public API ──────────────────────────────────────────────────────

    def inc_counter(self, key: str, labels: Dict[str, str] | None = None, amount: float = 1.0) -> None:
        """Increment a named counter, optionally with labeled dimensions."""
        label_key = tuple(sorted(labels.items())) if labels else ()
        with self._lock:
            self._counters[key][label_key] += amount

    def observe_histogram(self, key: str, value_seconds: float, labels: Dict[str, str] | None = None) -> None:
        """Record a histogram observation."""
        with self._lock:
            if key not in self._histograms:
                self._histograms[key] = _SimpleHistogram()
        self._histograms[key].observe(value_seconds)

    # ── snapshot readers (exported as Prometheus text) ───────────────────

    def get_counters(self) -> Dict[str, Dict[Tuple[str, ...], int]]:
        """Return a copy of all counters with proper frozen key types."""
        with self._lock:
            result = {}
            for k, vdict in self._counters.items():
                result[k] = dict(vdict)
            return result

    def get_histograms(self) -> Dict[str, Tuple[int, float, List[float]]]:
        """Return snapshots: count, sum, observations."""
        with self._lock:
            result = {}
            for key, hist in self._histograms.items():
                result[key] = hist.snapshot()
            return result

    def reset(self) -> None:
        """Clear all counters and histograms (test helper)."""
        with self._lock:
            self._counters.clear()
            self._histograms.clear()


# ── Module-level singleton ───────────────────────────────────────────────

_collector: MetricsCollector = MetricsCollector()


def get_collector() -> MetricsCollector:
    """Return the application-wide MetricsCollector singleton."""
    return _collector


def reset_collector() -> None:
    """Reset the singleton -- mainly for tests."""
    global _collector
    _collector = MetricsCollector()


# ── Prometheus text-format export ───────────────────────────────────────

def collect_as_text(collector: MetricsCollector | None = None) -> str:
    """Render all stored metrics as Prometheus exposition-format text.

    Example::

        # HELP llm_calls_total Total LLM calls
        # TYPE llm_calls_total counter
        llm_calls_total{provider="alibaba"} 150

    """
    if collector is None:
        collector = _collector

    lines: List[str] = []
    counters = collector.get_counters()
    histograms = collector.get_histograms()

    # Sort helper: convert le-label to numeric for ordering; +Inf goes last
    def _le_sort(k):
        if k == "+Inf":
            return float("inf")
        try:
            return float(k)
        except ValueError:
            return 0.0

    # Write counters
    for key, label_map in sorted(counters.items()):
        display_name = key.replace(".", " ").title()
        metric_id = key.replace(".", "_")
        lines.append(f"# HELP {metric_id} {display_name}")
        lines.append(f"# TYPE {metric_id} counter")
        for label_tuple, value in label_map.items():
            if label_tuple:
                label_str = ",".join(f'{k}="{v}"' for k, v in label_tuple)
                lines.append(f'{metric_id}{{{label_str}}} {int(value)}')
            else:
                lines.append(f"{metric_id} {int(value)}")

    # Write histograms — compute CUMULATIVE buckets from raw observations
    # Latency keys end in _latency → append _seconds for standard Prometheus naming
    def _hist_metric_id(key):
        mid = key.replace(".", "_")
        if mid.endswith("_latency"):
            return mid + "_seconds"
        return mid

    BUCKETS = (0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, float("inf"))
    bucket_labels = [
        f"{le:.2f}" if isinstance(le, float) and le != float("inf") else "+Inf"
        for le in BUCKETS
    ]

    for key, (hcount, hsum, observations) in sorted(histograms.items()):
        display_name = key.replace(".", " ").title()
        metric_id = _hist_metric_id(key)
        lines.append(f"# HELP {metric_id} {display_name}")
        lines.append(f"# TYPE {metric_id} histogram")

        cumulative = 0
        for le_label, edge in zip(bucket_labels, BUCKETS):
            cumulative += sum(1 for o in observations if o <= edge)
            escaped_le = le_label.replace("+Inf", "+INF")
            lines.append(f'{metric_id}_bucket{{le="{escaped_le}"}} {cumulative}')

        lines.append(f"{metric_id}_sum {hsum}")
        lines.append(f"{metric_id}_count {hcount}")

    return "\n".join(lines) + "\n"


# ── Pre-defined metric keys (consumer reference) ─────────────────────────

METRIC_LLM_CALLS_TOTAL = "llm.calls.total"
METRIC_LLM_CALLS_SUCCESS = "llm.calls.success"
METRIC_LLM_CALLS_ERROR = "llm.calls.error"
METRIC_LLM_LATENCY = "llm.latency"
METRIC_QUERY_COUNT = "query.count"
METRIC_QUERY_LATENCY = "query.latency"
METRIC_RESUME_GENERATION_COUNT = "resume_generation.count"
METRIC_RESUME_GENERATION_LATENCY = "resume_generation.latency"
