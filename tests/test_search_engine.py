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

    @patch("subprocess.run")
    def test_execute_graphrag_query_success(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Query search result"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        result = execute_graphrag_query("test query", "local")
        self.assertEqual(result, "Query search result")
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_execute_graphrag_query_failure(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = ""
        mock_proc.stderr = "GraphRAG CLI error occurred"
        mock_run.return_value = mock_proc

        with self.assertRaises(RuntimeError) as ctx:
            execute_graphrag_query("failing query", "local")
        
        self.assertIn("GraphRAG CLI error occurred", str(ctx.exception))

if __name__ == "__main__":
    unittest.main()
