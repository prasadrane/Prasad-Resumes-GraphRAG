"""
Unit tests for ATS Simulator and Match Scorer.
"""

import unittest
from src.generators.ats_simulator import ATSSimulator, ATSReport


class TestATSSimulator(unittest.TestCase):
    """Test suite for ATS parsing simulator and gap analysis."""

    def setUp(self):
        self.simulator = ATSSimulator()

    def test_ats_simulation_high_match(self):
        resume = """
        # Prasad Rane
        ## Summary
        Senior Software Engineer specializing in AWS ECS Fargate, Kafka, Python, and Microservices.
        ## Experience
        ### Rocket Mortgage
        Architected AWS ECS Fargate microservices and Kafka streaming pipelines.
        """
        jd = "Seeking Senior Software Engineer with AWS, Kafka, Python, and Microservices."

        report = self.simulator.simulate(resume, jd)
        self.assertIsInstance(report, ATSReport)
        self.assertGreaterEqual(report.overall_score, 80.0)
        self.assertGreaterEqual(report.keyword_coverage, 0.75)
        self.assertTrue(len(report.covered_keywords) > 0)
        self.assertTrue(report.is_compliant)

    def test_ats_simulation_missing_keywords(self):
        resume = "Software Engineer with experience in HTML and CSS."
        jd = "Looking for Kubernetes, Golang, Terraform, and GraphQL experts."

        report = self.simulator.simulate(resume, jd)
        self.assertLess(report.overall_score, 50.0)
        self.assertGreater(len(report.missing_keywords), 0)
        self.assertTrue(any("Kubernetes" in k or "Golang" in k for k in report.missing_keywords))

    def test_empty_inputs(self):
        report = self.simulator.simulate("", "")
        self.assertEqual(report.overall_score, 0.0)
        self.assertEqual(report.keyword_coverage, 0.0)


if __name__ == "__main__":
    unittest.main()
