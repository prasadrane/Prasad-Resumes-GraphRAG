# Subsystem: `src/observability` (Continent Level)

**Responsibility:** Structured JSON logging, metrics instrumentation, and synthetic benchmark evaluation.

---

## 1. Overview & Responsibility

**[Documented]** `src/observability` provides structured logging formats (`_StructuredFormatter`), execution tracing, latency measurements, and the automated synthetic benchmark evaluation harness (`BenchmarkEvaluator`).

**[Inferred]** This subsystem enables production monitoring and automated regression detection across context precision, context recall, and retrieval latency metrics.

---

## 2. Key Modules & Classes

| Module / Class | File | Responsibility |
|:---|:---|:---|
| `_StructuredFormatter` | `src/observability/__init__.py` | Formats log records into structured JSON objects with timestamps, log level, and component tags. |
| `get_logger` | `src/observability/__init__.py` | Configures and returns standard loggers with JSON or human-readable handlers. |
| [`MetricsCollector`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/metrics.py) | `src/metrics.py` | In-process thread-safe counters, latency histograms, and Prometheus-compatible endpoint formats. |
| `benchmark_eval` | `src/observability/benchmark_eval.py` | Runs synthetic evaluation queries against ground truth datasets to benchmark retrieval quality. |

---

## 3. Metrics Tracked

- `llm.calls.total`: Counter of LLM requests grouped by provider.
- `llm.calls.failed`: Counter of failed provider invocations.
- `retrieval.latency.ms`: Histogram of graph search and vector query duration.
- `guardrail.escalations`: Counter of self-healing retrieval escalations (e.g. `local` $\rightarrow$ `drift`).
