"""
Unit tests for centralized path configuration.
"""

import unittest

from src.config import ROOT_DIR, INPUT_DIR, OUTPUT_DIR, OUTPUT_DIR_PATH, MASTER_RESUME_PATH, WEB_STATIC_DIR


class TestConfig(unittest.TestCase):

    def test_root_dir_is_repo_root(self):
        self.assertTrue((ROOT_DIR / "settings.yaml").exists())
        self.assertTrue((ROOT_DIR / "src").is_dir())

    def test_derived_paths(self):
        self.assertEqual(INPUT_DIR, ROOT_DIR / "input")
        self.assertEqual(OUTPUT_DIR, "output")
        self.assertEqual(OUTPUT_DIR_PATH, ROOT_DIR / "output")
        self.assertEqual(MASTER_RESUME_PATH, ROOT_DIR / "input" / "MASTER_RESUME.txt")
        self.assertEqual(WEB_STATIC_DIR, ROOT_DIR / "src" / "web" / "static")

    def test_web_app_root_dir_matches_config(self):
        from src.web.app import ROOT_DIR as APP_ROOT_DIR
        self.assertEqual(APP_ROOT_DIR, ROOT_DIR)


if __name__ == "__main__":
    unittest.main()
