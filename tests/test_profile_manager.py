"""
Unit tests for Candidate Profile & Story Bank Manager.
"""

import tempfile
from pathlib import Path
import unittest

from src.converters.profile_manager import ProfileManager, CandidateProfile


class TestProfileManager(unittest.TestCase):
    """Test suite for CandidateProfile and ProfileManager."""

    def test_default_profile_loads_master_resume(self):
        manager = ProfileManager()
        profile = manager.get_profile("default")
        self.assertIsInstance(profile, CandidateProfile)
        self.assertEqual(profile.candidate_id, "default")
        self.assertTrue(len(profile.master_resume_text) > 0)
        self.assertIn("Prasad", profile.name)

    def test_list_profiles_includes_default(self):
        manager = ProfileManager()
        profiles = manager.list_profiles()
        self.assertIsInstance(profiles, list)
        self.assertTrue(any(p["id"] == "default" for p in profiles))

    def test_custom_profile_directory(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            cand_dir = tmp_path / "alex_doe"
            cand_dir.mkdir(parents=True)
            (cand_dir / "profile.yaml").write_text(
                "name: Alex Doe\ntitle: Staff AI Engineer\nemail: alex@example.com\n",
                encoding="utf-8",
            )
            (cand_dir / "resume.txt").write_text(
                "# Alex Doe\n## Summary\nExperienced AI Engineer.",
                encoding="utf-8",
            )

            manager = ProfileManager(profiles_dir=tmp_path)
            profile = manager.get_profile("alex_doe")
            self.assertEqual(profile.name, "Alex Doe")
            self.assertEqual(profile.title, "Staff AI Engineer")
            self.assertIn("Experienced AI Engineer", profile.master_resume_text)


if __name__ == "__main__":
    unittest.main()
