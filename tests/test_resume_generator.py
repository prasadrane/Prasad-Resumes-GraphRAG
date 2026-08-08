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
    reorder_skills_by_relevance,
    select_tailored_summary,
)

class TestResumeGenerator(unittest.TestCase):

    def test_get_output_dir(self):
        date_str = datetime.now().strftime("%m-%d-%Y")
        out_dir = get_output_dir("Google")
        self.assertTrue(str(out_dir).endswith(f"{date_str}\\Google") or str(out_dir).endswith(f"{date_str}/Google"))

    def test_get_output_dir_readonly(self):
        date_str = datetime.now().strftime("%m-%d-%Y")
        mock_read_only = Path("/non_existent_readonly_dir_12345/output")
        out_dir = get_output_dir("CrowdStrike", base_output_dir=mock_read_only)
        self.assertTrue(out_dir.exists())
        self.assertIn("CrowdStrike", str(out_dir))

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

    def test_title_line_excluded_from_markdown(self):
        data = ResumeData(
            name="Alex Smith",
            title="Senior Staff Engineer",
            contact_location="Austin, TX",
            contact_phone="512-555-0100",
            contact_email="alex@example.com",
            summary="Senior Staff Engineer specializing in Go and Kubernetes.",
            jobs=[JobEntry(heading="Staff Engineer | Global Systems | Austin, TX | 2021 - Present", bullets=["Led Go microservices."])],
            skills=["Backend: Go, Python, C#"],
            certifications=["Certified Kubernetes Administrator"],
            education=["B.S. in Computer Science - UT Austin"]
        )
        keywords = ["Go", "Kubernetes"]
        md_text = format_tailored_markdown(data, keywords)

        self.assertIn("# Alex Smith", md_text)
        self.assertNotIn("**Title:**", md_text) # Title line MUST be excluded!
        self.assertIn(f"## {SECTION_SUMMARY}", md_text)
        self.assertIn(f"## {SECTION_EXPERIENCE}", md_text)
        self.assertIn(f"## {SECTION_SKILLS}", md_text)

    def test_select_tailored_summary(self):
        sample_master = """# PRASAD RANE — MASTER RESUME
## 🎯 Executive & Specialized Professional Summaries
### Canonical Summary
Software Engineer with 10+ years experience.

### Domain-Specific Summary Variants
- **AI / LLM-Forward**: Software Engineer with 10 years experience building Amazon Bedrock Claude Sonnet chatbots.
- **Cloud & Reliability-Forward**: Software Engineer with 10 years experience on AWS ECS Fargate and Terraform.
"""
        # AI Keywords
        ai_sum = select_tailored_summary(sample_master, ["Bedrock", "Claude", "LLM"], "Anthropic")
        self.assertIn("Amazon Bedrock", ai_sum)

        # Cloud Keywords
        cloud_sum = select_tailored_summary(sample_master, ["Fargate", "Terraform", "AWS"], "AWS")
        self.assertIn("Fargate", cloud_sum)

    def test_reorder_skills_by_relevance(self):
        skills = [
            "Backend & APIs: C#, .NET, Python",
            "Cloud & Infrastructure: AWS, Fargate, Terraform",
            "AI / LLM Integration: Bedrock, Claude, GraphRAG"
        ]
        keywords = ["Bedrock", "Claude"]
        reordered = reorder_skills_by_relevance(skills, keywords)
        self.assertTrue(reordered[0].startswith("AI / LLM")) # AI skill moved to top!

    def test_generate_raw_resume(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            jd_text = "Senior Software Engineer skilled in Python, AWS ECS Fargate, and Bedrock."
            out_file = generate_raw_resume(
                company_name="CrowdStrike",
                jd_text=jd_text,
                base_output_dir=Path(tmp_dir),
            )
            self.assertTrue(out_file.exists())
            content = out_file.read_text(encoding="utf-8")
            self.assertNotIn("**Title:**", content)
            self.assertIn("## SUMMARY", content)
            self.assertIn("## EXPERIENCE", content)

if __name__ == "__main__":
    unittest.main()
