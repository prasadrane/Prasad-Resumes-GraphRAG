"""
Unit tests for Tailored Cover Letter Generator.
"""

import unittest
from src.generators.cover_letter_generator import CoverLetterGenerator, CoverLetterData


class TestCoverLetterGenerator(unittest.TestCase):
    """Test suite for companion cover letter synthesis."""

    def setUp(self):
        self.generator = CoverLetterGenerator()

    def test_generate_cover_letter_basic(self):
        company = "Stripe"
        jd = "Seeking a Staff Engineer with expertise in AWS, high-throughput Payment Gateways, and Kafka."
        data = self.generator.generate(company, jd, candidate_name="Prasad Rane")

        self.assertIsInstance(data, CoverLetterData)
        self.assertEqual(data.company_name, "Stripe")
        self.assertIn("Prasad Rane", data.candidate_name)
        self.assertGreaterEqual(len(data.paragraphs), 3)

        md = self.generator.render_markdown(data)
        self.assertIn("Dear Hiring Team at Stripe", md)
        self.assertIn("Prasad Rane", md)

    def test_empty_company_fallback(self):
        data = self.generator.generate("", "Looking for Python developer.")
        self.assertEqual(data.company_name, "Hiring Team")


if __name__ == "__main__":
    unittest.main()
