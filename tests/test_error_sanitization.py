"""
Regression tests: 500 responses and SSE error events must not leak raw
exception text, and the save-edit traversal guard must surface 403.
"""

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient


class TestErrorSanitization(unittest.TestCase):

    def test_local_query_500_does_not_leak_exception_text(self):
        from src.web.app import app
        client = TestClient(app)
        with patch(
            "src.shared.api_routes.execute_graphrag_query",
            side_effect=RuntimeError("SECRET_DB_PASSWORD"),
        ):
            response = client.post("/api/query", json={"query": "anything", "mode": "local"})
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("SECRET_DB_PASSWORD", response.json()["detail"])

    def test_vercel_generate_500_does_not_leak_exception_text(self):
        from api.index import app
        client = TestClient(app)
        with patch("src.web.app.generate_raw_resume", side_effect=RuntimeError("SECRET_API_KEY")):
            response = client.post("/api/generate", json={"company": "LeakCo", "jd_text": "Python"})
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("SECRET_API_KEY", response.json()["detail"])

    def test_save_edit_traversal_txt_url_returns_403_not_masked_500(self):
        from src.web.app import app
        client = TestClient(app)
        response = client.post("/api/save-edit", json={
            "txt_url": "/api/files/../../../../../../etc/passwd",
            "content": "malicious",
        })
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Access denied.")


if __name__ == "__main__":
    unittest.main()
