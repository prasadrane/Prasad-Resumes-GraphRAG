"""
Unit tests for the LLM service facade.
"""

import unittest
from unittest.mock import patch


class TestLLMService(unittest.TestCase):

    def test_call_llm_delegates_to_gateway(self):
        from src.llm.service import call_llm
        with patch("src.query.serverless_gateway.call_serverless_llm", return_value="ok") as mock_gateway:
            result = call_llm("hello prompt", system_prompt="hello system")
        self.assertEqual(result, "ok")
        mock_gateway.assert_called_once_with(
            prompt="hello prompt", system_prompt="hello system", temperature=0.3, timeout=30
        )

    def test_call_llm_safe_returns_empty_on_error(self):
        from src.llm.service import call_llm_safe
        with patch("src.query.serverless_gateway.call_serverless_llm", side_effect=RuntimeError("gateway down")):
            self.assertEqual(call_llm_safe("p", "s"), "")

    def test_call_llm_safe_passes_through_success(self):
        from src.llm.service import call_llm_safe
        with patch("src.query.serverless_gateway.call_serverless_llm", return_value="result text"):
            self.assertEqual(call_llm_safe("p", "s"), "result text")

    def test_resume_generator_safe_call_is_facade(self):
        from src.generators import resume_generator
        from src.llm.service import call_llm_safe
        self.assertIs(resume_generator._call_llm_safe, call_llm_safe)

    def test_ats_matcher_fallback_uses_facade(self):
        from src.generators import ats_matcher
        with patch("src.generators.ats_matcher.execute_graphrag_query", side_effect=RuntimeError("graphrag down")):
            with patch("src.query.serverless_gateway.call_serverless_llm", return_value="line one\nline two") as mock_gateway:
                result = ats_matcher.match_graphrag_stories(["Python"])
        self.assertEqual(result, ["line one", "line two"])
        self.assertTrue(mock_gateway.called)


if __name__ == "__main__":
    unittest.main()
