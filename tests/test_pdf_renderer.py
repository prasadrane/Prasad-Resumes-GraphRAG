"""
Unit tests for PDF renderer module.
"""

import tempfile
import unittest
from pathlib import Path
from src.generators.pdf_renderer import parse_raw_resume, render_pdf_resume

class TestPDFRenderer(unittest.TestCase):

    def test_parse_raw_resume_generic_candidate(self):
        raw_content = """# Alex Smith
**Title:** Principal Software Architect
**Contact:** San Francisco, CA | 415-555-0199 | alex@example.com | linkedin.com/in/alexsmith | alexsmith.dev

## SUMMARY
Principal Software Architect with 10 years experience in **Python** and **AWS**.

## EXPERIENCE
### Software Architect | TechCorp | San Francisco, CA | Jan 2021 - Present
- Built **Python** backend microservices.

### Senior Developer | CloudSystems | San Jose, CA | Dec 2018 - Dec 2020
- Optimized **PostgreSQL** database queries.

## SKILLS
- **Backend & APIs:** Python, Go, AWS, Docker, Kubernetes

## CERTIFICATIONS
- **AWS Solutions Architect Professional** - Amazon Web Services

## EDUCATION
- M.S. in Computer Science - Stanford University (2018)
"""
        parsed = parse_raw_resume(raw_content)
        self.assertEqual(parsed.name, "Alex Smith")
        self.assertEqual(parsed.title, "Principal Software Architect")
        self.assertEqual(parsed.contact_location, "San Francisco, CA")
        self.assertEqual(parsed.contact_email, "alex@example.com")
        self.assertEqual(len(parsed.jobs), 2)
        self.assertEqual(parsed.jobs[0].company, "TechCorp")
        self.assertEqual(parsed.jobs[1].company, "CloudSystems")
        self.assertEqual(parsed.jobs[1].location, "San Jose, CA")

        # Verify education year stripping
        self.assertNotIn("2018", parsed.education[0])

    def test_render_pdf_resume_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            render_pdf_resume(Path("non_existent_raw_resume.txt"), Path("out.pdf"))

    def test_render_pdf_resume_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            raw_file = tmp_path / "raw_resume.txt"
            raw_file.write_text(
                "# Alex Smith\n**Title:** Lead Engineer\n**Contact:** Remote | alex@example.com\n\n## SUMMARY\nExperienced in **Python**.\n\n## EXPERIENCE\n### Lead Engineer | Google | Remote | 2023 - Present\n- Led cloud teams.\n",
                encoding="utf-8",
            )

            pdf_file = tmp_path / "Prasad_Rane_Resume.pdf"
            result_file = render_pdf_resume(raw_file, pdf_file)

            self.assertTrue(result_file.exists())
            self.assertGreater(result_file.stat().st_size, 0)

if __name__ == "__main__":
    unittest.main()
