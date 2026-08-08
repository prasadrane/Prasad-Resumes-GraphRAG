"""
Unit tests for query search engine module.
"""

import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
from src.query.search_engine import execute_graphrag_query

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
    def test_execute_graphrag_query_fallback_on_exception(self, mock_llm):
        mock_llm.side_effect = Exception("LLM call failed")

        result = execute_graphrag_query("failing query", "local")
        self.assertIn("Prasad Rane's GraphRAG Summary for 'failing query'", result)

if __name__ == "__main__":
    unittest.main()
