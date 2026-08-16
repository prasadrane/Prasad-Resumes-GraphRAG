"""
Unit tests for ATS keyword extraction and GraphRAG matching module.
"""

import unittest
from unittest.mock import patch

from src.generators.ats_matcher import (
    extract_ats_keywords,
    match_graphrag_stories,
    rank_experience_bullets,
)


class TestATSMatcher(unittest.TestCase):

    def test_extract_ats_keywords(self):
        jd_text = """
        We are seeking a Senior Software Engineer with strong experience in Python, AWS, GraphRAG,
        and Microservices architecture. Experience with CI/CD, Kubernetes, and SQL is required.
        """
        keywords = extract_ats_keywords(jd_text, expand_ontology=False)
        self.assertIn("Python", keywords)
        self.assertIn("AWS", keywords)
        self.assertIn("GraphRAG", keywords)
        self.assertIn("Kubernetes", keywords)

    def test_extract_ats_keywords_empty(self):
        self.assertEqual(extract_ats_keywords(""), [])

    def test_extract_ats_keywords_with_ontology_expansion(self):
        jd_text = "Looking for an expert in Deep Learning and Event-Driven Architecture."
        keywords = extract_ats_keywords(jd_text, expand_ontology=True)
        # Should contain base matches as well as expanded terms from ontology
        keywords_lower = [k.lower() for k in keywords]
        self.assertTrue(
            any(k in keywords_lower for k in ["pytorch", "tensorflow", "keras"]),
            f"Expected deep learning child skills in {keywords_lower}"
        )
        self.assertTrue(
            any(k in keywords_lower for k in ["kafka", "rabbitmq", "event-driven architecture"]),
            f"Expected event streaming child skills in {keywords_lower}"
        )

    def test_rank_experience_bullets(self):
        bullets = [
            "Assisted in maintaining internal wiki documentation for legacy scripts.",
            "Architected AWS ECS Fargate microservices pipeline achieving 70% latency reduction and $400K cost savings.",
            "Implemented RESTful endpoints in FastAPI with basic test coverage.",
        ]
        ranked = rank_experience_bullets(
            bullets,
            keywords=["AWS", "FastAPI", "Microservices"],
            start_year=2023,
            end_year=2026,
        )
        self.assertEqual(len(ranked), 3)
        # The architected + metric bullet should rank highest
        top_bullet, top_score = ranked[0]
        self.assertIn("Architected AWS ECS Fargate", top_bullet)
        self.assertGreater(top_score.final_score, ranked[2][1].final_score)

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
