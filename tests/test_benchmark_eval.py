"""
Unit tests for Automated Synthetic Evaluation Harness & Benchmarking.
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock

from src.observability.benchmark_eval import (
    AggregateBenchmarkReport,
    BenchmarkCase,
    BenchmarkEvaluator,
    EvaluationResult,
    DEFAULT_BENCHMARK_DATASET,
)


class TestBenchmarkModels(unittest.TestCase):
    """Test data models for benchmark evaluation."""

    def test_benchmark_case_creation(self):
        case = BenchmarkCase(
            query="What AWS services did Prasad use at Rocket Mortgage?",
            query_type="skill_lookup",
            expected_entities=["AWS", "ECS Fargate", "Lambda", "DynamoDB", "Bedrock"],
            ground_truth_facts=[
                "Modernized VB.NET to AWS ECS Fargate",
                "Built Amazon Bedrock Claude Sonnet AI chatbot",
            ],
        )
        self.assertEqual(case.query, "What AWS services did Prasad use at Rocket Mortgage?")
        self.assertEqual(case.query_type, "skill_lookup")
        self.assertEqual(len(case.expected_entities), 5)
        self.assertEqual(len(case.ground_truth_facts), 2)

    def test_benchmark_case_defaults(self):
        case = BenchmarkCase(query="Tell me about Prasad")
        self.assertEqual(case.query, "Tell me about Prasad")
        self.assertEqual(case.query_type, "experience_lookup")
        self.assertEqual(case.expected_entities, [])
        self.assertEqual(case.ground_truth_facts, [])

    def test_evaluation_result_creation(self):
        res = EvaluationResult(
            case_query="What AWS services did Prasad use?",
            context_precision=0.85,
            context_recall=0.90,
            faithfulness=0.95,
            latency_ms=120.5,
            token_count=250,
            retrieval_mode="local",
            healed=False,
        )
        self.assertEqual(res.case_query, "What AWS services did Prasad use?")
        self.assertAlmostEqual(res.context_precision, 0.85)
        self.assertAlmostEqual(res.context_recall, 0.90)
        self.assertAlmostEqual(res.faithfulness, 0.95)
        self.assertAlmostEqual(res.latency_ms, 120.5)
        self.assertEqual(res.token_count, 250)
        self.assertEqual(res.retrieval_mode, "local")
        self.assertFalse(res.healed)

    def test_aggregate_benchmark_report(self):
        r1 = EvaluationResult(
            case_query="Q1",
            context_precision=0.8,
            context_recall=1.0,
            faithfulness=0.9,
            latency_ms=100.0,
            token_count=200,
            retrieval_mode="local",
            healed=False,
        )
        r2 = EvaluationResult(
            case_query="Q2",
            context_precision=1.0,
            context_recall=0.8,
            faithfulness=1.0,
            latency_ms=200.0,
            token_count=300,
            retrieval_mode="drift",
            healed=True,
        )

        report = AggregateBenchmarkReport(results=[r1, r2])
        self.assertEqual(report.total_cases, 2)
        self.assertAlmostEqual(report.avg_context_precision, 0.9)
        self.assertAlmostEqual(report.avg_context_recall, 0.9)
        self.assertAlmostEqual(report.avg_faithfulness, 0.95)
        self.assertAlmostEqual(report.avg_latency_ms, 150.0)
        self.assertEqual(report.healed_count, 1)

        # Test dictionary output
        report_dict = report.to_dict()
        self.assertIn("summary", report_dict)
        self.assertIn("results", report_dict)
        self.assertEqual(report_dict["summary"]["total_cases"], 2)

        # Test markdown table output
        md = report.to_markdown_table()
        self.assertIn("| Query |", md)
        self.assertIn("Q1", md)
        self.assertIn("Q2", md)
        self.assertIn("AVERAGE / SUMMARY", md)


class TestBenchmarkEvaluatorMetrics(unittest.TestCase):
    """Test metric calculations in BenchmarkEvaluator."""

    def setUp(self):
        self.evaluator = BenchmarkEvaluator()

    # ── Context Precision Tests ──────────────────────────────────────────

    def test_calculate_context_precision_perfect_match(self):
        context = "Prasad used AWS ECS Fargate, Lambda, and DynamoDB at Rocket Mortgage."
        entities = ["AWS", "ECS Fargate", "Lambda", "DynamoDB"]
        score = self.evaluator.calculate_context_precision(context, entities)
        self.assertAlmostEqual(score, 1.0)

    def test_calculate_context_precision_partial_match(self):
        context = "Prasad used AWS Lambda and DynamoDB."
        entities = ["AWS", "Lambda", "Kafka", "Kubernetes"]
        score = self.evaluator.calculate_context_precision(context, entities)
        self.assertAlmostEqual(score, 0.5)

    def test_calculate_context_precision_zero_match(self):
        context = "He enjoys playing guitar in his free time."
        entities = ["AWS", "ECS Fargate", "DynamoDB"]
        score = self.evaluator.calculate_context_precision(context, entities)
        self.assertAlmostEqual(score, 0.0)

    def test_calculate_context_precision_empty_inputs(self):
        self.assertEqual(self.evaluator.calculate_context_precision("", ["AWS"]), 0.0)
        self.assertEqual(self.evaluator.calculate_context_precision("Some context", []), 1.0)
        self.assertEqual(self.evaluator.calculate_context_precision("", []), 1.0)

    def test_calculate_context_precision_case_insensitivity(self):
        context = "prasad used aws ecs fargate and kafka."
        entities = ["AWS", "ECS FARGATE", "Kafka"]
        score = self.evaluator.calculate_context_precision(context, entities)
        self.assertAlmostEqual(score, 1.0)

    # ── Context Recall Tests ─────────────────────────────────────────────

    def test_calculate_context_recall_exact_match(self):
        context = (
            "Modernized VB.NET to AWS ECS Fargate cutting infrastructure costs by 40%. "
            "Built Amazon Bedrock AI chatbot reducing loan lookup time by 70%."
        )
        facts = [
            "Modernized VB.NET to AWS ECS Fargate",
            "cutting infrastructure costs by 40%",
            "reducing loan lookup time by 70%",
        ]
        score = self.evaluator.calculate_context_recall(context, facts)
        self.assertAlmostEqual(score, 1.0)

    def test_calculate_context_recall_keyword_overlap(self):
        context = (
            "Prasad modernized legacy VB.NET underwriter applications into cloud-native AWS ECS Fargate "
            "and cut infrastructure expenses by 40 percent."
        )
        facts = [
            "Modernized VB.NET to AWS ECS Fargate",
            "cutting infrastructure costs by 40%",
        ]
        score = self.evaluator.calculate_context_recall(context, facts)
        self.assertGreaterEqual(score, 0.7)

    def test_calculate_context_recall_zero_match(self):
        context = "Prasad attended school in Pune."
        facts = [
            "Modernized VB.NET to AWS ECS Fargate",
            "Established enterprise Kafka governance",
        ]
        score = self.evaluator.calculate_context_recall(context, facts)
        self.assertAlmostEqual(score, 0.0)

    def test_calculate_context_recall_empty_inputs(self):
        self.assertEqual(self.evaluator.calculate_context_recall("", ["Fact 1"]), 0.0)
        self.assertEqual(self.evaluator.calculate_context_recall("Context text", []), 1.0)
        self.assertEqual(self.evaluator.calculate_context_recall("", []), 1.0)

    # ── Faithfulness Tests ───────────────────────────────────────────────

    def test_calculate_faithfulness_fully_grounded(self):
        context = (
            "Prasad Rane built an AI chatbot on Amazon Bedrock using Claude Sonnet. "
            "It reduced loan lookup times by 70%."
        )
        answer = "Prasad developed an AI chatbot on Amazon Bedrock with Claude Sonnet that reduced lookup time by 70%."
        score = self.evaluator.calculate_faithfulness(answer, context)
        self.assertGreaterEqual(score, 0.85)

    def test_calculate_faithfulness_hallucination(self):
        context = "Prasad worked on .NET microservices and AWS ECS Fargate."
        answer = "Prasad worked as the chief flight director at NASA commanding Mars rovers for fifteen years."
        score = self.evaluator.calculate_faithfulness(answer, context)
        self.assertLess(score, 0.3)

    def test_calculate_faithfulness_empty_inputs(self):
        self.assertEqual(self.evaluator.calculate_faithfulness("", "Some context"), 1.0)
        self.assertEqual(self.evaluator.calculate_faithfulness("Some answer", ""), 0.0)
        self.assertEqual(self.evaluator.calculate_faithfulness("", ""), 1.0)


class TestBenchmarkEvaluatorExecution(unittest.TestCase):
    """Test engine evaluation execution in BenchmarkEvaluator."""

    def setUp(self):
        self.evaluator = BenchmarkEvaluator()

    def test_evaluate_case_sync_mock_engine(self):
        case = BenchmarkCase(
            query="What AWS services did Prasad use?",
            query_type="skill_lookup",
            expected_entities=["AWS", "Fargate", "Lambda"],
            ground_truth_facts=["Modernized VB.NET to AWS ECS Fargate"],
        )

        mock_engine = MagicMock()
        mock_engine.retrieve.return_value = {
            "text": "Modernized VB.NET to AWS ECS Fargate and Lambda for microservices."
        }
        mock_engine.format_context.return_value = "Modernized VB.NET to AWS ECS Fargate and Lambda for microservices."

        result = self.evaluator.evaluate_case(case, engine=mock_engine, mode="local", enable_guardrail=False)
        self.assertIsInstance(result, EvaluationResult)
        self.assertEqual(result.case_query, case.query)
        self.assertGreater(result.context_precision, 0.5)
        self.assertGreater(result.context_recall, 0.5)
        self.assertGreater(result.faithfulness, 0.5)
        self.assertGreater(result.latency_ms, 0.0)
        self.assertGreater(result.token_count, 0)
        self.assertEqual(result.retrieval_mode, "local")
        self.assertFalse(result.healed)

    def test_evaluate_case_async_mock_engine(self):
        case = BenchmarkCase(
            query="Tell me about Kafka governance",
            query_type="skill_lookup",
            expected_entities=["Kafka", "AWS MSK", "Schema Registry"],
            ground_truth_facts=["Established enterprise Kafka governance standards"],
        )

        mock_engine = MagicMock()
        mock_engine.retrieve = AsyncMock(return_value={
            "text": "Established enterprise Kafka and AWS MSK governance with Schema Registry."
        })
        mock_engine.format_context = MagicMock(
            return_value="Established enterprise Kafka and AWS MSK governance with Schema Registry."
        )

        result = self.evaluator.evaluate_case(case, engine=mock_engine, mode="drift", enable_guardrail=False)
        self.assertEqual(result.retrieval_mode, "drift")
        self.assertAlmostEqual(result.context_precision, 1.0)
        self.assertFalse(result.healed)

    def test_evaluate_case_guardrail_healing(self):
        case = BenchmarkCase(
            query="Tell me about payment gateway at London Computer Systems",
            query_type="experience_lookup",
            expected_entities=["London Computer Systems", "Payment Gateway"],
            ground_truth_facts=["Integrated ACH and credit card payment gateways"],
        )

        mock_engine = MagicMock()
        mock_engine.retrieve_healed = AsyncMock(return_value=(
            {"text": "At London Computer Systems, integrated ACH and credit card payment gateways."},
            [{"attempt": 1, "is_sufficient": False}, {"attempt": 2, "is_sufficient": True}],
        ))
        mock_engine.format_context = MagicMock(
            return_value="At London Computer Systems, integrated ACH and credit card payment gateways."
        )

        result = self.evaluator.evaluate_case(case, engine=mock_engine, mode="local", enable_guardrail=True)
        self.assertTrue(result.healed)
        self.assertAlmostEqual(result.context_precision, 1.0)
        self.assertAlmostEqual(result.context_recall, 1.0)

    def test_evaluate_dataset(self):
        dataset = [
            BenchmarkCase(
                query="Query 1",
                expected_entities=["AWS"],
                ground_truth_facts=["Used AWS"],
            ),
            BenchmarkCase(
                query="Query 2",
                expected_entities=["Kafka"],
                ground_truth_facts=["Used Kafka"],
            ),
        ]

        mock_engine = MagicMock()
        mock_engine.retrieve.return_value = {"text": "Used AWS and Kafka extensively."}
        mock_engine.format_context.return_value = "Used AWS and Kafka extensively."

        report = self.evaluator.evaluate_dataset(dataset, engine=mock_engine, enable_guardrail=False)
        self.assertIsInstance(report, AggregateBenchmarkReport)
        self.assertEqual(report.total_cases, 2)
        self.assertAlmostEqual(report.avg_context_precision, 1.0)
        self.assertAlmostEqual(report.avg_context_recall, 1.0)
        self.assertIn("Query 1", report.to_markdown_table())


class TestDefaultBenchmarkDataset(unittest.TestCase):
    """Verify default synthetic benchmark dataset covers key resume scenarios."""

    def test_default_dataset_structure(self):
        self.assertIsInstance(DEFAULT_BENCHMARK_DATASET, list)
        self.assertGreaterEqual(len(DEFAULT_BENCHMARK_DATASET), 6)

    def test_default_dataset_query_types(self):
        query_types = {case.query_type for case in DEFAULT_BENCHMARK_DATASET}
        expected_types = {
            "skill_lookup",
            "company_lookup",
            "metrics_lookup",
            "comparative_query",
            "experience_lookup",
        }
        for et in expected_types:
            self.assertIn(et, query_types, f"Query type {et} missing from default dataset")

    def test_default_dataset_scenarios(self):
        queries_text = " ".join([case.query for case in DEFAULT_BENCHMARK_DATASET]).lower()
        entities_text = " ".join([e for c in DEFAULT_BENCHMARK_DATASET for e in c.expected_entities]).lower()

        # AWS ECS Fargate
        self.assertTrue("fargate" in queries_text or "fargate" in entities_text)
        # Kafka at Rocket Mortgage
        self.assertTrue("kafka" in queries_text or "kafka" in entities_text)
        self.assertTrue("rocket mortgage" in queries_text or "rocket mortgage" in entities_text)
        # Payment Gateway at London Computer Systems
        self.assertTrue("payment" in queries_text or "payment" in entities_text)
        self.assertTrue("london computer systems" in queries_text or "london computer systems" in entities_text)
        # Optical devices at EXFO
        self.assertTrue("exfo" in queries_text or "exfo" in entities_text)
        # 70% latency / reduction metrics
        self.assertTrue("70%" in queries_text or any("70%" in f for c in DEFAULT_BENCHMARK_DATASET for f in c.ground_truth_facts))
        # Comparison between companies
        self.assertTrue(any(c.query_type == "comparative_query" for c in DEFAULT_BENCHMARK_DATASET))


if __name__ == "__main__":
    unittest.main()
