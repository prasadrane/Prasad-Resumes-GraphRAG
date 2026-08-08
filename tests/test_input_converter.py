"""
Unit tests for input_converter module (batch document conversion and filename normalization).
"""

import tempfile
import unittest
from pathlib import Path
from src.converters.input_converter import make_out_name, convert_documents

class TestInputConverter(unittest.TestCase):

    def test_make_out_name(self):
        self.assertEqual(make_out_name("Resume (1)"), "Resume_1.txt")
        self.assertEqual(make_out_name("My File"), "My_File.txt")
        self.assertEqual(
            make_out_name("Prasad Rane (Resume 2024)"),
            "Prasad_Rane_Resume_2024.txt"
        )
        self.assertEqual(make_out_name("Simple_File"), "Simple_File.txt")

    def test_convert_documents_missing_source(self):
        non_existent = Path("non_existent_directory_12345")
        with tempfile.TemporaryDirectory() as target_dir:
            stats = convert_documents(non_existent, Path(target_dir))
            self.assertEqual(stats, {"ok": 0, "skip": 0, "error": 0})

    def test_convert_documents_markdown_file(self):
        with tempfile.TemporaryDirectory() as src_dir, tempfile.TemporaryDirectory() as target_dir:
            src_path = Path(src_dir)
            target_path = Path(target_dir)

            md_file = src_path / "test_doc.md"
            md_file.write_text("# Test Document\n\nSample content.", encoding="utf-8")

            stats = convert_documents(src_path, target_path)
            self.assertEqual(stats["ok"], 1)
            self.assertEqual(stats["skip"], 0)
            self.assertEqual(stats["error"], 0)

            out_file = target_path / "test_doc.txt"
            self.assertTrue(out_file.exists())
            self.assertEqual(out_file.read_text(encoding="utf-8"), "# Test Document\n\nSample content.")

            # Run again without force -> should skip
            stats_skip = convert_documents(src_path, target_path, force=False)
            self.assertEqual(stats_skip["skip"], 1)
            self.assertEqual(stats_skip["ok"], 0)

            # Run again with force -> should overwrite
            stats_force = convert_documents(src_path, target_path, force=True)
            self.assertEqual(stats_force["ok"], 1)

if __name__ == "__main__":
    unittest.main()
