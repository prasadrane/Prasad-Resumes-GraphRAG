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

        # Test company question returns Prasad's actual employers
        res_company = execute_graphrag_query("Which companies has Prasad worked for?", "local")
        self.assertIn("Rocket Mortgage", res_company)
        self.assertIn("London Computer Systems", res_company)
        self.assertNotIn("Tech Corp", res_company)

        # Test AWS question returns AWS technologies
        res_aws = execute_graphrag_query("What AWS technologies did Prasad use?", "local")
        self.assertIn("AWS", res_aws)
        self.assertIn("Fargate", res_aws)

    def test_search_static_resume(self):
        company_res = search_static_resume("Which companies has Prasad worked for?")
        self.assertIn("Rocket Mortgage", company_res)
        self.assertIn("EXFO", company_res)

        aws_res = search_static_resume("What AWS technologies did Prasad use?")
        self.assertIn("Amazon Bedrock", aws_res)
        self.assertIn("ECS Fargate", aws_res)

if __name__ == "__main__":
    unittest.main()
