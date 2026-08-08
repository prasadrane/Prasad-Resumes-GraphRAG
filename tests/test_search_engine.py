"""
Unit tests for query search engine module.
"""

import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
from src.query.search_engine import execute_graphrag_query
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

if __name__ == "__main__":
    unittest.main()
