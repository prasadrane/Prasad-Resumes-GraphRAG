# tests/test_evaluator_api.py
import pytest
from fastapi.testclient import TestClient
from src.web.app import app

client = TestClient(app)

def test_evaluator_feasibility_endpoint():
    response = client.post(
        "/api/evaluator/feasibility",
        json={
            "company": "Stripe",
            "jd_text": "Looking for Senior Backend Engineer with Python, AWS, and Docker.",
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "baseline_match_pct" in data
    assert "verdict" in data
    assert data["verdict"] in ["STRONG_MATCH", "TAILORABLE", "HIGH_GAP", "DO_NOT_APPLY"]

def test_evaluator_tailor_endpoint():
    response = client.post(
        "/api/evaluator/tailor",
        json={
            "company": "TechCorp",
            "jd_text": "Senior Engineer with Python and AWS.",
            "max_turns": 1,
            "auto_refine": True,
            "generate_cover_letter": True,
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "feasibility" in data
    assert "scorecard" in data
    assert "status" in data
