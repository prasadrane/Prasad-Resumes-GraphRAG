"""
Unit tests for LLM Judge Hallucination Auditor.
"""

import unittest
from src.observability.judge_evaluator import LLMJudgeEvaluator, JudgeScore


class TestLLMJudgeEvaluator(unittest.TestCase):
    """Test suite for factual faithfulness and hallucination auditing."""

    def setUp(self):
        self.judge = LLMJudgeEvaluator()

    def test_evaluate_grounded_bullet(self):
        context = (
            "Rocket Mortgage (2023-2025): Modernized legacy underwriter VB.NET monolith into AWS ECS Fargate microservices, "
            "reducing query latency by 70% and saving $400K annually."
        )
        bullet = "Architected AWS ECS Fargate microservices reducing query latency by 70%."

        score = self.judge.evaluate(bullet, context)
        self.assertIsInstance(score, JudgeScore)
        self.assertGreaterEqual(score.faithfulness, 0.80)
        self.assertFalse(score.hallucination_detected)
        self.assertEqual(len(score.unsupported_claims), 0)

    def test_evaluate_hallucinated_bullet(self):
        context = "Prasad developed .NET Core web APIs and SQL Server databases at London Computer Systems."
        hallucinated = "Founded quantum computing laboratory at MIT, securing $50M in venture capital funding."

        score = self.judge.evaluate(hallucinated, context)
        self.assertLess(score.faithfulness, 0.40)
        self.assertTrue(score.hallucination_detected)
        self.assertGreater(len(score.unsupported_claims), 0)

    def test_empty_inputs(self):
        score = self.judge.evaluate("", "")
        self.assertEqual(score.faithfulness, 1.0)
        self.assertFalse(score.hallucination_detected)


if __name__ == "__main__":
    unittest.main()
