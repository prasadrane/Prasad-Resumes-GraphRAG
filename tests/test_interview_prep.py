"""
Unit tests for Candidate Interview Prep Question Generator.
"""

import unittest
from src.query.interview_prep import InterviewPrepGenerator, InterviewPrepResult


class TestInterviewPrepGenerator(unittest.TestCase):
    """Test suite for interview question prediction and candidate talking points."""

    def setUp(self):
        self.generator = InterviewPrepGenerator()

    def test_generate_prep_from_jd(self):
        jd = """
        We are looking for a Senior Backend Engineer to design scalable microservices on AWS ECS Fargate,
        manage Kafka event streams, and lead high-availability database optimizations.
        """
        result = self.generator.generate(jd)
        self.assertIsInstance(result, InterviewPrepResult)
        self.assertGreaterEqual(len(result.questions), 3)
        self.assertTrue(len(result.talking_points) > 0)
        self.assertTrue(any("AWS" in q or "Kafka" in q or "Microservices" in q for q in result.questions))

    def test_generate_prep_empty_jd(self):
        result = self.generator.generate("")
        self.assertGreaterEqual(len(result.questions), 1)


if __name__ == "__main__":
    unittest.main()
