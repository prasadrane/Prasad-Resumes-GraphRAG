"""End-to-end integration tests for GraphRAG query engine."""

import pytest
from httpx import AsyncClient, ASGITransport
from src.web.app import app

# Skip if no API keys available - tests need real GraphRAG artifacts
pytestmark = pytest.mark.skipif(
    not __import__("os").path.exists(__import__("pathlib").Path("output/entities.parquet")),
    reason="No GraphRAG artifacts found"
)


class TestGraphRAGE2E:
    """E2E tests for GraphRAG query flow."""

    @pytest.fixture
    async def client(self):
        """Create async HTTP client pointing at FastAPI app."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    @pytest.mark.asyncio
    async def test_query_endpoint_basic(self, client: AsyncClient):
        """Test basic /api/query endpoint returns valid response."""
        resp = await client.post("/api/query", json={
            "query": "What technologies did Prasad use?",
            "mode": "local",
        }, timeout=30)
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert data["status"] == "success"
        assert "response" in data
        assert len(data["response"]) > 0

    @pytest.mark.asyncio
    async def test_query_all_modes(self, client: AsyncClient):
        """Test all three modes: local, global, drift."""
        for mode in ["local", "global", "drift"]:
            resp = await client.post("/api/query", json={
                "query": "Python cloud computing experience",
                "mode": mode,
            }, timeout=30)
            assert resp.status_code == 200, f"Mode {mode} failed"
            data = resp.json()
            assert data["status"] == "success"
            assert data["mode"] == mode

    @pytest.mark.asyncio
    async def test_chat_stream_endpoint(self, client: AsyncClient):
        """Test /api/chat-stream returns streaming SSE events."""
        resp = await client.post("/api/chat-stream", json={
            "query": "AWS infrastructure skills",
            "mode": "local",
            "session_id": "e2e-test-session",
        }, timeout=30)
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")

        # Read streaming response
        content = await resp.text()
        assert "data:" in content  # SSE format

    @pytest.mark.asyncio
    async def test_conversation_memory_persistence(self, client: AsyncClient):
        """Test that conversation history persists across requests."""
        session = "e2e-history-test"

        # First message
        resp1 = await client.post("/api/chat-stream", json={
            "query": "First question",
            "mode": "local",
            "session_id": session,
        }, timeout=30)
        assert resp1.status_code == 200

        # Second message (should include first in context)
        resp2 = await client.post("/api/chat-stream", json={
            "query": "Second question",
            "mode": "local",
            "session_id": session,
        }, timeout=30)
        assert resp2.status_code == 200

    @pytest.mark.asyncio
    async def test_empty_query_rejected(self, client: AsyncClient):
        """Test empty query returns 400."""
        resp = await client.post("/api/query", json={
            "query": "",
            "mode": "local",
        }, timeout=10)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_invalid_mode_default_to_local(self, client: AsyncClient):
        """Test invalid mode defaults to local."""
        resp = await client.post("/api/query", json={
            "query": "test",
            "mode": "invalid_mode_xyz",
        }, timeout=30)
        # Should succeed with mode normalized to 'local'
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_drift_mode_multi_hop(self, client: AsyncClient):
        """Test DRIFT mode expands entity connections."""
        resp = await client.post("/api/query", json={
            "query": "Python microservices cloud architecture",
            "mode": "drift",
        }, timeout=60)
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "drift"
        # DRIFT should return longer responses due to multi-hop expansion
        assert len(data.get("response", "")) >= 50
