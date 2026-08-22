# tests/test_feasibility_checker.py
import pytest
from src.evaluator.feasibility_checker import FeasibilityChecker

def test_feasibility_checker_strong_match():
    master_content = """
    ## Core Skills
    Python, C#, AWS, Docker, Kubernetes, Microservices, DynamoDB, FastApi
    ## Gap-Framing
    | Kubernetes | Yes | Managed multi-cluster K8s deployments on AWS |
    """
    jd_text = """
    We are looking for a Senior Backend Engineer proficient in Python, AWS, Docker, Microservices, and DynamoDB.
    """
    checker = FeasibilityChecker(master_content=master_content)
    report = checker.check_feasibility(jd_text, company_name="TechCorp")
    assert report.verdict in ["STRONG_MATCH", "TAILORABLE"]
    assert report.baseline_match_pct >= 50.0
    assert len(report.matched_skills) > 0

    blueprint = checker.build_strategy_blueprint(jd_text, company_name="TechCorp", feasibility=report)
    assert blueprint.target_company == "TechCorp"
    assert len(blueprint.must_include_keywords) > 0

def test_feasibility_checker_severe_gap_do_not_apply():
    master_content = """
    ## Core Skills
    C#, .NET, Python, AWS
    """
    jd_text = """
    Looking for a Lead Hardware Design Engineer specializing in FPGA, Verilog, VHDL, RTOS, and Oscilloscope Signal Processing.
    """
    checker = FeasibilityChecker(master_content=master_content)
    report = checker.check_feasibility(jd_text, company_name="HardwareCorp")
    assert report.verdict in ["HIGH_GAP", "DO_NOT_APPLY"]
    assert len(report.unfillable_gaps) > 0

def test_feasibility_checker_empty_jd():
    checker = FeasibilityChecker(master_content="Some content")
    report = checker.check_feasibility("", company_name="")
    assert report.verdict == "DO_NOT_APPLY"
    assert report.baseline_match_pct == 0.0
