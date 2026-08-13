"""
Unit tests for query search engine module.
"""

import threading
import time
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
from src.query.search_engine import TTLCache, execute_graphrag_query, query_cache
from src.query.static_graph_reader import search_static_resume

class TestSearchEngine(unittest.TestCase):

    def setUp(self):
        execute_graphrag_query.cache_clear()

    @patch("src.query.search_engine.call_serverless_llm")
    def test_execute_graphrag_query_success(self, mock_llm):
        mock_llm.return_value = "Query search result"

        result = execute_graphrag_query("test query", "local")
        self.assertEqual(result, "Query search result")
        mock_llm.assert_called_once()

    @patch("src.query.search_engine.call_serverless_llm")
    def test_execute_graphrag_query_dynamic_fallback(self, mock_llm):
        mock_llm.side_effect = Exception("LLM call failed")

        # Test local mode returns granular company details
        res_local = execute_graphrag_query("Which companies has Prasad worked for?", "local")
        self.assertIn("Local Context", res_local)
        self.assertIn("Rocket Mortgage", res_local)

        # Test global mode returns global executive summary
        res_global = execute_graphrag_query("Which companies has Prasad worked for?", "global")
        self.assertIn("Global Summary", res_global)
        self.assertIn("10+ Year Career Progression", res_global)

        # Verify local vs global responses are NOT identical
        self.assertNotEqual(res_local, res_global)

    def test_search_static_resume_modes(self):
        company_local = search_static_resume("Which companies has Prasad worked for?", mode="local")
        self.assertIn("[Local Context]", company_local)
        self.assertIn("Rocket Mortgage", company_local)

        company_global = search_static_resume("Which companies has Prasad worked for?", mode="global")
        self.assertIn("[Global Summary]", company_global)
        self.assertIn("Career Trajectory", company_global)
        self.assertNotEqual(company_local, company_global)


# ---------------------------------------------------------------------------
# 3.1 & 3.2 & 3.4 — TTLCache unit tests + cache integration metrics
# ---------------------------------------------------------------------------

class TestTTLCache(unittest.TestCase):
    """Test TTL cache: basic CRUD, TTL expiry, LRU eviction."""

    def setUp(self):
        # Fresh cache per test — avoids cross-test interference from sleep-based expiry
        self.cache = TTLCache(max_size=3, ttl=1)

    # -- put / get ---------------------------------------------------------

    def test_set_and_get(self):
        self.cache.set("k", "v")
        self.assertEqual(self.cache.get("k"), "v")

    def test_get_missing_key_returns_none(self):
        self.assertIsNone(self.cache.get("nonexistent"))

    # -- TTL expiry --------------------------------------------------------

    def test_expired_entry_returns_none(self):
        self.cache.set("expire_me", "data")
        # Wait longer than TTL (1s) — using sleep here is fine for a unit test
        time.sleep(1.1)
        self.assertIsNone(self.cache.get("expire_me"))

    def test_fresh_entry_still_returned_before_expiry(self):
        self.cache.set("fresh", "value")
        time.sleep(0.5)
        self.assertEqual(self.cache.get("fresh"), "value")

    # -- max_size eviction -------------------------------------------------

    def test_evicts_oldest_on_overflow(self):
        self.cache.set("a", "1")
        self.cache.set("b", "2")
        self.cache.set("c", "3")
        self.assertEqual(self.cache.size, 3)

        # Adding a 4th entry should evict oldest ('a')
        self.cache.set("d", "4")
        self.assertIsNone(self.cache.get("a"))
        self.assertEqual(self.cache.get("d"), "4")
        self.assertEqual(self.cache.size, 3)

    def test_eviction_increments_counter(self):
        self.cache.set("x", "1")
        self.cache.set("y", "2")
        self.cache.set("z", "3")
        self.cache.set("overflow", "4")
        self.assertEqual(self.cache.evictions, 1)

    # -- thread safety -----------------------------------------------------

    def test_concurrent_writes_do_not_crash(self):
        errors: list[Exception] = []

        def writer(n: int):
            try:
                for i in range(50):
                    self.cache.set(f"thread-{n}-key-{i}", f"value-{i}")
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=writer, args=(t,)) for t in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [])

    # -- cache_clear -------------------------------------------------------

    def test_cache_clear_resets_everything(self):
        self.cache.set("a", "1")
        self.cache.get("a")       # produces a hit
        self.cache.set("b", "2")   # no eviction yet
        self.cache.cache_clear()
        # All counters are now zero after clear
        self.assertEqual(self.cache.size, 0)
        self.assertEqual(self.cache.hits, 0)
        self.assertEqual(self.cache.misses, 0)
        self.assertEqual(self.cache.evictions, 0)
        # Verify stale entries are truly gone (subsequent gets count as misses)
        self.assertIsNone(self.cache.get("a"))
        self.assertIsNone(self.cache.get("b"))
        self.assertEqual(self.cache.misses, 2)  # the two above gets

    # -- metrics counters --------------------------------------------------

    def test_hit_miss_counters(self):
        c = TTLCache(max_size=10, ttl=60)
        c.get("miss")                 # miss
        self.assertEqual(c.misses, 1)
        c.set("hit_key", "val")
        c.get("hit_key")              # hit
        self.assertEqual(c.hits, 1)

    def test_expired_counts_as_miss(self):
        c = TTLCache(max_size=10, ttl=1)
        c.set("exp", "v")
        time.sleep(1.1)
        c.get("exp")                  # expired -> miss
        self.assertEqual(c.misses, 1)


class TestQueryCacheIntegration(unittest.TestCase):
    """Verify execute_graphrag_query transparently uses query_cache."""

    @patch("src.query.search_engine.call_serverless_llm")
    def test_first_call_caches_result(self, mock_llm):
        mock_llm.return_value = "cached response"
        query_cache.cache_clear()
        result1 = execute_graphrag_query("same query", "local")
        self.assertEqual(result1, "cached response")
        self.assertEqual(mock_llm.call_count, 1)

    @patch("src.query.search_engine.call_serverless_llm")
    def test_second_identical_call_hits_cache(self, mock_llm):
        mock_llm.return_value = "cached response"
        query_cache.cache_clear()
        _ = execute_graphrag_query("same query", "local")
        _ = execute_graphrag_query("same query", "local")  # cache hit
        self.assertEqual(mock_llm.call_count, 1)  # NOT called again
        self.assertGreater(query_cache.hits, 0)

    @patch("src.query.search_engine.call_serverless_llm")
    def test_different_mode_different_cache_key(self, mock_llm):
        mock_llm.return_value = "mode-specific"
        query_cache.cache_clear()
        _ = execute_graphrag_query("q", "local")
        _ = execute_graphrag_query("q", "global")
        self.assertEqual(mock_llm.call_count, 2)  # different keys

    @patch("src.query.search_engine.call_serverless_llm")
    def test_cache_clear_restores_full_llm_calls(self, mock_llm):
        mock_llm.return_value = "resp"
        query_cache.cache_clear()
        _ = execute_graphrag_query("q", "local")
        _ = execute_graphrag_query("q", "local")  # hit
        query_cache.cache_clear()
        _ = execute_graphrag_query("q", "local")  # miss after clear
        self.assertEqual(mock_llm.call_count, 2)


# ---------------------------------------------------------------------------
# Connection pooling verification
# ---------------------------------------------------------------------------

class TestConnectionPooling(unittest.TestCase):
    """Verify _ensure_session produces correct TCPConnector + ClientTimeout config.

    Because aiohttp.TCPConnector requires a running event loop to instantiate,
    we verify the *source code* contains the expected connector arguments rather
    than forcing an event loop just for smoke-testing the session object.
    """

    def test_connector_source_has_pooling_args(self):
        """Confirm _ensure_session source includes pooling configuration."""
        import inspect
        from src.gateway.base import _ensure_session
        source = inspect.getsource(_ensure_session)
        self.assertIn("limit=100", source)
        self.assertIn("limit_per_host=10", source)
        self.assertIn("ttl_dns_cache=300", source)
        self.assertIn("use_dns_cache=True", source)
        self.assertIn("force_close=False", source)

    def test_timeout_source_has_granular_settings(self):
        """Confirm _ensure_session source includes granular timeouts."""
        import inspect
        from src.gateway.base import _ensure_session
        source = inspect.getsource(_ensure_session)
        self.assertIn("total=300", source)
        self.assertIn("connect=10", source)
        self.assertIn("sock_read=60", source)


if __name__ == "__main__":
    unittest.main()
