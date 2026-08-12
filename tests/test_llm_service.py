"""
Unit tests for the LLM service facade.
"""

import logging
import unittest
from unittest.mock import patch


class TestLLMService(unittest.TestCase):

    def test_call_llm_delegates_to_gateway(self):
        from src.llm.service import call_llm
        with patch("src.gateway.call_serverless_llm", return_value="ok") as mock_gateway:
            result = call_llm("hello prompt", system_prompt="hello system")
        self.assertEqual(result, "ok")
        kwargs = mock_gateway.call_args[1]
        self.assertEqual(kwargs["prompt"], "hello prompt")
        self.assertEqual(kwargs["system_prompt"], "hello system")
        self.assertEqual(kwargs["temperature"], 0.3)
        self.assertEqual(kwargs["timeout"], 30)
        # Default use_case="chat" should resolve a model from providers
        self.assertIn("model", kwargs)

    def test_call_llm_safe_returns_empty_on_error(self):
        from src.llm.service import call_llm_safe
        with patch("src.gateway.call_serverless_llm", side_effect=RuntimeError("gateway down")):
            self.assertEqual(call_llm_safe("p", "s"), "")

    def test_call_llm_safe_passes_through_success(self):
        from src.llm.service import call_llm_safe
        with patch("src.gateway.call_serverless_llm", return_value="result text"):
            self.assertEqual(call_llm_safe("p", "s"), "result text")

    def test_resume_generator_safe_call_is_facade(self):
        from src.generators import resume_generator
        from src.llm.service import call_llm_safe
        self.assertIs(resume_generator._call_llm_safe, call_llm_safe)

    def test_ats_matcher_fallback_uses_facade(self):
        from src.generators import ats_matcher
        with patch("src.generators.ats_matcher.execute_graphrag_query", side_effect=RuntimeError("graphrag down")):
            with patch("src.gateway.call_serverless_llm", return_value="line one\nline two") as mock_gateway:
                result = ats_matcher.match_graphrag_stories(["Python"])
        self.assertEqual(result, ["line one", "line two"])
        self.assertTrue(mock_gateway.called)

    # ── Consolidated API (Task 1.1) ──────────────────────────────────────

    def test_call_llm_log_level_info(self):
        """Verify that call_llm uses logger.info, not print()."""
        from src.llm.service import call_llm
        handler = logging.Handler()
        messages = []
        handler.emit = lambda record: messages.append(record.getMessage())
        logger = logging.getLogger("src.llm.service")
        logger.handlers = [handler]
        logger.setLevel(logging.INFO)
        try:
            with patch("src.gateway.call_serverless_llm", return_value="ok"):
                call_llm("hi")
            self.assertGreater(len(messages), 0)
            self.assertIn("completed", messages[0].lower())
        finally:
            logger.handlers.clear()

    def test_call_llm_safe_log_level_warning(self):
        """Verify that call_llm_safe uses logger.warning, not print()."""
        from src.llm.service import call_llm_safe
        handler = logging.Handler()
        messages = []
        handler.emit = lambda record: messages.append(record.getMessage())
        logger = logging.getLogger("src.llm.service")
        logger.handlers = [handler]
        logger.setLevel(logging.WARNING)
        try:
            with patch("src.gateway.call_serverless_llm", side_effect=RuntimeError("down")):
                call_llm_safe("p", "s")
            self.assertGreater(len(messages), 0)
            self.assertIn("failed", messages[0].lower())
        finally:
            logger.handlers.clear()

    def test_use_case_resume_resolves_correct_model(self):
        """call_llm(use_case='resume') should pass the resolved model."""
        from src.llm.service import call_llm_for_resume
        with patch("src.gateway.call_serverless_llm", return_value="ok") as mock:
            call_llm_for_resume("hi")
        self.assertIn("model", mock.call_args[1])

    def test_legacy_wrappers_unchanged_signature(self):
        """Legacy functions still exist and accept their old signatures."""
        from src.llm.service import call_llm_for_resume, call_llm_safe_for_resume
        self.assertTrue(callable(call_llm_for_resume))
        self.assertTrue(callable(call_llm_safe_for_resume))


if __name__ == "__main__":
    unittest.main()
