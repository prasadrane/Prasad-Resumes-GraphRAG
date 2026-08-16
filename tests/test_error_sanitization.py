"""
Regression tests: 500 responses and SSE error events must not leak raw
exception text, and the save-edit traversal guard must surface 403.
"""

import unittest
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient


class TestErrorSanitization(unittest.TestCase):

    def test_local_query_500_does_not_leak_exception_text(self):
        from src.web.app import app
        from unittest.mock import AsyncMock
        client = TestClient(app)
        # The query endpoint goes through `get_engine()` → engine.chat_stream().
        # Patch get_engine to return a mock whose chat_stream raises, so the
        # exception handler in _handle_query_core sanitizes the message.
        mock_engine = MagicMock()
        async def failing_stream(*args, **kwargs):
            raise RuntimeError("SECRET_DB_PASSWORD")
            yield "never_yielded"
        mock_engine.chat_stream = failing_stream
        with patch("src.shared.api_routes.get_engine", return_value=mock_engine):
            response = client.post("/api/query", json={"query": "anything", "mode": "local"})
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("SECRET_DB_PASSWORD", response.json()["detail"])

    def test_vercel_generate_500_does_not_leak_exception_text(self):
        from api.index import app
        from tests.conftest import VALID_JD_TEXT
        client = TestClient(app)
        with patch("src.web.app.generate_raw_resume", side_effect=RuntimeError("SECRET_API_KEY")):
            response = client.post("/api/generate", json={"company": "LeakCo", "jd_text": VALID_JD_TEXT})
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
