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
        self.assertTrue("text/html" in response.headers.get("content-type", "") or "<!DOCTYPE html>" in response.text or "status" in response.text)

    def test_default_resume_endpoint_vercel(self):
        response = self.client.get("/api/default-resume")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("raw_resume", data)
        self.assertIn("pdf_url", data)
        self.assertTrue(data["pdf_url"].startswith("data:application/pdf;base64,"))

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
        self.assertIn("pdf_url", data)
        self.assertTrue(data["pdf_url"].startswith("data:application/pdf;base64,"))

    def test_query_endpoint_distinct_responses(self):
        res_comp = self.client.post("/api/query", json={"query": "Which companies has Prasad worked for?", "mode": "local"})
        self.assertEqual(res_comp.status_code, 200)
        text_comp = res_comp.json()["response"]
        self.assertIn("Rocket Mortgage", text_comp)

        res_aws = self.client.post("/api/query", json={"query": "What AWS technologies did Prasad use?", "mode": "local"})
        self.assertEqual(res_aws.status_code, 200)
        text_aws = res_aws.json()["response"]
        self.assertIn("AWS", text_aws)
        self.assertIn("Bedrock", text_aws)

        self.assertNotEqual(text_comp, text_aws)

if __name__ == "__main__":
    unittest.main()
