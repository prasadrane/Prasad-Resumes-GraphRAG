"""
Unit tests for ATS keyword extraction and GraphRAG matching module.
"""

import unittest
from src.generators.ats_matcher import extract_ats_keywords, match_graphrag_stories

class TestATSMatcher(unittest.TestCase):

    def test_extract_ats_keywords(self):
        jd_text = """
        We are seeking a Senior Software Engineer with strong experience in Python, AWS, GraphRAG,
        and Microservices architecture. Experience with CI/CD, Kubernetes, and SQL is required.
        """
        keywords = extract_ats_keywords(jd_text)
        self.assertIn("Python", keywords)
        self.assertIn("AWS", keywords)
        self.assertIn("GraphRAG", keywords)
        self.assertIn("Kubernetes", keywords)

    def test_extract_ats_keywords_empty(self):
        self.assertEqual(extract_ats_keywords(""), [])

    def test_match_graphrag_stories(self):
        keywords = ["AWS", "Python", "GraphRAG"]
        # Mock/test matching logic return
        matches = match_graphrag_stories(keywords)
        self.assertIsInstance(matches, list)

if __name__ == "__main__":
    unittest.main()
