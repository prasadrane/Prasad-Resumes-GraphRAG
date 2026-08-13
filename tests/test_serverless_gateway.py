"""
Unit tests for the gateway package (formerly serverless_gateway.py).

The old module is now a thin re-export shim. These tests exercise the
real ``src.gateway`` public API — sync chat with urllib mocking, failover
behavior, and the empty-keys guard. Provider-level parsing is covered
in ``tests/test_gateway_providers.py``.
"""

import unittest
from unittest.mock import patch, MagicMock
import os
import json
from src.gateway import call_serverless_llm


class TestGatewayFacade(unittest.TestCase):
    """Sync chat via urllib, failover, and error surface."""

    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "test_openrouter_key"})
    @patch("urllib.request.urlopen")
    def test_call_serverless_llm_openrouter_success(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "choices": [{"message": {"content": "Serverless OpenRouter response"}}]
        }).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        res = call_serverless_llm("Test prompt", system_prompt="Test sys")
        self.assertEqual(res, "Serverless OpenRouter response")

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_gemini_key"}, clear=True)
    @patch("urllib.request.urlopen")
    def test_call_serverless_llm_gemini_success(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "candidates": [{"content": {"parts": [{"text": "Serverless Gemini response"}]}}]
        }).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        res = call_serverless_llm("Test prompt")
        self.assertEqual(res, "Serverless Gemini response")

    @patch.dict(os.environ, {}, clear=True)
    def test_call_serverless_llm_no_keys(self):
        with self.assertRaises(ValueError) as ctx:
            call_serverless_llm("Test prompt")
        self.assertIn("Neither OPENROUTER_API_KEY nor GEMINI_API_KEY", str(ctx.exception))

    @patch.dict(os.environ, {"ALIBABA_API_KEY": "test_alibaba_key"})
    @patch("urllib.request.urlopen")
    def test_call_serverless_llm_alibaba_skips_thinking_blocks(self, mock_urlopen):
        """Alibaba content blocks of type 'thinking' are skipped; first 'text' block wins."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "content": [
                {"type": "thinking", "thinking": "internal reasoning"},
                {"type": "text", "text": "hello user"},
            ]
        }).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        res = call_serverless_llm("Test prompt")
        self.assertEqual(res, "hello user")


if __name__ == "__main__":
    unittest.main()
