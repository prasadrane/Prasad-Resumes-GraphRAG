"""
Unit tests for src/cli.py main() dispatch. All side effects are mocked;
no subprocess, proxy, LLM, or file outside a temp dir is touched.
"""

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import ANY, MagicMock, patch

from src.cli import main


class TestCLIMain(unittest.TestCase):

    def _run_main(self, argv):
        with patch.object(sys, "argv", ["cli.py"] + argv):
            main()

    def test_convert_command(self):
        with patch("src.cli.convert_documents", return_value={"converted": 2}) as mock_conv:
            captured = io.StringIO()
            with redirect_stdout(captured):
                self._run_main(["convert", "--source", "/tmp/src", "--force"])
        mock_conv.assert_called_once_with(Path("/tmp/src"), ANY, force=True)
        self.assertIn("[CLI] Conversion complete", captured.getvalue())

    def test_index_command_success(self):
        with patch("src.cli.check_proxy_health", return_value=True), \
             patch("src.cli.subprocess.run", return_value=MagicMock(returncode=0)) as mock_run:
            self._run_main(["index"])
        cmd = mock_run.call_args[0][0]
        self.assertIn("graphrag", cmd)
        self.assertIn("index", cmd)

    def test_index_command_failure_exits(self):
        with patch("src.cli.check_proxy_health", return_value=True), \
             patch("src.cli.subprocess.run", return_value=MagicMock(returncode=2)):
            with self.assertRaises(SystemExit) as ctx:
                self._run_main(["index"])
        self.assertEqual(ctx.exception.code, 2)

    def test_proxy_command(self):
        with patch("src.cli.start_proxy_server") as mock_start:
            self._run_main(["proxy", "--port", "8005"])
        mock_start.assert_called_once()
        self.assertEqual(mock_start.call_args[1]["port"], 8005)

    def test_generate_with_jd_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            jd_file = tmp_path / "jd.txt"
            jd_file.write_text("Need Python and AWS experience.", encoding="utf-8")
            raw_path = tmp_path / "raw_resume.txt"

            with patch("src.cli.generate_raw_resume", return_value=raw_path) as mock_gen, \
                 patch("src.cli.render_pdf_resume") as mock_render:
                self._run_main(["generate", "--company", "Google", "--jd-file", str(jd_file)])

            mock_gen.assert_called_once_with("Google", "Need Python and AWS experience.")
            mock_render.assert_called_once_with(raw_path, tmp_path / "Prasad_Rane_Resume.pdf")

    def test_generate_missing_jd_file_exits(self):
        with self.assertRaises(SystemExit) as ctx:
            self._run_main(["generate", "--company", "Google", "--jd-file", "/nonexistent/jd.txt"])
        self.assertEqual(ctx.exception.code, 1)

    def test_generate_empty_jd_exits(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            jd_file = Path(tmp_dir) / "jd.txt"
            jd_file.write_text("   \n", encoding="utf-8")
            with self.assertRaises(SystemExit) as ctx:
                self._run_main(["generate", "--company", "Google", "--jd-file", str(jd_file)])
        self.assertEqual(ctx.exception.code, 1)

    def test_query_command_success(self):
        with patch("src.cli.check_proxy_health", return_value=True), \
             patch("src.cli.execute_graphrag_query", return_value="ANSWER TEXT") as mock_query:
            captured = io.StringIO()
            with redirect_stdout(captured):
                self._run_main(["query", "--mode", "global", "Career trajectory?"])
        self.assertEqual(mock_query.call_args[0], ("Career trajectory?", "global"))
        self.assertIn("ANSWER TEXT", captured.getvalue())

    def test_query_command_failure_exits(self):
        with patch("src.cli.check_proxy_health", return_value=True), \
             patch("src.cli.execute_graphrag_query", side_effect=RuntimeError("boom")):
            with self.assertRaises(SystemExit) as ctx:
                self._run_main(["query", "anything"])
        self.assertEqual(ctx.exception.code, 1)

    def test_ui_command(self):
        with patch("src.cli.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            self._run_main(["ui"])
        mock_run.assert_called_once_with(["vercel", "dev"], cwd=ANY)

    def test_no_command_prints_help(self):
        captured = io.StringIO()
        with redirect_stdout(captured):
            self._run_main([])
        self.assertIn("usage:", captured.getvalue().lower())


if __name__ == "__main__":
    unittest.main()
