"""
Unit tests for Vercel serverless FastAPI endpoints.
"""

import unittest
from fastapi.testclient import TestClient
from api.index import app

class TestVercelAPI(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def test_read_root(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("status", response.json())
        self.assertEqual(response.json()["status"], "ok")

    def test_get_keywords(self):
        payload = {
            "company": "Amazon",
            "jd_text": "Looking for AWS, Python, Docker, Microservices engineer."
        }
        response = self.client.post("/api/keywords", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("keywords", data)
        self.assertIn("AWS", data["keywords"])
        self.assertIn("Python", data["keywords"])

    def test_generate_resume_endpoint(self):
        payload = {
            "company": "TestCorp",
            "jd_text": "Backend engineer with Python, AWS, PostgreSQL experience."
        }
        response = self.client.post("/api/generate", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("raw_resume", data)

if __name__ == "__main__":
    unittest.main()
