"""
Unit tests for TelemetryTracer and Observability Spans.
"""

import time
import unittest
from src.observability.telemetry import TelemetryTracer, SpanRecord


class TestTelemetryTracer(unittest.TestCase):
    """Test suite for TelemetryTracer and performance span tracking."""

    def setUp(self):
        self.tracer = TelemetryTracer()

    def test_span_records_latency_and_attributes(self):
        with self.tracer.start_span("retrieval.local", {"query": "AWS services"}) as span:
            time.sleep(0.01)
            span.set_attribute("entity_count", 5)

        records = self.tracer.get_spans("retrieval.local")
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertIsInstance(record, SpanRecord)
        self.assertEqual(record.name, "retrieval.local")
        self.assertGreaterEqual(record.duration_ms, 0.0)
        self.assertEqual(record.attributes.get("entity_count"), 5)
        self.assertEqual(record.status, "ok")

    def test_span_captures_exception(self):
        try:
            with self.tracer.start_span("gateway.call"):
                raise RuntimeError("upstream timeout")
        except RuntimeError:
            pass

        records = self.tracer.get_spans("gateway.call")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].status, "error")
        self.assertIn("upstream timeout", records[0].error_message)

    def test_latency_summary_statistics(self):
        for duration in [10.0, 20.0, 30.0, 40.0, 50.0]:
            with self.tracer.start_span("pdf.render"):
                time.sleep(duration / 1000.0)

        stats = self.tracer.get_summary("pdf.render")
        self.assertEqual(stats["count"], 5)
        self.assertGreaterEqual(stats["avg_ms"], 0.0)
        self.assertGreaterEqual(stats["p90_ms"], 0.0)


if __name__ == "__main__":
    unittest.main()
