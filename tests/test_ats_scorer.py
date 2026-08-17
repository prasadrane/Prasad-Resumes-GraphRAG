"""
Unit tests for ats_scorer.py — Real-time ATS match scoring, section breakdown, and recommendations.
"""

import unittest
from src.generators.ats_scorer import calculate_ats_score, ATSScoreReport


class TestATSScorer(unittest.TestCase):

    def setUp(self):
        self.jd_text = """
        Senior Software Engineer - Cloud & Distributed Systems
        We are seeking a Senior Engineer skilled in Python, FastAPI, AWS ECS, Kafka, and DynamoDB.
        You will build scalable microservices, optimize SQL Server databases, and deploy with Terraform and Docker.
        Requirements:
        - 5+ years of experience with Python, C#, and .NET Core
        - Experience with AWS (ECS, Lambda, SQS, SNS, DynamoDB)
        - Experience with event streaming via Kafka
        - Strong background in CI/CD and Docker
        """

        self.resume_text = """
        # Prasad Rane
        **Contact:** Lake Bluff, IL | 513-967-9423 | test@example.com

        ## SUMMARY
        Senior Software Engineer with 10+ years of experience in Python, AWS ECS, and microservices.

        ## EXPERIENCE
        ### Software Engineer | Tech Corp | Remote | Jan 2023 - Present
        - Architected AWS ECS Fargate microservices using Python and FastAPI, cutting costs by 40%.
        - Engineered Kafka event streaming pipelines handling 10M daily transactions.
        - Deployed containerized applications with Docker and Terraform IaC.

        ## SKILLS
        - Backend & APIs: Python, FastAPI, C#, .NET Core
        - Cloud & DevOps: AWS ECS, Docker, Terraform, Kafka

        ## CERTIFICATIONS
        - AWS Certified Solutions Architect

        ## EDUCATION
        - B.S. in Computer Science
        """

    def test_calculate_ats_score_returns_valid_report(self):
        report = calculate_ats_score(self.resume_text, self.jd_text)
        self.assertIsInstance(report, ATSScoreReport)
        self.assertGreaterEqual(report.overall_score, 50)
        self.assertLessEqual(report.overall_score, 100)
        self.assertTrue(len(report.matched_keywords) > 0)
        self.assertIn("Python", [k.term for k in report.matched_keywords])
        self.assertIn("Kafka", [k.term for k in report.matched_keywords])

    def test_calculate_ats_score_identifies_missing_keywords(self):
        report = calculate_ats_score(self.resume_text, self.jd_text)
        missing_terms = [k.term for k in report.missing_keywords]
        # DynamoDB or SQL Server or SQS might be missing from the test resume text
        self.assertTrue(any(term in ["DynamoDB", "SQL Server", "SQS", "SNS", "Lambda"] for term in missing_terms))

    def test_calculate_ats_score_provides_actionable_suggestions(self):
        report = calculate_ats_score(self.resume_text, self.jd_text)
        self.assertTrue(len(report.suggestions) > 0)
        self.assertTrue(any("Add" in s or "Include" in s for s in report.suggestions))

    def test_empty_resume_or_jd_handled_gracefully(self):
        report_empty_jd = calculate_ats_score(self.resume_text, "")
        self.assertEqual(report_empty_jd.overall_score, 0)
        self.assertEqual(report_empty_jd.matched_keywords, [])

        report_empty_resume = calculate_ats_score("", self.jd_text)
        self.assertEqual(report_empty_resume.overall_score, 0)
        self.assertEqual(report_empty_resume.matched_keywords, [])


if __name__ == "__main__":
    unittest.main()
