"""
Unit tests for jd_extractor.py — URL job description extraction and HTML cleaning.
"""

import unittest
from unittest.mock import patch, MagicMock
from src.converters.jd_extractor import extract_jd_from_url, clean_html_to_text


class TestJDExtractor(unittest.TestCase):

    def test_clean_html_to_text_removes_tags_and_scripts(self):
        html = """
        <html>
            <head><title>Senior Engineer at Stripe</title><script>var x = 1;</script></head>
            <body>
                <header><nav>Home | Jobs | Contact</nav></header>
                <main>
                    <h1>Senior Backend Engineer</h1>
                    <p>We are looking for a Python and AWS engineer to join our payments platform.</p>
                    <ul>
                        <li>Experience with distributed systems and Kafka</li>
                        <li>5+ years backend development in Python or Go</li>
                    </ul>
                </main>
                <footer>&copy; 2026 Stripe. All rights reserved.</footer>
            </body>
        </html>
        """
        cleaned = clean_html_to_text(html)
        self.assertIn("Senior Backend Engineer", cleaned)
        self.assertIn("Python and AWS engineer", cleaned)
        self.assertIn("distributed systems and Kafka", cleaned)
        self.assertNotIn("var x = 1", cleaned)
        self.assertNotIn("<script>", cleaned)
        self.assertNotIn("<header>", cleaned)

    @patch("urllib.request.urlopen")
    def test_extract_jd_from_url_success(self, mock_urlopen):
        mock_response = MagicMock()
        mock_html = """
        <html>
            <head>
                <title>Senior Cloud Engineer - Stripe Careers</title>
                <meta property="og:site_name" content="Stripe">
            </head>
            <body>
                <div class="job-description">
                    <h1>Senior Cloud Engineer</h1>
                    <p>Stripe is hiring a Senior Cloud Engineer to scale AWS infrastructure and Kubernetes clusters.</p>
                    <p>Requirements include Python, Terraform, Docker, and CI/CD pipelines.</p>
                </div>
            </body>
        </html>
        """
        mock_response.read.return_value = mock_html.encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        result = extract_jd_from_url("https://stripe.com/jobs/senior-cloud-engineer")
        self.assertEqual(result["company"], "Stripe")
        self.assertEqual(result["title"], "Senior Cloud Engineer")
        self.assertIn("AWS infrastructure and Kubernetes", result["jd_text"])
        self.assertIn("Python, Terraform, Docker", result["jd_text"])

    def test_invalid_url_raises_value_error(self):
        with self.assertRaises(ValueError):
            extract_jd_from_url("not-a-valid-url")


if __name__ == "__main__":
    unittest.main()
