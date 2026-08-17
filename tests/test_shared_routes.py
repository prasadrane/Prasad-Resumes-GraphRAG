"""
Unit tests that both FastAPI apps serve /api/query, /api/chat-stream, /api/ats-score,
and /api/extract-jd-url from the single shared router.
"""

import unittest
from fastapi.testclient import TestClient


class TestSharedRoutes(unittest.TestCase):

    def test_local_app_exposes_shared_routes(self):
        from src.web.app import app
        client = TestClient(app)
        # Verify routes respond (not 404)
        resp = client.post("/api/ats-score", json={"company": "Test", "jd_text": "Short", "raw_resume": "Test"})
        self.assertNotEqual(resp.status_code, 404)

        resp = client.post("/api/extract-jd-url", json={"url": "invalid-url"})
        self.assertNotEqual(resp.status_code, 404)

        resp = client.post("/api/save-edit", json={})
        self.assertNotEqual(resp.status_code, 404)

    def test_vercel_app_exposes_shared_routes(self):
        from api.index import app
        client = TestClient(app)
        # Verify routes respond (not 404)
        resp = client.post("/api/ats-score", json={"company": "Test", "jd_text": "Short", "raw_resume": "Test"})
        self.assertNotEqual(resp.status_code, 404)

        resp = client.post("/api/extract-jd-url", json={"url": "invalid-url"})
        self.assertNotEqual(resp.status_code, 404)

        resp = client.post("/api/save-edit", json={})
        self.assertNotEqual(resp.status_code, 404)

    def test_both_apps_use_the_same_shared_router(self):
        from src.web.app import app as local_app
        from api.index import app as vercel_app
        from src.shared.api_routes import shared_router

        # Verify shared_router has expected endpoints
        router_paths = {r.path for r in shared_router.routes}
        self.assertIn("/api/query", router_paths)
        self.assertIn("/api/chat-stream", router_paths)
        self.assertIn("/api/ats-score", router_paths)
        self.assertIn("/api/extract-jd-url", router_paths)
        self.assertIn("/api/save-edit", router_paths)
        self.assertIn("/api/render_pdf", router_paths)


if __name__ == "__main__":
    unittest.main()
