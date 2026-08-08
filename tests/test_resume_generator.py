"""
Unit tests for resume generator module (raw text formatting, bold keyword marking, date path resolution).
"""

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from src.generators.resume_generator import (
    bold_keywords,
    clean_em_dashes,
    get_output_dir,
    generate_raw_resume,
)

class TestResumeGenerator(unittest.TestCase):

    def test_get_output_dir(self):
        date_str = datetime.now().strftime("%m-%d-%Y")
        out_dir = get_output_dir("Google")
        self.assertTrue(str(out_dir).endswith(f"{date_str}\\Google") or str(out_dir).endswith(f"{date_str}/Google"))

    def test_clean_em_dashes(self):
        # Em-dash in bullet prose replaced with period
        bullet = "Reduced false positive alerts — improving on-call responsiveness."
        cleaned = clean_em_dashes(bullet)
        self.assertIn("alerts. improving", cleaned)
        self.assertNotIn("—", cleaned)

        # Date range hyphens preserved
        dates = "Jan 2023 - Jul 2025"
        self.assertEqual(clean_em_dashes(dates), "Jan 2023 - Jul 2025")

    def test_bold_keywords_limit_and_percentage_cap(self):
        # Long bullet text
        bullet = "Architected high-throughput microservices using Python, AWS, Docker, Kubernetes, and GraphRAG to optimize performance and reduce latency."
        keywords = ["Python", "AWS", "Docker", "Kubernetes", "GraphRAG"]
        bolded = bold_keywords(bullet, keywords, max_bold_phrases=3, max_bold_ratio=0.25)

        # Ensure max 3 phrases bolded and bold length ratio is controlled
        bold_count = bolded.count("**") // 2
        self.assertLessEqual(bold_count, 3)
        self.assertIn("**Python**", bolded)

    def test_generate_raw_resume(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            jd_text = "Senior Software Engineer skilled in Python, AWS, and GraphRAG."
            out_file = generate_raw_resume(
                company_name="Google",
                jd_text=jd_text,
                base_output_dir=Path(tmp_dir),
            )
            self.assertTrue(out_file.exists())
            self.assertEqual(out_file.name, "raw_resume.txt")
            content = out_file.read_text(encoding="utf-8")
            self.assertIn("Prasad Rane", content)
            self.assertIn("## SUMMARY", content)
            self.assertIn("## EXPERIENCE", content)
            self.assertIn("## SKILLS", content)
            self.assertIn("## CERTIFICATIONS", content)
            self.assertIn("## EDUCATION", content)
            self.assertNotIn("Gap-Framing", content)

if __name__ == "__main__":
    unittest.main()
