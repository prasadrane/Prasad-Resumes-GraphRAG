"""
Unit tests for resume generator module (raw text formatting, bold keyword marking, date path resolution).
"""

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from src.generators.constants import (
    SECTION_CERTIFICATIONS,
    SECTION_EDUCATION,
    SECTION_EXPERIENCE,
    SECTION_SKILLS,
    SECTION_SUMMARY,
)
from src.generators.models import JobEntry, ResumeData
from src.generators.resume_generator import (
    bold_keywords,
    clean_em_dashes,
    format_tailored_markdown,
    generate_raw_resume,
    get_output_dir,
    parse_master_resume,
)

class TestResumeGenerator(unittest.TestCase):

    def test_get_output_dir(self):
        date_str = datetime.now().strftime("%m-%d-%Y")
        out_dir = get_output_dir("Google")
        self.assertTrue(str(out_dir).endswith(f"{date_str}\\Google") or str(out_dir).endswith(f"{date_str}/Google"))

    def test_clean_em_dashes(self):
        bullet = "Reduced false positive alerts — improving on-call responsiveness."
        cleaned = clean_em_dashes(bullet)
        self.assertIn("alerts. improving", cleaned)
        self.assertNotIn("—", cleaned)

        dates = "Jan 2023 - Jul 2025"
        self.assertEqual(clean_em_dashes(dates), "Jan 2023 - Jul 2025")

    def test_bold_keywords_limit_and_percentage_cap(self):
        bullet = "Architected high-throughput microservices using Python, AWS, Docker, Kubernetes, and GraphRAG to optimize performance and reduce latency."
        keywords = ["Python", "AWS", "Docker", "Kubernetes", "GraphRAG"]
        bolded = bold_keywords(bullet, keywords, max_bold_phrases=3, max_bold_ratio=0.25)

        bold_count = bolded.count("**") // 2
        self.assertLessEqual(bold_count, 3)
        self.assertIn("**Python**", bolded)

    def test_parse_master_resume_generic_candidate(self):
        sample_master = """# JANE DOE — MASTER RESUME
**Title:** Principal Cloud Architect
**Contact:** Seattle, WA | 206-555-0199 | jane@example.com | linkedin.com/in/janedoe | janedoe.dev

## 🎯 Executive & Specialized Professional Summaries
### Canonical Summary
Principal Cloud Architect with 12+ years experience building distributed systems.

## 💼 Exhaustive Experience & Bullet Library
### Lead Architect | TechCorp | Seattle, WA | Jan 2022 - Present
#### Story 1 — Cloud Modernization
- Led cloud migration to AWS and Kubernetes.

## 🛠️ Complete Technical Skills Inventory
- **Cloud & Infrastructure**: AWS, Kubernetes, Terraform

## 🏆 Certifications
- **AWS Solutions Architect Professional** - Amazon Web Services

## 🎓 Education
- **M.S. in Computer Science** - University of Washington (2018)
"""
        parsed: ResumeData = parse_master_resume(sample_master)
        self.assertEqual(parsed.name, "JANE DOE")
        self.assertEqual(parsed.title, "Principal Cloud Architect")
        self.assertIn("12+ years", parsed.summary)
        self.assertEqual(len(parsed.jobs), 1)
        self.assertEqual(parsed.jobs[0].heading, "Lead Architect | TechCorp | Seattle, WA | Jan 2022 - Present")
        self.assertEqual(len(parsed.skills), 1)
        self.assertEqual(len(parsed.certifications), 1)
        self.assertNotIn("2018", parsed.education[0])

    def test_format_tailored_markdown_generic(self):
        data = ResumeData(
            name="Alex Smith",
            title="Senior Staff Engineer",
            contact_location="Austin, TX",
            contact_phone="512-555-0100",
            contact_email="alex@example.com",
            contact_linkedin="linkedin.com/in/alexsmith",
            contact_portfolio="alexsmith.dev",
            summary="Senior Staff Engineer specializing in Go and Kubernetes.",
            jobs=[JobEntry(heading="Staff Engineer | Global Systems | Austin, TX | 2021 - Present", bullets=["Led Go microservices."])],
            skills=["Backend: Go, Python, C#"],
            certifications=["Certified Kubernetes Administrator"],
            education=["B.S. in Computer Science - UT Austin"]
        )
        keywords = ["Go", "Kubernetes"]
        md_text = format_tailored_markdown(data, keywords)

        self.assertIn("# Alex Smith", md_text)
        self.assertIn("**Title:** Senior Staff Engineer", md_text)
        self.assertIn(f"## {SECTION_SUMMARY}", md_text)
        self.assertIn(f"## {SECTION_EXPERIENCE}", md_text)
        self.assertIn(f"## {SECTION_SKILLS}", md_text)
        self.assertIn(f"## {SECTION_CERTIFICATIONS}", md_text)
        self.assertIn(f"## {SECTION_EDUCATION}", md_text)
        self.assertIn("**Go**", md_text)

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
            self.assertIn("## SUMMARY", content)
            self.assertIn("## EXPERIENCE", content)
            self.assertIn("## SKILLS", content)
            self.assertIn("## CERTIFICATIONS", content)
            self.assertIn("## EDUCATION", content)

if __name__ == "__main__":
    unittest.main()
