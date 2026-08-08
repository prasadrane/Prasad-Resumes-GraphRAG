"""
test_web_ui.py — Integration and Unit Tests for Web UI FastAPI Backend.
"""

import unittest
from unittest.mock import patch
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

    def test_history_endpoint(self):
        """Test GET /api/history returns valid resume history entries."""
        response = self.client.get("/api/history")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        # Check if TestCompanyUI exists in history
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
        # Create mock TXT file
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

        # Verify TXT file updated
        updated_content = test_txt.read_text(encoding="utf-8")
        self.assertIn("Updated summary line", updated_content)

        # Cleanup TXT file
        if test_txt.exists():
            test_txt.unlink()


    def test_query_endpoint_validation(self):
        """Test POST /api/query validation on empty query."""
        response = self.client.post("/api/query", json={"query": ""})
        self.assertIn(response.status_code, [400, 422])

    @patch("src.web.app.execute_graphrag_query")
    def test_query_endpoint_success(self, mock_query):
        """Test POST /api/query invokes GraphRAG search engine correctly."""
        mock_query.return_value = "Prasad used AWS Lambda and S3."
        response = self.client.post("/api/query", json={"query": "What AWS services did Prasad use?", "mode": "local"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["response"], "Prasad used AWS Lambda and S3.")
        mock_query.assert_called_once_with(query="What AWS services did Prasad use?", mode="local", root_dir=ROOT_DIR)


if __name__ == "__main__":
    unittest.main()


