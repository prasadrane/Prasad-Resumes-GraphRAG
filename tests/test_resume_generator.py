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
        # Em-dash in bullet prose replaced with period
        bullet = "Reduced false positive alerts — improving on-call responsiveness."
        cleaned = clean_em_dashes(bullet)
        self.assertIn("alerts. improving", cleaned)
        self.assertNotIn("—", cleaned)

        # Date range hyphens preserved
        dates = "Jan 2023 - Jul 2025"
        self.assertEqual(clean_em_dashes(dates), "Jan 2023 - Jul 2025")

    def test_bold_keywords_limit_and_percentage_cap(self):
        bullet = "Architected high-throughput microservices using Python, AWS, Docker, Kubernetes, and GraphRAG to optimize performance and reduce latency."
        keywords = ["Python", "AWS", "Docker", "Kubernetes", "GraphRAG"]
        bolded = bold_keywords(bullet, keywords, max_bold_phrases=3, max_bold_ratio=0.25)

        bold_count = bolded.count("**") // 2
        self.assertLessEqual(bold_count, 3)
        self.assertIn("**Python**", bolded)

    def test_parse_master_resume(self):
        sample_master = """# PRASAD RANE — MASTER RESUME
## 🎯 Executive & Specialized Professional Summaries
### Canonical Summary
Senior Software Engineer with 10+ years of experience architecting cloud systems.

## 💼 Exhaustive Experience & Bullet Library
### Software Engineer | Rocket Mortgage | Lake Bluff, IL | Jan 2023 - Jul 2025
#### Story 1 — Observability
- Diagnosed monitoring gap on Fannie Mae integration.

## 🛠️ Complete Technical Skills Inventory
- **Backend & APIs**: C#, .NET Core, Python, AWS

## 🏆 Certifications
- **AWS Certified Cloud Practitioner** - Amazon Web Services | Issued: Apr 2026 | Expires: Apr 2029

## 🎓 Education
- **M.S. in Information Systems** - University of Cincinnati (2019)
"""
        parsed: ResumeData = parse_master_resume(sample_master)
        self.assertEqual(parsed.name, "Prasad Rane")
        self.assertIn("10+ years", parsed.summary)
        self.assertEqual(len(parsed.jobs), 1)
        self.assertIn("Rocket Mortgage", parsed.jobs[0].heading)
        self.assertEqual(len(parsed.skills), 1)
        self.assertEqual(len(parsed.certifications), 1)
        self.assertNotIn("2019", parsed.education[0])

    def test_format_tailored_markdown(self):
        data = ResumeData(
            summary="Senior Engineer specializing in Python and AWS.",
            jobs=[JobEntry(heading="Software Engineer | Google | Remote | 2023 - Present", bullets=["Led Python microservices."])],
            skills=["Backend: Python, C#"],
            certifications=["AWS Certified Cloud Practitioner"],
            education=["M.S. in Information Systems - University of Cincinnati"]
        )
        keywords = ["Python", "AWS"]
        md_text = format_tailored_markdown(data, keywords)

        self.assertIn(f"## {SECTION_SUMMARY}", md_text)
        self.assertIn(f"## {SECTION_EXPERIENCE}", md_text)
        self.assertIn(f"## {SECTION_SKILLS}", md_text)
        self.assertIn(f"## {SECTION_CERTIFICATIONS}", md_text)
        self.assertIn(f"## {SECTION_EDUCATION}", md_text)
        self.assertIn("**Python**", md_text)

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

if __name__ == "__main__":
    unittest.main()
