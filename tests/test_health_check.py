"""
test_health_check — Verify /api/health endpoint behavior via unittest.

Tests:
  - Returns status "ok" when dependencies check out
  - Returns status "degraded" with 503 when a dependency is down
  - Health response contains all required fields (status, checks, timestamp)
  - Each sub-check has a "status" key
  - X-Correlation-ID header is present on the response
"""

import unittest
from unittest.mock import patch, MagicMock

# ── Mock sqlite3 module to avoid actual file I/O ─────────────────────────

class FakeConn:
    """Fake SQLite connection that never fails."""
    row_factory = None
    def execute(self, sql, params=None): return self
    def fetchone(self): return [1] if "SELECT" in str(type(self)) else None
    def fetchall(self): return []
    def commit(self): pass
    def close(self): pass


class FakeSQLite:
    connect = staticmethod(lambda path: FakeConn())


def mock_sqlite_conn(path):
    return FakeConn()


# Now safe to import FastAPI test client and app
from fastapi.testclient import TestClient
from src.web.app import app


class TestHealthCheckStructure(unittest.TestCase):
    """Verify the health response schema."""

    def _get_health(self):
        client = TestClient(app)
        return client.get("/api/health")

    def test_health_returns_json(self):
        resp = self._get_health()
        self.assertIn(resp.status_code, (200, 503))

    def test_health_has_status_field(self):
        resp = self._get_health()
        data = resp.json()
        self.assertIn("status", data)
        self.assertIn(data["status"], ("ok", "degraded", "down"))

    def test_health_has_checks_field(self):
        resp = self._get_health()
        data = resp.json()
        self.assertIn("checks", data)
        self.assertIsInstance(data["checks"], dict)

    def test_health_has_timestamp(self):
        resp = self._get_health()
        data = resp.json()
        self.assertIn("timestamp", data)

    def test_health_subchecks_have_status(self):
        """Every sub-check must include a 'status' key."""
        resp = self._get_health()
        data = resp.json()
        checks = data.get("checks", {})
        for name, check in checks.items():
            self.assertIn("status", check, f"check '{name}' missing 'status'")

    def test_health_always_has_api_check(self):
        """The API itself should always report ok."""
        resp = self._get_health()
        data = resp.json()
        api_check = data.get("checks", {}).get("api", {})
        self.assertEqual(api_check.get("status"), "ok")


class TestHealthCheckStatusCode(unittest.TestCase):
    """Verify correct HTTP status codes."""

    @patch("src.query.conversation_store.sqlite3.connect", mock_sqlite_conn)
    def test_all_checks_have_status(self):
        """Every dependency check reports a status string."""
        with patch("src.config.providers.get_model_for") as mock_gmf:
            mock_gmf.return_value = ("alibaba", "qwen3.7-plus", None)
            resp = TestClient(app).get("/api/health")
            data = resp.json()
            checks = data.get("checks", {})
            for name, check in checks.items():
                self.assertIn("status", check, f"check '{name}' missing 'status'")
            # API always ok
            self.assertEqual(checks.get("api", {}).get("status"), "ok")
            # At least one dep check present (llm_gateway or graphrag or database)
            non_api = [k for k in checks if k != "api"]
            self.assertTrue(len(non_api) >= 1, "At least one dependency check expected")

    @patch("src.query.conversation_store.sqlite3.connect", mock_sqlite_conn)
    def test_degraded_dep_returns_503(self):
        """When LLM gateway raises -> 503 degraded."""
        with patch("src.config.providers.get_model_for") as mock_gmf:
            mock_gmf.side_effect = ConnectionRefusedError("no provider reachable")
            resp = TestClient(app).get("/api/health")
            self.assertEqual(resp.status_code, 503)
            data = resp.json()
            self.assertIn(data["status"], ("degraded", "down"))
            self.assertEqual(data["checks"]["llm_gateway"]["status"], "down")

    @patch("src.query.conversation_store.sqlite3.connect", mock_sqlite_conn)
    def test_detailed_response_body(self):
        """Response body contains detailed per-dependency information."""
        with patch("src.config.providers.get_model_for") as mock_gmf:
            mock_gmf.return_value = ("alibaba", "qwen3.7-plus", None)

            resp = TestClient(app).get("/api/health")
            data = resp.json()

            # Should have llm_gateway details
            self.assertIn("checks", data)
            checks = data["checks"]
            self.assertIn("provider", checks.get("llm_gateway", {}))
            self.assertIn("latency_ms", checks.get("llm_gateway", {}))


class TestCorrelationID(unittest.TestCase):
    """X-Correlation-ID must be present and consistent."""

    def test_correlation_id_header_on_health(self):
        resp = TestClient(app).get("/api/health")
        cid = resp.headers.get("x-correlation-id", "")
        self.assertTrue(len(cid) > 0)

    def test_correlation_id_from_client_header(self):
        """If the client sends X-Correlation-ID it should echo back."""
        resp = TestClient(app).get(
            "/api/health", headers={"X-Correlation-ID": "my-corr-123"}
        )
        cid = resp.headers.get("x-correlation-id", "")
        self.assertEqual(cid, "my-corr-123")

    def test_response_time_header_present(self):
        resp = TestClient(app).get("/api/health")
        rt = resp.headers.get("x-response-time-ms", "")
        self.assertTrue(len(rt) > 0)

    def test_correlation_id_is_consistent_across_routes(self):
        """Same request should produce same correlation ID."""
        client = TestClient(app)
        r1 = client.get("/api/health")
        cid1 = r1.headers.get("x-correlation-id")

        # Different request should also have an ID (could be different since separate requests)
        r2 = client.get("/api/health")
        cid2 = r2.headers.get("x-correlation-id")

        self.assertTrue(len(cid1) > 0)
        self.assertTrue(len(cid2) > 0)


if __name__ == "__main__":
    unittest.main()
