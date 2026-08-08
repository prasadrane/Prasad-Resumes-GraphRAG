"""
Unit tests for CLI parser and subcommands.
"""

import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
from src.cli import build_parser, get_default_source_dir

class TestCLI(unittest.TestCase):

    def test_default_source_dir_env(self):
        with patch.dict("os.environ", {"SOURCE_RESUMES_DIR": "/custom/source/dir"}):
            source_dir = get_default_source_dir()
            self.assertEqual(source_dir, Path("/custom/source/dir"))

    def test_parser_convert(self):
        parser = build_parser()
        args = parser.parse_args(["convert", "--force"])
        self.assertEqual(args.command, "convert")
        self.assertTrue(args.force)

    def test_parser_query(self):
        parser = build_parser()
        args = parser.parse_args(["query", "--mode", "global", "Who is Prasad?"])
        self.assertEqual(args.command, "query")
        self.assertEqual(args.mode, "global")
        self.assertEqual(args.query_string, "Who is Prasad?")

    def test_parser_index(self):
        parser = build_parser()
        args = parser.parse_args(["index"])
        self.assertEqual(args.command, "index")

    def test_parser_proxy(self):
        parser = build_parser()
        args = parser.parse_args(["proxy", "--port", "8005"])
        self.assertEqual(args.command, "proxy")
        self.assertEqual(args.port, 8005)

    def test_parser_generate(self):
        parser = build_parser()
        args = parser.parse_args(["generate", "--company", "Google", "--jd-file", "jd.txt"])
        self.assertEqual(args.command, "generate")
        self.assertEqual(args.company, "Google")
        self.assertEqual(args.jd_file, "jd.txt")

if __name__ == "__main__":
    unittest.main()
