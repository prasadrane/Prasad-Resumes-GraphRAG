"""
Unit tests for ATS keyword extraction and GraphRAG matching module.
"""

import unittest
from unittest.mock import patch

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

    def test_match_splits_response_lines(self):
        with patch(
            "src.generators.ats_matcher.execute_graphrag_query",
            return_value="Line one\n\nLine two\n",
        ) as mock_query:
            matches = match_graphrag_stories(["AWS", "Python"])
        self.assertEqual(matches, ["Line one", "Line two"])
        mock_query.assert_called_once()

    def test_match_empty_response_returns_empty(self):
        with patch(
            "src.generators.ats_matcher.execute_graphrag_query", return_value=""
        ):
            self.assertEqual(match_graphrag_stories(["AWS"]), [])

    def test_match_falls_back_to_llm_on_query_error(self):
        with patch(
            "src.generators.ats_matcher.execute_graphrag_query",
            side_effect=RuntimeError("graph offline"),
        ), patch("src.llm.service.call_llm", return_value="Fallback line") as mock_llm:
            matches = match_graphrag_stories(["AWS"])
        self.assertEqual(matches, ["Fallback line"])
        mock_llm.assert_called_once()

    def test_match_empty_keywords_skips_query(self):
        with patch("src.generators.ats_matcher.execute_graphrag_query") as mock_query:
            self.assertEqual(match_graphrag_stories([]), [])
        mock_query.assert_not_called()


if __name__ == "__main__":
    unittest.main()
