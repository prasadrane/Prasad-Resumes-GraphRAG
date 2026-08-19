"""
test_career_studio_api.py — Unit tests for Cover Letter, Interview Prep, and LinkedIn Profile API routes.
"""

import pytest
from fastapi.testclient import TestClient
from src.web.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_cover_letter_generation(client):
    response = client.post(
        "/api/cover-letter",
        json={
            "company": "Lyft",
            "role_title": "Senior Software Engineer, Lyft Business",
            "jd_text": "Looking for a Senior Software Engineer with AWS, Python, Kubernetes, Kafka, and Microservices.",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "Lyft" in data["markdown"]
    assert "Prasad Rane" in data["markdown"]
    assert "AWS" in data["markdown"] or "microservices" in data["markdown"].lower()


def test_cover_letter_missing_company(client):
    response = client.post("/api/cover-letter", json={"company": ""})
    assert response.status_code in (400, 422)


def test_interview_prep_generation(client):
    response = client.post(
        "/api/interview-prep",
        json={
            "jd_text": "Proficiency in AWS, Python, Kafka, and Kubernetes required.",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["questions"]) > 0
    assert len(data["talking_points"]) > 0


def test_linkedin_profile_generation(client):
    response = client.post(
        "/api/linkedin-profile",
        json={
            "target_role": "Staff Cloud Architect",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "Staff Cloud Architect" in data["headline"]
    assert "Prasad Rane" in data["about"] or "experience" in data["about"]


def test_telemetry_stats_endpoint(client):
    response = client.get("/api/telemetry-stats")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "avg_ats_score" in data
