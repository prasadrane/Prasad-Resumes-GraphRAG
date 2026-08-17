"""
Unit tests for STAR Behavioral Interview Response Generator.
"""

import unittest
from unittest.mock import patch

from src.query.star_generator import STARGenerator, STARResponse


class TestSTARGenerator(unittest.TestCase):
    """Test suite for STAR format behavioral interview answer generation."""

    def setUp(self):
        self.generator = STARGenerator()

    def test_star_response_model(self):
        resp = STARResponse(
            situation="Legacy monolith caused high latency and deployment bottlenecks.",
            task="Modernize services to cloud-native microservices on AWS.",
            action="Architected ECS Fargate services, integrated Bedrock AI, and implemented Kafka governance.",
            result="Reduced latency by 70% and cut infrastructure costs by 40%.",
            metrics=["70% latency reduction", "40% cost reduction"],
            technologies=["AWS ECS Fargate", "Kafka", "Amazon Bedrock"],
        )
        self.assertIn("Legacy monolith", resp.situation)
        self.assertIn("70%", resp.result)
        self.assertEqual(len(resp.metrics), 2)
        self.assertEqual(len(resp.technologies), 3)
        self.assertIn("### **Situation**", resp.to_markdown())

    def test_generate_star_response_with_mock_context(self):
        context = (
            "Rocket Mortgage: Modernized underwriter VB.NET monolith to AWS ECS Fargate, "
            "reducing latency by 70% and saving $400K annually. Built Bedrock AI chatbot."
        )
        question = "Tell me about a time you led a major cloud migration or architectural change."
        
        resp = self.generator.generate_star_response(question, context=context)
        self.assertIsInstance(resp, STARResponse)
        self.assertTrue(len(resp.situation) > 0)
        self.assertTrue(len(resp.task) > 0)
        self.assertTrue(len(resp.action) > 0)
        self.assertTrue(len(resp.result) > 0)
        self.assertTrue(any("70%" in m or "$400k" in m.lower() for m in resp.metrics))

    def test_dimension_classification(self):
        self.assertEqual(self.generator.classify_dimension("How did you handle a production incident?"), "incident_response")
        self.assertEqual(self.generator.classify_dimension("Tell me about resolving a team conflict"), "leadership_conflict")
        self.assertEqual(self.generator.classify_dimension("How did you optimize cloud infrastructure costs?"), "cost_optimization")
        self.assertEqual(self.generator.classify_dimension("Tell me about scaling microservices"), "architecture_scaling")


if __name__ == "__main__":
    unittest.main()
