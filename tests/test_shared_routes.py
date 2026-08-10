"""
Unit tests that both FastAPI apps serve /api/query and /api/chat-stream from
the single shared router.
"""

import unittest


class TestSharedRoutes(unittest.TestCase):

    def _route_paths(self, app):
        return {getattr(r, "path", None) for r in app.routes}

    def test_local_app_exposes_shared_routes(self):
        from src.web.app import app
        paths = self._route_paths(app)
        self.assertIn("/api/query", paths)
        self.assertIn("/api/chat-stream", paths)

    def test_vercel_app_exposes_shared_routes(self):
        from api.index import app
        paths = self._route_paths(app)
        self.assertIn("/api/query", paths)
        self.assertIn("/api/chat-stream", paths)

    def test_both_apps_use_the_same_handler(self):
        from src.web.app import app as local_app
        from api.index import app as vercel_app
        from src.shared.api_routes import query_endpoint
        for app in (local_app, vercel_app):
            handlers = [r.endpoint for r in app.routes if getattr(r, "path", None) == "/api/query"]
            self.assertIn(query_endpoint, handlers)


if __name__ == "__main__":
    unittest.main()
