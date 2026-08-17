"""
Unit tests for the shared API request models and the unified Vercel contract.
"""

import unittest

from fastapi.testclient import TestClient

from src.shared.api_models import QueryRequest, ResumeGenerationRequest, SaveEditRequest


class TestSharedApiModels(unittest.TestCase):

    def test_query_request_defaults(self):
        req = QueryRequest(query="hello")
        self.assertEqual(req.mode, "local")

    def test_generation_request_defaults(self):
        req = ResumeGenerationRequest(company="Acme")
        self.assertEqual(req.jd_text, "")

    def test_save_edit_request_fields_optional(self):
        req = SaveEditRequest()
        self.assertIsNone(req.raw_text)
        self.assertIsNone(req.content)
        self.assertIsNone(req.txt_url)
        self.assertEqual(req.company, "Tailored")

    def test_vercel_render_pdf_accepts_content_alias(self):
        from api.index import app
        client = TestClient(app)
        raw = "# Prasad Rane\n\n## Professional Summary\nAlias field test.\n"
        response = client.post("/api/render_pdf", json={"content": raw})
        self.assertEqual(response.status_code, 200)
    def test_query_request_allows_technical_sql_words(self):
        req = QueryRequest(query="How did Prasad optimize SQL SELECT and UPDATE performance?")
        self.assertEqual(req.query, "How did Prasad optimize SQL SELECT and UPDATE performance?")

    def test_query_request_rejects_script_injection(self):
        with self.assertRaises(ValueError):
            QueryRequest(query="<script>alert('xss')</script>")


if __name__ == "__main__":
    unittest.main()
