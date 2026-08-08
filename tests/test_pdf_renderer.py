"""
Unit tests for PDF renderer module.
"""

import tempfile
import unittest
from pathlib import Path
from src.generators.pdf_renderer import parse_raw_resume, render_pdf_resume

class TestPDFRenderer(unittest.TestCase):

    def test_parse_raw_resume(self):
        raw_content = """# Prasad Rane
**Title:** Senior Software Engineer
**Contact:** prasad@example.com | 123-456-7890

## SUMMARY
Experienced in **Python**, **AWS**, and **GraphRAG**.

## SKILLS
Python, C#, AWS, Docker, Kubernetes
"""
        parsed = parse_raw_resume(raw_content)
        self.assertEqual(parsed["name"], "Prasad Rane")
        self.assertEqual(parsed["title"], "Senior Software Engineer")
        self.assertIn("SUMMARY", parsed["sections"])
        self.assertIn("SKILLS", parsed["sections"])

    def test_render_pdf_resume(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            raw_file = tmp_path / "raw_resume.txt"
            raw_file.write_text("# Prasad Rane\n**Title:** Lead Engineer\n\n## SUMMARY\nExperienced in **Python**.", encoding="utf-8")

            pdf_file = tmp_path / "Prasad_Rane_Resume.pdf"
            result_file = render_pdf_resume(raw_file, pdf_file)

            self.assertTrue(result_file.exists())
            self.assertGreater(result_file.stat().st_size, 0)

if __name__ == "__main__":
    unittest.main()
