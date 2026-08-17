"""
Unit tests for Incremental Delta GraphRAG Indexer.
"""

import tempfile
from pathlib import Path
import unittest

from src.converters.delta_indexer import DeltaGraphIndexer, DeltaDiffReport


class TestDeltaIndexer(unittest.TestCase):
    """Test suite for delta hash tracking and incremental indexer."""

    def test_compute_diff_initial_run(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            source_file = tmp_path / "resume.txt"
            source_file.write_text("## Experience\nWorked on AWS.\n## Education\nBS CS.", encoding="utf-8")
            manifest_file = tmp_path / "manifest.json"

            indexer = DeltaGraphIndexer(manifest_path=manifest_file)
            diff = indexer.compute_diff(source_file)
            self.assertIsInstance(diff, DeltaDiffReport)
            self.assertTrue(diff.has_changes)
            self.assertGreater(len(diff.added_or_modified_chunks), 0)

    def test_compute_diff_no_changes_on_second_run(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            source_file = tmp_path / "resume.txt"
            source_file.write_text("## Experience\nWorked on AWS.", encoding="utf-8")
            manifest_file = tmp_path / "manifest.json"

            indexer = DeltaGraphIndexer(manifest_path=manifest_file)
            diff1 = indexer.compute_diff(source_file)
            indexer.save_manifest(source_file, diff1)

            # Second run with same file content
            diff2 = indexer.compute_diff(source_file)
            self.assertFalse(diff2.has_changes)
            self.assertEqual(len(diff2.added_or_modified_chunks), 0)

    def test_compute_diff_detects_chunk_modification(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            source_file = tmp_path / "resume.txt"
            source_file.write_text("## Experience\nWorked on AWS.\n## Education\nBS CS.", encoding="utf-8")
            manifest_file = tmp_path / "manifest.json"

            indexer = DeltaGraphIndexer(manifest_path=manifest_file)
            diff1 = indexer.compute_diff(source_file)
            indexer.save_manifest(source_file, diff1)

            # Modify Experience section only
            source_file.write_text("## Experience\nWorked on AWS ECS Fargate & Kafka.\n## Education\nBS CS.", encoding="utf-8")
            diff2 = indexer.compute_diff(source_file)
            self.assertTrue(diff2.has_changes)
            # Only Experience chunk should be in added_or_modified
            self.assertTrue(any("Experience" in chunk_name for chunk_name, _ in diff2.added_or_modified_chunks))


if __name__ == "__main__":
    unittest.main()
