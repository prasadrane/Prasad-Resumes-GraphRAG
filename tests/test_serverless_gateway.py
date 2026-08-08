"""
Unit tests for serverless LLM gateway module.
"""

import unittest
from unittest.mock import patch, MagicMock
import os
import json
from src.query.serverless_gateway import call_serverless_llm

class TestServerlessGateway(unittest.TestCase):

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

if __name__ == "__main__":
    unittest.main()
