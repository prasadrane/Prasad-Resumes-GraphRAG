"""
test_web_ui.py — Integration and Unit Tests for Web UI FastAPI Backend.
"""

import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
from fastapi.testclient import TestClient

from src.web.app import app, ROOT_DIR


class TestWebUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.test_output_dir = ROOT_DIR / "output" / "TestCompanyUI"
        cls.test_output_dir.mkdir(parents=True, exist_ok=True)
        cls.test_pdf = cls.test_output_dir / "Prasad_Rane_Resume.pdf"
        cls.test_pdf.write_bytes(b"%PDF-1.4 Mock PDF Content")

    @classmethod
    def tearDownClass(cls):
        if cls.test_pdf.exists():
            cls.test_pdf.unlink()
        if cls.test_output_dir.exists():
            try:
                cls.test_output_dir.rmdir()
            except OSError:
                pass

    def test_default_resume_endpoint(self):
        """Test GET /api/default-resume returns master resume PDF and raw text."""
        response = self.client.get("/api/default-resume")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("pdf_url", data)
        self.assertIn("raw_resume", data)
        self.assertIn("PRASAD RANE", data["raw_resume"])

    def test_default_resume_1p_endpoint(self):
        """Test GET /api/default-resume?pages=1 returns 1-page budgeted resume."""
        response = self.client.get("/api/default-resume?pages=1")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data.get("pages"), 1)
        self.assertIn("pdf_url", data)

    def test_default_resume_2p_endpoint(self):
        """Test GET /api/default-resume?pages=2 returns 2-page budgeted resume."""
        response = self.client.get("/api/default-resume?pages=2")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data.get("pages"), 2)
        self.assertIn("pdf_url", data)

    def test_history_endpoint(self):
        """Test GET /api/history returns valid resume history entries."""
        response = self.client.get("/api/history")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        companies = [item.get("company") for item in data]
        self.assertIn("TestCompanyUI", companies)

    def test_pdf_serve_endpoint(self):
        """Test GET /api/pdf/{company}/{filename} serves the correct file."""
        response = self.client.get("/api/pdf/TestCompanyUI/Prasad_Rane_Resume.pdf")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF-1.4"))

    def test_pdf_serve_not_found(self):
        """Test GET /api/pdf/{company}/{filename} returns 404 for missing file."""
        response = self.client.get("/api/pdf/NonExistentCompany999/Missing.pdf")
        self.assertEqual(response.status_code, 404)

    def test_generate_endpoint_validation(self):
        """Test POST /api/generate with missing/empty fields returns 422 or 400 validation error."""
        response = self.client.post("/api/generate", json={"company": ""})
        self.assertIn(response.status_code, [400, 422])

    def test_save_edit_endpoint(self):
        """Test POST /api/save-edit updates raw text and re-renders PDF."""
        self.test_output_dir.mkdir(parents=True, exist_ok=True)
        test_txt = self.test_output_dir / "Prasad_Rane_Resume.txt"
        test_txt.write_text("# Prasad Rane\n\n## Professional Summary\nInitial summary.", encoding="utf-8")

        response = self.client.post("/api/save-edit", json={
            "txt_url": "/api/files/TestCompanyUI/Prasad_Rane_Resume.txt",
            "content": "# Prasad Rane\n\n## Professional Summary\nUpdated summary line."
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("pdf_url", data)

        updated_content = test_txt.read_text(encoding="utf-8")
        self.assertIn("Updated summary line", updated_content)

        if test_txt.exists():
            test_txt.unlink()

    def test_query_endpoint_validation(self):
        """Test POST /api/query validation on empty query."""
        response = self.client.post("/api/query", json={"query": ""})
        self.assertIn(response.status_code, [400, 422])

    def test_query_endpoint_success(self):
        """Test POST /api/query invokes GraphRAG search engine correctly."""
        from unittest.mock import AsyncMock
        # Build a mock engine whose chat_stream yields a single SSE frame
        # followed by a done frame carrying the answer.
        async def fake_stream(query, mode, history):
            yield 'data: {"token": "Prasad used AWS Lambda and S3.", "done": false}\n'
            yield 'data: {"token": "", "done": true, "response": "Prasad used AWS Lambda and S3.", "sources": []}\n'
        mock_engine = MagicMock()
        mock_engine.chat_stream = fake_stream
        with patch("src.shared.api_routes.get_engine", return_value=mock_engine), \
             patch("src.shared.api_routes.get_conversation_store") as mock_store:
            mock_store.return_value.has_session.return_value = False
            response = self.client.post("/api/query", json={"query": "What AWS services did Prasad use?", "mode": "local"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["response"], "Prasad used AWS Lambda and S3.")

    def test_generate_stream_returns_sse(self):
        """Test POST /api/generate-stream returns correct content type."""
        from tests.conftest import VALID_JD_TEXT
        response = self.client.post("/api/generate-stream", json={"company": "TestCompany", "jd_text": VALID_JD_TEXT})
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/event-stream", response.headers.get("content-type", ""))

    def test_generate_stream_all_steps_emitted(self):
        """Test POST /api/generate-stream emits all expected progress steps in SSE format."""
        from tests.conftest import VALID_JD_TEXT
        # Use patch to ensure we avoid real LLM calls during web UI test
        with patch("src.generators.resume_generator._call_llm_safe", return_value="Mocked LLM content"):
            response = self.client.post("/api/generate-stream", json={"company": "TestCompany", "jd_text": VALID_JD_TEXT})
            self.assertEqual(response.status_code, 200)
            
            lines = [line.decode("utf-8") if hasattr(line, "decode") else line for line in response.iter_lines() if line]
            data_lines = [line for line in lines if line.startswith("data: ")]
            self.assertGreater(len(data_lines), 0)
            
            # Verify we get the expected step payloads
            import json
            steps_received = []
            for dl in data_lines:
                payload = json.loads(dl[6:])
                steps_received.append(payload.get("step"))
            
            expected_steps = [
                "extracting_keywords",
                "loading_master",
                "selecting_summary",
                "tailoring_summary",
                "tailoring_bullets",
                "formatting",
                "rendering_pdf",
                "complete"
            ]
            for step in expected_steps:
                self.assertIn(step, steps_received)

    def test_generate_stream_validation_error(self):
        """Test POST /api/generate-stream with empty company returns validation error."""
        response = self.client.post("/api/generate-stream", json={"company": "", "jd_text": "some jd"})
        self.assertIn(response.status_code, [400, 422])

    def test_chat_stream_returns_sse(self):
        """Test POST /api/chat-stream returns event stream."""
        with patch("src.gateway.call_serverless_llm", return_value="Mock LLM Answer"):
            response = self.client.post("/api/chat-stream", json={"query": "What AWS services did Prasad use?", "mode": "local"})
            self.assertEqual(response.status_code, 200)
            self.assertIn("text/event-stream", response.headers.get("content-type", ""))

            lines = [line.decode("utf-8") if hasattr(line, "decode") else line for line in response.iter_lines() if line]
            data_lines = [line for line in lines if line.startswith("data: ")]
            self.assertGreater(len(data_lines), 0)

    def test_chat_stream_validation(self):
        """Test POST /api/chat-stream validation on empty query."""
        response = self.client.post("/api/chat-stream", json={"query": "", "mode": "local"})
        self.assertIn(response.status_code, [400, 422])

if __name__ == "__main__":
    unittest.main()
