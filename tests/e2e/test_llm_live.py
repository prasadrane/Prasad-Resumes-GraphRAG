"""
Live LLM end-to-end tests. These call real LLM APIs (via the serverless
gateway) and therefore cost credits and can be slow/flaky. They are marked
`live` and excluded by default (see pytest.ini addopts `-m "not live"`).

Run explicitly with:  pytest tests/e2e/ -m live
"""

import httpx
import pytest

pytestmark = pytest.mark.live


def test_query_returns_response(app_server):
    resp = httpx.post(
        f"{app_server}/api/query",
        json={"query": "What AWS technologies did Prasad use?", "mode": "local"},
        timeout=180.0,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert len(body["response"]) > 0


def test_generate_returns_resume(app_server):
    jd_text = (
        "Looking for a senior engineer with Python, AWS, Kubernetes, and "
        "experience building LLM-powered platform tooling."
    )
    resp = httpx.post(
        f"{app_server}/api/generate",
        json={"company": "LiveTestCo", "jd_text": jd_text},
        timeout=600.0,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert len(body["raw_resume"]) > 0


def test_chat_stream_emits_done(app_server):
    with httpx.stream(
        "POST",
        f"{app_server}/api/chat-stream",
        json={"query": "Summarize Prasad's career.", "mode": "local"},
        timeout=300.0,
    ) as resp:
        assert resp.status_code == 200
        chunks = "".join(resp.iter_text())
    assert "event: done" in chunks or "event: error" in chunks
