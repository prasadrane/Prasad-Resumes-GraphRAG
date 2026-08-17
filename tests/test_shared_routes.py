"""
Unit tests that both FastAPI apps serve /api/query and /api/chat-stream from
the single shared router.
"""

import unittest


class TestSharedRoutes(unittest.TestCase):

    def _route_paths(self, app):
        routes = getattr(getattr(app, "router", None), "routes", getattr(app, "routes", []))
        paths = set()
        for r in routes:
            p = getattr(r, "path", None)
            if p:
                paths.add(p)
            if hasattr(r, "routes"):
                for sub_r in r.routes:
                    sub_p = getattr(sub_r, "path", None)
                    if sub_p:
                        paths.add(sub_p)
        return paths

    def _has_shared_routes(self, app):
        """Check if shared router routes are registered."""
        paths = self._route_paths(app)
        return "/api/query" in paths and "/api/chat-stream" in paths

    def test_local_app_exposes_shared_routes(self):
        from src.web.app import app
        paths = self._route_paths(app)
        self.assertIn("/api/query", paths)
        self.assertIn("/api/chat-stream", paths)
        self.assertIn("/api/save-edit", paths)
        self.assertIn("/api/render_pdf", paths)
        self.assertIn("/api/ats-score", paths)
        self.assertIn("/api/extract-jd-url", paths)

    def test_vercel_app_exposes_shared_routes(self):
        from api.index import app
        paths = self._route_paths(app)
        self.assertIn("/api/query", paths)
        self.assertIn("/api/chat-stream", paths)
        self.assertIn("/api/save-edit", paths)
        self.assertIn("/api/render_pdf", paths)
        self.assertIn("/api/ats-score", paths)
        self.assertIn("/api/extract-jd-url", paths)

    def test_both_apps_use_the_same_handler(self):
        from src.web.app import app as local_app
        from api.index import app as vercel_app
        from src.shared.api_routes import query_endpoint
        for app in (local_app, vercel_app):
            routes = getattr(getattr(app, "router", None), "routes", getattr(app, "routes", []))
            handlers = []
            for r in routes:
                if getattr(r, "path", None) == "/api/query":
                    handlers.append(r.endpoint)
                if hasattr(r, "routes"):
                    for sub_r in r.routes:
                        if getattr(sub_r, "path", None) == "/api/query":
                            handlers.append(sub_r.endpoint)
            self.assertIn(query_endpoint, handlers)


if __name__ == "__main__":
    unittest.main()
