# tests/test_post_evaluator.py
import pytest
from src.evaluator.post_evaluator import PostEvaluator

def test_post_evaluator_evaluation_and_scorecard():
    master_content = """
    ## Core Skills
    Python, AWS, Docker, FastApi
    ## Experience
    Company: TechCorp
    - Built microservices on AWS ECS reducing latency by 40%.
    - Implemented REST APIs with FastAPI and Docker.
    """
    resume_text = """
    ## Summary
    Senior Software Engineer with 8+ years experience building cloud applications on AWS and Python.
    ## Experience
    - Built microservices on AWS ECS reducing latency by 40%.
    - Implemented REST APIs with FastAPI and Docker.
    ## Skills
    Python, AWS, Docker, FastAPI
    """
    cover_letter = """
    Dear Hiring Team,
    I am writing to express my enthusiasm for the Senior Software Engineer role at Acme Corp.
    With extensive experience architecting distributed cloud backends with Python, FastAPI, and AWS,
    I have consistently delivered low-latency, scalable microservice architectures.
    """
    jd_text = """
    Looking for a Senior Software Engineer with strong Python, FastAPI, Docker, and AWS microservices background.
    """
    evaluator = PostEvaluator(master_content=master_content)
    scorecard = evaluator.evaluate(
        resume_text=resume_text,
        cover_letter_text=cover_letter,
        jd_text=jd_text,
        iteration=1,
    )
    assert scorecard.ats_score > 60.0
    assert scorecard.story_grounding_score >= 80.0
    assert scorecard.format_compliance is True
    assert scorecard.cover_letter_score >= 70.0
    assert scorecard.verdict in ["APPROVED", "NEEDS_REFINEMENT"]
    assert "Iteration 1" in scorecard.critique_summary

def test_post_evaluator_empty_inputs():
    evaluator = PostEvaluator(master_content="")
    scorecard = evaluator.evaluate(
        resume_text="",
        cover_letter_text="",
        jd_text="",
        iteration=1,
    )
    assert scorecard.ats_score == 0.0
    assert scorecard.format_compliance is False
    assert len(scorecard.actionable_refinements) > 0
