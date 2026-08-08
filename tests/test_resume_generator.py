"""
Unit tests for resume generator module (raw text formatting, bold keyword marking, date path resolution).
"""

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from src.generators.resume_generator import (
    bold_keywords,
    get_output_dir,
    generate_raw_resume,
)

class TestResumeGenerator(unittest.TestCase):

    def test_get_output_dir(self):
        date_str = datetime.now().strftime("%m-%d-%Y")
        out_dir = get_output_dir("Google")
        self.assertTrue(str(out_dir).endswith(f"{date_str}\\Google") or str(out_dir).endswith(f"{date_str}/Google"))

    def test_bold_keywords(self):
        text = "Experienced in Python and AWS cloud infrastructure."
        keywords = ["Python", "AWS"]
        bolded = bold_keywords(text, keywords)
        self.assertIn("**Python**", bolded)
        self.assertIn("**AWS**", bolded)

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
            self.assertIn("SUMMARY", content)
            self.assertIn("**Python**", content)

if __name__ == "__main__":
    unittest.main()
