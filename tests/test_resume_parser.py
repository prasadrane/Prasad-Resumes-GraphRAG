"""
Unit tests for the extracted resume_parser module and the broken
resume_generator <-> pdf_renderer import cycle.
"""

import inspect
import unittest

from src.generators.resume_parser import (
    clean_em_dashes,
    extract_summary_variants,
    parse_resume_markdown,
)
from src.generators import resume_generator

SAMPLE = """# PRASAD RANE — MASTER RESUME
**Contact:** Chicago, IL | 555-0100 | prasad@example.com | [LinkedIn](https://linkedin.com/in/prasad)

## SUMMARY
### Canonical Summary
Software Engineer with 10+ years experience.

## EXPERIENCE
### Senior Software Engineer | Rocket Mortgage | Chicago, IL | Jan 2020 - Present
- Built microservices reducing latency by 40%.

## SKILLS
- Backend: Python, C#
"""


class TestResumeParser(unittest.TestCase):

    def test_parse_fields(self):
        data = parse_resume_markdown(SAMPLE)
        self.assertEqual(data.name, "PRASAD RANE")
        self.assertEqual(data.contact_location, "Chicago, IL")
        self.assertEqual(data.contact_phone, "555-0100")
        self.assertEqual(data.contact_email, "prasad@example.com")
        self.assertEqual(data.contact_linkedin, "https://linkedin.com/in/prasad")
        self.assertEqual(len(data.jobs), 1)
        self.assertEqual(data.jobs[0].company, "Rocket Mortgage")
        self.assertEqual(data.jobs[0].bullets, ["Built microservices reducing latency by 40%."])
        self.assertIn("Backend: Python, C#", data.skills)

    def test_extract_summary_variants(self):
        variants = extract_summary_variants(SAMPLE)
        self.assertIn("Canonical", variants)
        self.assertIn("Software Engineer with 10+ years experience.", variants["Canonical"])

    def test_clean_em_dashes_via_parser(self):
        self.assertNotIn("—", clean_em_dashes("Reduced alerts — improved response."))

    def test_resume_generator_reexports_are_identical(self):
        self.assertIs(resume_generator.parse_resume_markdown, parse_resume_markdown)
        self.assertIs(resume_generator.parse_master_resume, parse_resume_markdown)
        self.assertIs(resume_generator.clean_em_dashes, clean_em_dashes)

    def test_pdf_renderer_does_not_import_resume_generator(self):
        import src.generators.pdf_renderer as pr
        source = inspect.getsource(pr)
        self.assertNotIn("from .resume_generator import", source)
        self.assertIn("from .resume_parser import parse_resume_markdown", source)

    def test_pdf_renderer_alias_still_exported(self):
        from src.generators.pdf_renderer import parse_raw_resume
        self.assertIs(parse_raw_resume, parse_resume_markdown)


if __name__ == "__main__":
    unittest.main()
