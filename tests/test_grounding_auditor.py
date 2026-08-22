# tests/test_grounding_auditor.py
import pytest
from src.evaluator.grounding_auditor import GroundingAuditor

def test_grounding_auditor_authentic_text():
    master_text = """
    ## Experience
    Company: TechCorp
    - Architected C# .NET microservices on AWS ECS reducing latency by 40%.
    - Built streaming data pipelines using Apache Kafka and DynamoDB.
    """
    resume_text = """
    ## Experience
    - Architected C# .NET microservices on AWS ECS reducing latency by 40%.
    - Built streaming data pipelines using Apache Kafka and DynamoDB.
    """
    auditor = GroundingAuditor(master_content=master_text)
    score, violations = auditor.audit(resume_text)
    assert score >= 85.0
    assert len(violations) == 0

def test_grounding_auditor_detects_hallucination():
    master_text = """
    ## Experience
    Company: TechCorp
    - Architected C# .NET microservices on AWS ECS reducing latency by 40%.
    """
    resume_text = """
    ## Experience
    - Built quantum entanglement cryptographic algorithms in Rust with 99.999% fidelity on custom ASIC hardware.
    """
    auditor = GroundingAuditor(master_content=master_text)
    score, violations = auditor.audit(resume_text)
    assert score < 60.0
    assert len(violations) > 0
    assert "quantum" in violations[0].lower() or "unverified" in violations[0].lower()

def test_grounding_auditor_empty_input():
    auditor = GroundingAuditor(master_content="")
    score, violations = auditor.audit("")
    assert score == 0.0
    assert len(violations) > 0
