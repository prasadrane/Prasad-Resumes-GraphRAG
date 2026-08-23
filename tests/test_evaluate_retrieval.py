"""
test_evaluate_retrieval.py — Unit tests for GraphRAG retrieval evaluation and Ragas-style triad metrics.
"""

import pytest
from pathlib import Path
import json

from evaluation.evaluate_retrieval import (
    _precision_recall,
    _compute_context_relevance,
    _compute_groundedness_estimate,
    evaluate_query,
    format_markdown_report,
)


def test_precision_recall_metric():
    got = {"aws", "ec2", "s3", "lambda", "python"}
    expected = {"aws", "ec2", "s3", "fargate"}
    
    # 3 true positives (aws, ec2, s3)
    # len(got) = 5 -> prec = 3/5 = 0.6
    # len(expected) = 4 -> rec = 3/4 = 0.75
    metrics = _precision_recall(got, expected)
    assert metrics["precision"] == 0.6
    assert metrics["recall"] == 0.75
    assert metrics["f1"] > 0.6


def test_context_relevance_metric():
    response = "Prasad Rane has extensive experience with AWS, EC2, S3, and Lambda functions in microservices."
    expected_keywords = {"aws", "ec2", "s3", "lambda"}
    
    relevance = _compute_context_relevance(response, expected_keywords)
    assert relevance > 0.0
    assert relevance <= 1.0


def test_groundedness_estimate():
    response = "Architected AWS ECS Fargate microservices cutting cloud costs by 40%."
    graph_context = "Spearheaded cloud modernization to AWS ECS Fargate (.NET Core), cutting infrastructure costs by 40%."
    
    groundedness = _compute_groundedness_estimate(response, graph_context)
    assert groundedness >= 0.7


def test_format_markdown_report():
    results = [
        {
            "id": 1,
            "query": "What AWS services has Prasad used?",
            "category": "skill_lookup",
            "mode": "local",
            "entity_metrics": {"precision": 0.8, "recall": 0.9, "f1": 0.85},
            "keyword_metrics": {"precision": 0.7, "recall": 0.8, "f1": 0.75},
            "context_relevance": 0.88,
            "found_at_least_one": True,
        }
    ]
    report = format_markdown_report(results)
    assert "GraphRAG Retrieval Evaluation Report" in report
    assert "What AWS services has Prasad used?" in report
    assert "skill_lookup" in report
