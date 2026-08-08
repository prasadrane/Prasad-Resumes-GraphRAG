"""
Unit tests for PDF renderer module.
"""

import tempfile
import unittest
from pathlib import Path
from src.generators.pdf_renderer import parse_raw_resume, render_pdf_resume

class TestPDFRenderer(unittest.TestCase):

    def test_parse_raw_resume_multi_job(self):
        raw_content = """# Prasad Rane
**Title:** Senior Software Engineer
**Contact:** Lake Bluff, IL | 513-967-9423 | emailprasadrane@gmail.com | linkedin.com/in/rane-prasad | prasadrane.vercel.app

## SUMMARY
Senior Software Engineer with 10 years experience in **Python** and **AWS**.

## EXPERIENCE
### Software Engineer | Rocket Mortgage | Lake Bluff, IL | Jan 2023 - Jul 2025
- Built **Python** backend microservices.

### Software Developer | London Computer Systems | Cincinnati, OH | Dec 2019 - Jan 2023
- Optimized **SQL Server** database queries.

## SKILLS
- **Backend & APIs:** Python, C#, AWS, Docker, Kubernetes

## CERTIFICATIONS
- **AWS Certified Cloud Practitioner** - Amazon Web Services | Issued: Apr 2026 | Expires: Apr 2029

## EDUCATION
- M.S. in Information Systems - University of Cincinnati (2019)
- B.E. in Electronics & Telecommunication - University of Pune (2013)
"""
        parsed = parse_raw_resume(raw_content)
        self.assertEqual(parsed["name"], "Prasad Rane")
        self.assertEqual(len(parsed["jobs"]), 2)
        self.assertEqual(parsed["jobs"][0]["company"], "Rocket Mortgage")
        self.assertEqual(parsed["jobs"][1]["company"], "London Computer Systems")
        self.assertEqual(parsed["jobs"][1]["location"], "Cincinnati, OH")

        # Verify education year stripping
        self.assertNotIn("2019", parsed["education"][0])
        self.assertNotIn("2013", parsed["education"][1])

    def test_render_pdf_resume_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            render_pdf_resume(Path("non_existent_raw_resume.txt"), Path("out.pdf"))

    def test_render_pdf_resume_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            raw_file = tmp_path / "raw_resume.txt"
            raw_file.write_text(
                "# Prasad Rane\n\n## SUMMARY\nExperienced in **Python**.\n\n## EXPERIENCE\n### Lead Engineer | Google | Remote | 2023 - Present\n- Led cloud teams.\n",
                encoding="utf-8",
            )

            pdf_file = tmp_path / "Prasad_Rane_Resume.pdf"
            result_file = render_pdf_resume(raw_file, pdf_file)

            self.assertTrue(result_file.exists())
            self.assertGreater(result_file.stat().st_size, 0)

if __name__ == "__main__":
    unittest.main()
