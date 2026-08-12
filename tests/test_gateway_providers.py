"""
Unit tests for individual provider response-parsing logic.

Each provider's sync ``chat()`` is exercised against a mocked urllib so that
we verify payload shape and response parsing without hitting the network.

Providers are constructed with inline :class:`ProviderConfig` fixtures so
these tests don't depend on env vars being set.
"""

import os
import unittest
import time
from unittest.mock import patch, MagicMock, call
import json
from src.config.providers import ProviderConfig
from src.gateway.alibaba import AlibabaProvider
from src.gateway.openrouter import OpenRouterProvider
from src.gateway.gemini import GeminiProvider
from src.gateway.base import pad_embedding, is_rate_limit_error
from src.gateway.circuit_breaker import CircuitBreaker, ProviderCircuitOpen, State
from src.gateway.facade import retry_with_backoff


def _mock_urlopen(payload_dict):
    """Build a context-manager mock that returns *payload_dict* as JSON bytes."""
    mock_ctx = MagicMock()
    mock_ctx.read.return_value = json.dumps(payload_dict).encode("utf-8")
    mock_ctx.__enter__.return_value = mock_ctx
    return mock_ctx


def _cfg(name):
    """Build a ProviderConfig that reads its API key from a test-only env var."""
    return {
        "alibaba": ProviderConfig(
            name="alibaba",
            base_url="https://token-plan.ap-southeast-1.maas.aliyuncs.com/v1",
            api_key_env="TEST_ALIBABA_KEY",
            models={"chat": "qwen3.6-flash"},
        ),
        "openrouter": ProviderConfig(
            name="openrouter",
            base_url="https://openrouter.ai/api/v1",
            api_key_env="TEST_OPENROUTER_KEY",
            models={"chat": "anthropic/claude-opus-4.5"},
        ),
        "gemini": ProviderConfig(
            name="gemini",
            base_url="https://generativelanguage.googleapis.com/v1beta/openai",
            api_key_env="TEST_GEMINI_KEY",
            models={"chat": "gemini-2.0-flash-exp"},
        ),
    }[name]


# Keys are injected via env so ProviderConfig.get_api_key() can read them.
_KEYS = {
    "TEST_ALIBABA_KEY": "fake-alibaba",
    "TEST_OPENROUTER_KEY": "fake-openrouter",
    "TEST_GEMINI_KEY": "fake-gemini",
}


class _KeysPatched:
    """Mixin that sets test API keys in os.environ around each test."""

    def setUp(self):
        self._patcher = patch.dict(os.environ, _KEYS)
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()


# ── Embedded Helpers (Task 1.2 + 1.3) ────────────────────────────────────────

class TestPadEmbedding(unittest.TestCase):

    def test_padding_zeros(self):
        result = pad_embedding([1.0, 2.0], target_dim=5)
        self.assertEqual(result, [1.0, 2.0, 0.0, 0.0, 0.0])

    def test_truncation(self):
        result = pad_embedding([1.0, 2.0, 3.0, 4.0, 5.0, 6.0], target_dim=3)
        self.assertEqual(result, [1.0, 2.0, 3.0])

    def test_exact_length_copy(self):
        emb = [1.0, 2.0, 3.0]
        result = pad_embedding(emb, target_dim=3)
        self.assertEqual(result, [1.0, 2.0, 3.0])
        self.assertIsNot(result, emb)  # Must be a copy, not alias

    def test_default_dimension(self):
        result = pad_embedding([])
        self.assertEqual(len(result), 2048)


class TestIsRateLimitError(unittest.TestCase):

    def test_rate_limit_tag(self):
        self.assertTrue(is_rate_limit_error("rate_limit_exceeded"))
        self.assertTrue(is_rate_limit_error("rate limited, try again"))

    def test_status_code_429(self):
        self.assertTrue(is_rate_limit_error("got 429 from server"))

    def test_resource_exhausted(self):
        self.assertTrue(is_rate_limit_error("RESOURCE_EXHAUSTED"))

    def test_quota(self):
        self.assertTrue(is_rate_limit_error("quota exceeded"))

    def test_explicit_status_code_attr(self):
        exc = RuntimeError("timeout")
        exc.status_code = 429
        self.assertTrue(is_rate_limit_error(exc))

    def test_non_rate_limit(self):
        self.assertFalse(is_rate_limit_error("connection refused"))
        self.assertFalse(is_rate_limit_error(ValueError("bad value")))

    def test_false_status_code(self):
        exc = RuntimeError("timeout")
        exc.status_code = 500
        self.assertFalse(is_rate_limit_error(exc))


# ── Circuit Breaker (Task 1.7) ───────────────────────────────────────────────

class TestCircuitBreaker(unittest.TestCase):

    def test_initial_state_closed(self):
        cb = CircuitBreaker("test-provider")
        self.assertEqual(cb.state, State.CLOSED)

    def test_opens_after_threshold_failures(self):
        cb = CircuitBreaker("test-provider", failure_threshold=3, recovery_timeout=30)
        for _ in range(3):
            with self.assertRaises(RuntimeError):
                cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        self.assertEqual(cb.state, State.OPEN)

    def test_raises_provider_circuit_open_when_open(self):
        cb = CircuitBreaker("test-provider", failure_threshold=1, recovery_timeout=30)
        with self.assertRaises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("first fail")))
        self.assertEqual(cb.state, State.OPEN)
        with self.assertRaises(ProviderCircuitOpen):
            cb.call(lambda: "should not reach here")

    def test_half_open_transitions_to_closed_on_success(self):
        # Use long timeout so OPEN persists; patch monotonic for half-open probe.
        cb = CircuitBreaker("test-provider", failure_threshold=1, recovery_timeout=3600)
        with self.assertRaises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        self.assertEqual(cb.state, State.OPEN)
        # Simulate time passing by setting last_failure_time far enough back
        cb._last_failure_time = time.monotonic() - 3601
        self.assertEqual(cb.state, State.HALF_OPEN)
        # Success in half-open → closed
        result = cb.call(lambda: "recovered")
        self.assertEqual(result, "recovered")
        self.assertEqual(cb.state, State.CLOSED)

    def test_half_open_failure_puts_back_to_open(self):
        cb = CircuitBreaker("test-provider", failure_threshold=1, recovery_timeout=3600)
        with self.assertRaises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        self.assertEqual(cb.state, State.OPEN)
        # Simulate time passing for half-open probe
        cb._last_failure_time = time.monotonic() - 3601
        self.assertEqual(cb.state, State.HALF_OPEN)
        with self.assertRaises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("second fail")))
        self.assertEqual(cb.state, State.OPEN)

    def test_reset_clears_state(self):
        cb = CircuitBreaker("test-provider", failure_threshold=1, recovery_timeout=30)
        with self.assertRaises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        self.assertEqual(cb.state, State.OPEN)
        cb.reset()
        self.assertEqual(cb.state, State.CLOSED)


class TestRetryWithBackoff(unittest.TestCase):

    @patch("time.sleep")
    def test_succeeds_first_try(self, mock_sleep):
        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def fn():
            return 42
        self.assertEqual(fn(), 42)
        mock_sleep.assert_not_called()

    @patch("time.sleep")
    def test_retries_on_transient_error(self, mock_sleep):
        count = [0]
        @retry_with_backoff(max_retries=2, base_delay=0.01)
        def fn():
            count[0] += 1
            if count[0] < 3:
                raise ConnectionError("network error")
            return "success"
        result = fn()
        self.assertEqual(result, "success")
        self.assertEqual(count[0], 3)
        self.assertEqual(mock_sleep.call_count, 2)

    def test_rate_limit_errors_pass_through_immediately(self):
        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def fn():
            raise RuntimeError("429 rate limited")
        with self.assertRaises(RuntimeError) as ctx:
            fn()
        self.assertIn("429", str(ctx.exception))

    def test_exhausts_retries_raises_runtimes(self):
        @retry_with_backoff(max_retries=2, base_delay=0.01)
        def fn():
            raise ValueError("persistent error")
        with self.assertRaises(RuntimeError) as ctx:
            fn()
        self.assertIn("persistent error", str(ctx.exception))
        self.assertIn("2 retries", str(ctx.exception))


# ── Original Provider Tests (unchanged) ─────────────────────────────────────

class TestAlibabaProvider(_KeysPatched, unittest.TestCase):

    @patch("urllib.request.urlopen")
    def test_parses_anthropic_response_skipping_thinking(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen({
            "content": [
                {"type": "thinking", "thinking": "secret reasoning"},
                {"type": "text", "text": "visible answer"},
            ]
        })
        provider = AlibabaProvider(_cfg("alibaba"))
        result = provider.chat("hi", None, "qwen3.6-flash")
        self.assertEqual(result, "visible answer")

        req = mock_urlopen.call_args.args[0]
        # urllib.Request.get_header() is case-insensitive; direct .headers dict
        # lookup depends on whether Python normalized the key on construction.
        self.assertEqual(req.get_header("X-api-key"), "fake-alibaba")
        self.assertEqual(req.get_header("Anthropic-version"), "2023-06-01")
        self.assertTrue(req.full_url.endswith("/apps/anthropic/v1/messages"))

    @patch("urllib.request.urlopen")
    def test_returns_empty_when_no_text_block(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen({"content": [{"type": "thinking"}]})
        provider = AlibabaProvider(_cfg("alibaba"))
        self.assertEqual(provider.chat("hi", None, "qwen3.6-flash"), "")


class TestOpenRouterProvider(_KeysPatched, unittest.TestCase):

    @patch("urllib.request.urlopen")
    def test_parses_openai_response(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen({
            "choices": [{"message": {"content": "hello from openrouter"}}]
        })
        provider = OpenRouterProvider(_cfg("openrouter"))
        result = provider.chat("hi", None, "anthropic/claude-opus-4.5")
        self.assertEqual(result, "hello from openrouter")

        req = mock_urlopen.call_args.args[0]
        self.assertEqual(req.get_header("Authorization"), "Bearer fake-openrouter")
        self.assertTrue(req.full_url.endswith("/chat/completions"))

    @patch("urllib.request.urlopen")
    def test_system_prompt_is_sent(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen({
            "choices": [{"message": {"content": "ok"}}]
        })
        provider = OpenRouterProvider(_cfg("openrouter"))
        provider.chat("user msg", system_prompt="you are helpful", model="m")
        payload = json.loads(mock_urlopen.call_args.args[0].data.decode())
        self.assertEqual(payload["messages"][0]["role"], "system")
        self.assertEqual(payload["messages"][0]["content"], "you are helpful")
        self.assertEqual(payload["messages"][1]["role"], "user")


class TestGeminiProvider(_KeysPatched, unittest.TestCase):

    @patch("urllib.request.urlopen")
    def test_parses_gemini_response(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen({
            "candidates": [{"content": {"parts": [{"text": "gemini answer"}]}}]
        })
        provider = GeminiProvider(_cfg("gemini"))
        result = provider.chat("hi", None, "gemini-2.0-flash-exp")
        self.assertEqual(result, "gemini answer")

        # Gemini auth is in the URL query string, not the headers.
        req = mock_urlopen.call_args.args[0]
        self.assertIn("key=fake-gemini", req.full_url)
        self.assertIsNone(req.get_header("Authorization"))
        self.assertIn(":generateContent", req.full_url)

    @patch("urllib.request.urlopen")
    def test_rate_limit_forwarded_as_runtime_error(self, mock_urlopen):
        mock_urlopen.side_effect = Exception("HTTP 429 RESOURCE_EXHAUSTED: quota exceeded")
        provider = GeminiProvider(_cfg("gemini"))
        with self.assertRaises(RuntimeError) as ctx:
            provider.chat("hi", None, "gemini-2.0-flash-exp")
        self.assertIn("rate limited", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()
