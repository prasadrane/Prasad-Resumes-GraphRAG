"""
Baseline characterization tests for the deterministic (non-LLM) API surface
of the local UI server (src.web.app:app).

These tests record the currently working behavior. They must pass before any
refactoring begins and after every change, acting as the safety net.
"""

import base64

import httpx


def test_root_serves_ui(app_server):
    resp = httpx.get(f"{app_server}/", timeout=30.0)
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")


def test_history_returns_list(app_server):
    resp = httpx.get(f"{app_server}/api/history", timeout=30.0)
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    for item in body:
        assert "company" in item
        assert "pdf_url" in item


def test_default_resume_returns_pdf(app_server):
    resp = httpx.get(f"{app_server}/api/default-resume", timeout=90.0)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert len(body["raw_resume"]) > 0
    # Local server returns a data URI (same contract as serverless).
    pdf_url = body["pdf_url"]
    assert pdf_url.startswith("data:application/pdf;base64,")
    # Decode and verify PDF magic bytes
    b64_data = pdf_url.split(",", 1)[1]
    assert base64.b64decode(b64_data)[:4] == b"%PDF"


def test_render_pdf_from_raw_text(app_server):
    raw_text = (
        "PRASAD RANE\n"
        "Contact: prasad@example.com | https://linkedin.com/in/prasad\n\n"
        "EXECUTIVE SUMMARY\n"
        "Experienced software engineer building cloud platforms.\n\n"
        "TECHNICAL SKILLS\n"
        "Languages: Python, SQL\n\n"
        "EXPERIENCE\n"
        "Senior Engineer, Acme Corp | Jan 2020 - Present\n"
        "- Built distributed systems in Python and AWS\n"
    )
    resp = httpx.post(
        f"{app_server}/api/render_pdf",
        json={"raw_text": raw_text, "company": "Baseline"},
        timeout=90.0,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    pdf_url = body["pdf_url"]
    assert pdf_url.startswith("data:application/pdf;base64,")
    pdf_bytes = base64.b64decode(pdf_url.split(",", 1)[1])
    assert pdf_bytes[:4] == b"%PDF"
