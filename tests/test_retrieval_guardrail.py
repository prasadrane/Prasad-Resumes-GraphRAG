"""
Unit tests for Self-Healing Retrieval Guardrail Agent.
"""

import unittest
from unittest.mock import MagicMock

from src.query.retrieval_guardrail import (
    ContextQualityReport,
    HealingTraceStep,
    RetrievalGuardrail,
)


class TestRetrievalGuardrailModels(unittest.TestCase):
    """Test data models for context quality reports and healing traces."""

    def test_context_quality_report_instantiation(self):
        report = ContextQualityReport(
            is_sufficient=True,
            token_count=120,
            entity_coverage=0.85,
            relevance_score=0.9,
            detected_issues=[],
            suggested_action="proceed",
        )
        self.assertTrue(report.is_sufficient)
        self.assertEqual(report.token_count, 120)
        self.assertEqual(report.entity_coverage, 0.85)
        self.assertEqual(report.relevance_score, 0.9)
        self.assertEqual(report.detected_issues, [])
        self.assertEqual(report.suggested_action, "proceed")

    def test_context_quality_report_defaults(self):
        report = ContextQualityReport(
            is_sufficient=False,
            token_count=0,
            entity_coverage=0.0,
            relevance_score=0.0,
        )
        self.assertFalse(report.is_sufficient)
        self.assertEqual(report.detected_issues, [])
        self.assertEqual(report.suggested_action, "proceed")

    def test_healing_trace_step_fields(self):
        report = ContextQualityReport(
            is_sufficient=False,
            token_count=5,
            entity_coverage=0.0,
            relevance_score=0.1,
            detected_issues=["low_token_density", "zero_entity_overlap"],
            suggested_action="fallback_drift",
        )
        step = HealingTraceStep(
            attempt=1,
            mode="local",
            query="AWS services",
            quality_report=report,
            action_taken="fallback_to_drift",
        )
        self.assertEqual(step.attempt, 1)
        self.assertEqual(step.mode, "local")
        self.assertEqual(step.query, "AWS services")
        self.assertEqual(step.quality_report, report)
        self.assertEqual(step.action_taken, "fallback_to_drift")


class TestRetrievalGuardrailEvaluation(unittest.TestCase):
    """Test Context Evaluation logic of RetrievalGuardrail."""

    def setUp(self):
        self.guardrail = RetrievalGuardrail(min_tokens=30, min_entity_coverage=0.3)

    def test_evaluate_empty_context(self):
        for empty_val in ["", "   ", "\n\t  "]:
            report = self.guardrail.evaluate_context("What AWS services did Prasad use?", empty_val)
            self.assertFalse(report.is_sufficient)
            self.assertEqual(report.token_count, 0)
            self.assertEqual(report.entity_coverage, 0.0)
            self.assertEqual(report.relevance_score, 0.0)
            self.assertIn("empty_context", report.detected_issues)
            self.assertIn("fallback", report.suggested_action)

    def test_evaluate_low_token_density(self):
        # 5 tokens, less than min_tokens (30)
        short_context = "Prasad worked with AWS Lambda."
        report = self.guardrail.evaluate_context("Tell me about Prasad's AWS Lambda experience", short_context)
        self.assertFalse(report.is_sufficient)
        self.assertLess(report.token_count, 30)
        self.assertIn("low_token_density", report.detected_issues)

    def test_evaluate_zero_entity_overlap(self):
        # Long context (50+ words) but completely missing query entities
        irrelevant_context = (
            "Prasad led sales and marketing initiatives across retail banking departments. "
            "He coordinated customer acquisition funnels, designed graphic assets in Adobe Photoshop, "
            "and managed direct email outreach campaigns resulting in higher subscriber engagement. "
            "He worked closely with editorial teams to produce quarterly newsletters and flyers."
        )
        report = self.guardrail.evaluate_context(
            "What Kubernetes, Docker, and Terraform experience does Prasad have?",
            irrelevant_context,
            extracted_entities=["kubernetes", "docker", "terraform"],
        )
        self.assertFalse(report.is_sufficient)
        self.assertEqual(report.entity_coverage, 0.0)
        self.assertIn("zero_entity_overlap", report.detected_issues)

    def test_evaluate_with_extracted_entities_partial_coverage(self):
        context = (
            "Prasad developed cloud-native microservices on AWS using Docker containers and Python. "
            "He deployed services using automated CI/CD pipelines with GitHub Actions and monitored "
            "system performance with Datadog and CloudWatch dashboards across multi-region clusters."
        )
        entities = ["AWS", "Docker", "Kubernetes", "Terraform"]
        report = self.guardrail.evaluate_context(
            "What DevOps tools did Prasad use?",
            context,
            extracted_entities=entities,
        )
        # AWS and Docker appear (2/4 = 0.5 >= min_entity_coverage 0.3)
        self.assertGreaterEqual(report.entity_coverage, 0.5)
        self.assertNotIn("zero_entity_overlap", report.detected_issues)
        self.assertTrue(report.is_sufficient)
        self.assertEqual(report.suggested_action, "proceed")

    def test_evaluate_sufficient_context(self):
        rich_context = (
            "Prasad Rane served as a Lead Cloud Solutions Engineer at Rocket Mortgage from 2021 to 2024. "
            "In this role, he architected scalable microservices using Python, FastAPI, and AWS Lambda. "
            "He spearheaded the migration of legacy monolithic pipelines to event-driven architectures "
            "using Apache Kafka and AWS DynamoDB, reducing end-to-end processing latency by 45%. "
            "Additionally, he instituted automated testing with PyTest and container orchestration on Kubernetes."
        )
        report = self.guardrail.evaluate_context(
            "Tell me about Prasad's experience with AWS, Kafka, and Python at Rocket Mortgage",
            rich_context,
        )
        self.assertTrue(report.is_sufficient)
        self.assertEqual(report.suggested_action, "proceed")
        self.assertEqual(report.detected_issues, [])
        self.assertGreater(report.token_count, 30)
        self.assertGreater(report.relevance_score, 0.6)

    def test_configurable_thresholds(self):
        custom_guardrail = RetrievalGuardrail(min_tokens=10, min_entity_coverage=0.2)
        short_ok_context = "Prasad used Python and AWS Lambda to build serverless APIs."
        report = custom_guardrail.evaluate_context("Python AWS", short_ok_context)
        self.assertTrue(report.is_sufficient)
        self.assertEqual(report.suggested_action, "proceed")


class TestRetrievalGuardrailSelfHealing(unittest.TestCase):
    """Test Self-Healing retrieval and mode fallback behavior."""

    def setUp(self):
        self.guardrail = RetrievalGuardrail(min_tokens=30, min_entity_coverage=0.3)

    def test_heal_retrieval_sufficient_on_first_try(self):
        rich_context = (
            "Prasad Rane architected AWS serverless solutions using Python, DynamoDB, and Lambda. "
            "He built event-driven data streaming pipelines handling over 5 million daily events "
            "with zero downtime and high availability across multiple availability zones."
        )
        mock_retrieval = MagicMock(return_value=rich_context)

        result_context, trace = self.guardrail.heal_retrieval(
            query="AWS DynamoDB Lambda experience",
            current_mode="local",
            retrieval_fn=mock_retrieval,
        )

        self.assertEqual(result_context, rich_context)
        self.assertEqual(len(trace), 1)
        self.assertEqual(trace[0].mode, "local")
        self.assertTrue(trace[0].quality_report.is_sufficient)
        self.assertEqual(trace[0].action_taken, "proceed")
        mock_retrieval.assert_called_once_with("AWS DynamoDB Lambda experience", mode="local")

    def test_heal_retrieval_fallback_local_to_drift(self):
        empty_local = ""
        rich_drift = (
            "Prasad Rane has deep experience with Docker and Kubernetes container orchestration. "
            "He configured Helm charts, managed multi-node clusters, and automated continuous delivery "
            "using GitHub Actions and ArgoCD for microservices deployments."
        )

        def mock_retrieval(query, mode="local"):
            if mode == "local":
                return empty_local
            elif mode == "drift":
                return rich_drift
            return "unexpected"

        result_context, trace = self.guardrail.heal_retrieval(
            query="Kubernetes Docker container experience",
            current_mode="local",
            retrieval_fn=mock_retrieval,
            max_retries=2,
        )

        self.assertEqual(result_context, rich_drift)
        self.assertEqual(len(trace), 2)
        self.assertEqual(trace[0].mode, "local")
        self.assertFalse(trace[0].quality_report.is_sufficient)
        self.assertEqual(trace[1].mode, "drift")
        self.assertTrue(trace[1].quality_report.is_sufficient)
        self.assertEqual(trace[1].action_taken, "proceed")

    def test_heal_retrieval_fallback_drift_to_global(self):
        empty_local = "Short"
        empty_drift = "Still too short"
        rich_global = (
            "Across his 10+ year engineering career, Prasad Rane has operated as a Lead Cloud Architect "
            "and Full-Stack Engineer, driving cloud migrations, microservice transformations, and AI/ML "
            "innovations across enterprise financial and tech organizations."
        )

        def mock_retrieval(query, mode="local"):
            if mode == "local":
                return empty_local
            elif mode == "drift":
                return empty_drift
            elif mode == "global":
                return rich_global
            return ""

        result_context, trace = self.guardrail.heal_retrieval(
            query="Career overview and leadership",
            current_mode="local",
            retrieval_fn=mock_retrieval,
            max_retries=2,
        )

        self.assertEqual(result_context, rich_global)
        self.assertEqual(len(trace), 3)
        self.assertEqual(trace[0].mode, "local")
        self.assertEqual(trace[1].mode, "drift")
        self.assertEqual(trace[2].mode, "global")
        self.assertTrue(trace[2].quality_report.is_sufficient)

    def test_heal_retrieval_ontology_expansion_retry(self):
        sparse_context = "Prasad has used various tools."
        rich_expanded_context = (
            "Prasad Rane has extensive experience with Kubernetes (k8s), Docker containers, "
            "and Container Orchestration across AWS ECS and AWS Fargate clusters. "
            "He deployed production container workloads with zero downtime deployments for enterprise clients."
        )

        call_count = 0

        def mock_retrieval(query, mode="local"):
            nonlocal call_count
            call_count += 1
            if "container orchestration" in query.lower() or "kubernetes" in query.lower():
                return rich_expanded_context
            return sparse_context

        result_context, trace = self.guardrail.heal_retrieval(
            query="k8s",
            current_mode="local",
            retrieval_fn=mock_retrieval,
            max_retries=2,
        )

        self.assertEqual(result_context, rich_expanded_context)
        self.assertGreaterEqual(len(trace), 2)
        self.assertTrue(trace[-1].quality_report.is_sufficient)

    def test_heal_retrieval_exhausted_retries_returns_best_context(self):
        weak_context_1 = "Short string."
        weak_context_2 = "Slightly longer string but still below minimum threshold."

        responses = [weak_context_1, weak_context_2, ""]
        idx = 0

        def mock_retrieval(query, mode="local"):
            nonlocal idx
            resp = responses[idx] if idx < len(responses) else ""
            idx += 1
            return resp

        result_context, trace = self.guardrail.heal_retrieval(
            query="Unknown technology",
            current_mode="local",
            retrieval_fn=mock_retrieval,
            max_retries=2,
        )

        # Should return best context seen (weak_context_2)
        self.assertEqual(result_context, weak_context_2)
        self.assertEqual(len(trace), 3)
        self.assertFalse(trace[-1].quality_report.is_sufficient)


if __name__ == "__main__":
    unittest.main()
