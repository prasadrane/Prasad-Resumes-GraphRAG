"""
test_bm25_search.py — Unit tests for BM25 Okapi sparse search and Reciprocal Rank Fusion.
"""

import pytest
import pandas as pd

from src.query.bm25_search import BM25Index, reciprocal_rank_fusion, tokenize_code_and_text


def test_tokenize_code_and_text():
    text = "Architected AWS EKS, Kafka & C# .NET microservices with 99.99% uptime!"
    tokens = tokenize_code_and_text(text)
    assert "aws" in tokens
    assert "eks" in tokens
    assert "kafka" in tokens
    assert "c#" in tokens or "csharp" in tokens
    assert ".net" in tokens or "dotnet" in tokens
    assert "99.99" in tokens or "99.99%" in tokens


def test_bm25_index_basic_scoring():
    docs = [
        "Architected AWS EKS clusters and Kafka event streaming for low latency.",
        "Developed Python FastAPI microservices with PostgreSQL and Redis caching.",
        "Led team of 15 engineers in agile sprint planning and stakeholder management.",
        "Engineered Terraform IaC modules for multi-region AWS cloud deployments."
    ]
    index = BM25Index(docs)
    
    # Query matching doc 0 and 3 on AWS, but doc 0 on Kafka/EKS
    results = index.search("Kafka EKS", top_k=2)
    assert len(results) >= 1
    top_doc_idx, top_score = results[0]
    assert top_doc_idx == 0
    assert top_score > 0.0

    # Query matching doc 1 on Python FastAPI
    py_results = index.search("Python FastAPI", top_k=2)
    assert py_results[0][0] == 1


def test_bm25_dataframe_search():
    df = pd.DataFrame({
        "id": ["tu_1", "tu_2", "tu_3"],
        "text": [
            "Prasad Rane reduced latency by 45% using AWS Lambda and S3.",
            "Containerized legacy applications using Docker and Kubernetes.",
            "Implemented CI/CD pipelines using GitHub Actions and ArgoCD."
        ]
    })
    index = BM25Index.from_dataframe(df, text_col="text", id_col="id")
    matches = index.search_df("AWS Lambda S3", top_k=1)
    assert not matches.empty
    assert matches.iloc[0]["id"] == "tu_1"


def test_reciprocal_rank_fusion():
    # dense returned [A, B, C, D]
    # sparse returned [C, A, E, B]
    dense_items = ["A", "B", "C", "D"]
    sparse_items = ["C", "A", "E", "B"]

    fused = reciprocal_rank_fusion([dense_items, sparse_items], k=60)
    
    # 'A' was rank 0 in dense, rank 1 in sparse -> 1/61 + 1/62
    # 'C' was rank 2 in dense, rank 0 in sparse -> 1/63 + 1/61
    assert len(fused) == 5
    top_item, top_score = fused[0]
    assert top_item in ["A", "C"]
    assert top_score > 0.0
