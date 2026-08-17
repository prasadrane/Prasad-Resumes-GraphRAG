"""
Unit tests for LinkedIn Profile & Headline Optimizer.
"""

import unittest
from src.generators.linkedin_optimizer import LinkedInOptimizer, LinkedInProfileData


class TestLinkedInOptimizer(unittest.TestCase):
    """Test suite for LinkedIn headline and profile optimization."""

    def setUp(self):
        self.optimizer = LinkedInOptimizer()

    def test_optimize_profile_headline_length(self):
        data = self.optimizer.optimize(target_role="Staff Cloud Engineer")
        self.assertIsInstance(data, LinkedInProfileData)
        self.assertLessEqual(len(data.headline), 220)
        self.assertGreater(len(data.headline), 20)
        self.assertIn("Staff Cloud Engineer", data.headline)

    def test_about_section_structure(self):
        data = self.optimizer.optimize()
        self.assertTrue(len(data.about_section) > 100)
        self.assertTrue(len(data.core_skills) > 0)


if __name__ == "__main__":
    unittest.main()
