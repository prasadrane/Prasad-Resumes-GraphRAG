"""
test_agentic_stream_api.py — Integration tests for SSE streaming agentic endpoint.
"""

import json
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from src.web.app import app
from src.agents.models import AgentEvent


@pytest.fixture
def client():
    return TestClient(app)


def test_agentic_stream_endpoint_missing_input(client):
    response = client.post("/api/stream-agent-tailor", json={})
    assert response.status_code == 400


@patch("src.web.app.AgenticPipelineOrchestrator")
def test_agentic_stream_endpoint_with_jd_text(mock_orch_cls, client, tmp_path):
    mock_orch = MagicMock()
    mock_orch_cls.return_value = mock_orch
    
    mock_orch.run.return_value = [
        AgentEvent(
            step="ingestion",
            agent="JobIngestionAgent",
            status="Ingested JD text for Databricks",
            payload={"posting": {"company": "Databricks", "role_title": "Cloud Architect"}}
        ),
        AgentEvent(
            step="critic_eval",
            agent="ATSCriticAgent",
            status="Initial score 77.0%",
            payload={"iteration": 0, "score": 77.0}
        ),
        AgentEvent(
            step="complete",
            agent="PDFTypesetterAgent",
            status="Complete",
            payload={
                "company": "Databricks",
                "role_title": "Cloud Architect",
                "final_score": 93.0,
                "pdf_path": str(tmp_path / "Prasad_Rane_Resume.pdf"),
                "raw_resume": "Resume Markdown Content",
                "diffs": [],
                "iterations_count": 1,
            }
        ),
    ]
    
    # Create fake dummy pdf for _pdf_to_data_uri
    dummy_pdf = tmp_path / "Prasad_Rane_Resume.pdf"
    dummy_pdf.write_bytes(b"%PDF-1.4 dummy pdf bytes")
    
    response = client.post(
        "/api/stream-agent-tailor",
        json={
            "company": "Databricks",
            "jd_text": "Looking for Cloud Architect with AWS, Kubernetes, Terraform, and Python.",
            "max_iterations": 2,
            "min_score": 90.0,
        },
    )
    
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    
    # Parse SSE events from body
    lines = response.text.strip().split("\n\n")
    events = [json.loads(line.replace("data: ", "")) for line in lines if line.startswith("data: ")]
    
    assert len(events) == 3
    assert events[0]["step"] == "ingestion"
    assert events[1]["step"] == "critic_eval"
    assert events[2]["step"] == "complete"
    assert events[2]["payload"]["final_score"] == 93.0
