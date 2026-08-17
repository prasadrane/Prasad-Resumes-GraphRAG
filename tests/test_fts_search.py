"""
Unit tests for SQLite FTS5 Full-Text Search Engine.
"""

import tempfile
from pathlib import Path
import unittest

from src.query.fts_search import FTS5SearchEngine, FTSResult


class TestFTS5SearchEngine(unittest.TestCase):
    """Test suite for embedded FTS5 full-text search."""

    def test_fts5_indexing_and_query(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "fts_test.db"
            engine = FTS5SearchEngine(db_path=db_path)

            docs = [
                {"title": "Rocket Mortgage", "content": "Modernized underwriter monolith to AWS ECS Fargate and Kafka."},
                {"title": "London Computer Systems", "content": "Optimized SQL Server billing database reducing latency."},
                {"title": "EXFO", "content": "Engineered C# offline synchronization for optical test devices."},
            ]
            engine.index_documents(docs)

            # Query 1: Exact keyword
            results = engine.search("Fargate")
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].title, "Rocket Mortgage")
            self.assertIn("Fargate", results[0].content)

            # Query 2: Multiple terms
            results_multi = engine.search("SQL Server billing")
            self.assertEqual(len(results_multi), 1)
            self.assertEqual(results_multi[0].title, "London Computer Systems")

            # Query 3: Non-existent term
            results_empty = engine.search("NonExistentTechXYZ")
            self.assertEqual(len(results_empty), 0)


if __name__ == "__main__":
    unittest.main()
