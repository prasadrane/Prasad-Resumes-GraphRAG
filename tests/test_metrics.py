"""
test_metrics — Verify MetricsCollector and /api/metrics endpoint via unittest.

Tests:
  - Counter increments and resets
  - Histogram observes, snapshots, and bucket counts
  - collect_as_text() returns valid Prometheus format
  - Pre-defined metric key constants are set correctly
"""

import unittest

from src.metrics import (
    MetricsCollector,
    collect_as_text,
    get_collector,
    reset_collector,
    METRIC_LLM_CALLS_TOTAL,
    METRIC_LLM_CALLS_SUCCESS,
    METRIC_LLM_CALLS_ERROR,
    METRIC_LLM_LATENCY,
    METRIC_QUERY_COUNT,
    METRIC_QUERY_LATENCY,
    METRIC_RESUME_GENERATION_COUNT,
    METRIC_RESUME_GENERATION_LATENCY,
)


class TestCounters(unittest.TestCase):
    def setUp(self):
        reset_collector()

    def tearDown(self):
        reset_collector()

    def test_inc_counter_default(self):
        c = MetricsCollector()
        c.inc_counter("foo")
        self.assertEqual(c.get_counters()["foo"][()], 1)

    def test_inc_counter_increment(self):
        c = MetricsCollector()
        c.inc_counter("bar", amount=3)
        self.assertEqual(c.get_counters()["bar"][()], 3)

    def test_inc_counter_with_labels(self):
        c = MetricsCollector()
        c.inc_counter("llm.calls.total", labels={"provider": "alibaba"})
        c.inc_counter("llm.calls.total", labels={"provider": "gemini"})
        counters = c.get_counters()["llm.calls.total"]
        # Labels stored as tuples of sorted (key, value) pairs
        alibaba_key = tuple(sorted({"provider": "alibaba"}.items()))
        gemini_key = tuple(sorted({"provider": "gemini"}.items()))
        self.assertEqual(counters[alibaba_key], 1)
        self.assertEqual(counters[gemini_key], 1)

    def test_reset_clears_counters(self):
        c = MetricsCollector()
        c.inc_counter("x")
        c.reset()
        self.assertNotIn("x", c.get_counters())


class TestHistograms(unittest.TestCase):
    def setUp(self):
        reset_collector()

    def tearDown(self):
        reset_collector()

    def test_observe_and_snapshot(self):
        c = MetricsCollector()
        c.observe_histogram("h", 0.25)
        c.observe_histogram("h", 0.75)
        count, total_sum, observations = c.get_histograms()["h"]
        self.assertEqual(count, 2)
        self.assertAlmostEqual(total_sum, 1.0, places=2)
        self.assertEqual(observations, [0.25, 0.75])

    def test_bucket_observations_stored(self):
        """Raw observations are stored and returned correctly."""
        c = MetricsCollector()
        c.observe_histogram("h", 0.1)
        c.observe_histogram("h", 0.5)
        c.observe_histogram("h", 5.0)
        _, _, obs = c.get_histograms()["h"]
        self.assertEqual(obs, [0.1, 0.5, 5.0])

    def test_reset_clears_histograms(self):
        c = MetricsCollector()
        c.observe_histogram("h", 1.0)
        c.reset()
        self.assertNotIn("h", c.get_histograms())


class TestCollectAsText(unittest.TestCase):
    def setUp(self):
        reset_collector()

    def tearDown(self):
        reset_collector()

    def test_empty_collection(self):
        text = collect_as_text(MetricsCollector())
        # No metrics → just trailing newline from join
        self.assertTrue(text in ("", "\n"))

    def test_counter_in_text(self):
        c = MetricsCollector()
        c.inc_counter("llm.calls.total", labels={"provider": "alibaba"}, amount=150)
        text = collect_as_text(c)
        self.assertIn("# HELP llm_calls_total", text)
        self.assertIn("# TYPE llm_calls_total counter", text)
        self.assertIn('llm_calls_total{provider="alibaba"} 150', text)

    def test_multiple_count_different_labels(self):
        c = MetricsCollector()
        c.inc_counter("llm.calls.total", labels={"provider": "alibaba"}, amount=100)
        c.inc_counter("llm.calls.total", labels={"provider": "openrouter"}, amount=50)
        text = collect_as_text(c)
        self.assertIn('provider="alibaba"', text)
        self.assertIn('provider="openrouter"', text)

    def test_histogram_in_text(self):
        c = MetricsCollector()
        c.observe_histogram("llm.latency", 0.45)
        c.observe_histogram("llm.latency", 1.20)
        text = collect_as_text(c)
        self.assertIn("llm_latency_seconds_count 2", text)
        # Sum = 0.45 + 1.20 = 1.65
        self.assertIn("llm_latency_seconds_sum 1.65", text)

    def test_histogram_bucket_format(self):
        """Bucket lines use _seconds suffix for latency metrics."""
        c = MetricsCollector()
        c.observe_histogram("q.latency", 0.20)
        text = collect_as_text(c)
        self.assertIn('q_latency_seconds_bucket', text)
        self.assertIn('le="+INF"', text)
        # Single observation at 0.20 should appear in buckets >= 0.20
        self.assertIn('q_latency_seconds_bucket{le="0.25"} 1', text)


class TestMetricConstants(unittest.TestCase):
    def test_llm_totals_defined(self):
        self.assertEqual(METRIC_LLM_CALLS_TOTAL, "llm.calls.total")
        self.assertEqual(METRIC_LLM_CALLS_SUCCESS, "llm.calls.success")
        self.assertEqual(METRIC_LLM_CALLS_ERROR, "llm.calls.error")

    def test_query_defined(self):
        self.assertEqual(METRIC_QUERY_COUNT, "query.count")
        self.assertEqual(METRIC_QUERY_LATENCY, "query.latency")

    def test_resume_defined(self):
        self.assertEqual(METRIC_RESUME_GENERATION_COUNT, "resume_generation.count")
        self.assertEqual(METRIC_RESUME_GENERATION_LATENCY, "resume_generation.latency")


if __name__ == "__main__":
    unittest.main()
