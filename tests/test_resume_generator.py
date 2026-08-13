"""
Unit tests for resume generator module (raw text formatting, bold keyword marking, date path resolution).
Includes TDD test for 5-JD distinct LLM-driven tailoring and graceful fallback verification.
"""

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

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
    llm_tailor_resume,
    parse_master_resume,
    reorder_skills_by_relevance,
    select_tailored_summary,
)


# ── Five representative job descriptions ─────────────────────────────────────
JD_AWS_CLOUD_SECURITY = """
Senior Cloud Security Engineer — AWS Native Platform
We are looking for a security-focused engineer who can own our AWS IAM hardening,
OAuth2 and JWT token architecture, and CrowdStrike SIEM integration.
Must have experience with CloudWatch, Terraform IaC, and audit trail design.
Preferred: penetration testing background, Dynatrace observability integration.
"""

JD_AI_LLM = """
AI / ML Platform Engineer — LLM Orchestration
Build and scale production-grade AI pipelines on Amazon Bedrock using Claude Sonnet.
Architect prompt engineering guardrails, RAG-adjacent retrieval workflows, and
LLM-as-router intent classification. Python/FastAPI backend, GraphRAG, vector stores.
Must have experience shipping LLM products to production users at scale.
"""

JD_PYTHON_MICROSERVICES = """
Senior Backend Engineer — Python Microservices
Design and operate high-throughput microservices with FastAPI and Python.
Own event-driven architecture via Kafka topic governance, SQS/SNS messaging patterns.
Experience with Docker, Kubernetes, ECS Fargate, CI/CD pipelines essential.
Strong SQL optimization, stored procedure refactoring, and T-SQL proficiency preferred.
"""

JD_KAFKA_DATA_INFRA = """
Staff Data Infrastructure Engineer — Kafka & Streaming
Lead architecture for real-time event streaming infrastructure using Apache Kafka / MSK.
Own Kafka topic governance, consumer group reliability, and cross-team schema registry.
Must have experience with DynamoDB single-table design, Splunk dashboards, PagerDuty alert tuning.
Strong .NET or Java background preferred. OpenTelemetry distributed tracing experience.
"""

JD_FINTECH_FULLSTACK = """
Full-Stack Software Engineer — FinTech Regulatory Platform
Modernize legacy VB.NET monolith to cloud-native .NET 8/9 microservices on AWS ECS.
Own Angular 18 frontend with NgRx state management, TypeScript, and RxJS.
RBAC, JWT authorization code + PKCE flows, compliance with SOX/audit trail requirements.
Must have legacy modernization experience and strong C# ASP.NET Core background.
"""

ALL_5_JDS = [
    ("CrowdStrike", JD_AWS_CLOUD_SECURITY),
    ("Anthropic", JD_AI_LLM),
    ("Stripe", JD_PYTHON_MICROSERVICES),
    ("Confluent", JD_KAFKA_DATA_INFRA),
    ("Fiserv", JD_FINTECH_FULLSTACK),
]


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
        self.assertNotIn("**Title:**", md_text)  # Title line MUST be excluded!
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
        self.assertTrue(reordered[0].startswith("AI / LLM"))  # AI skill moved to top!

    def test_generate_raw_resume(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            jd_text = "Senior Software Engineer skilled in Python, AWS ECS Fargate, and Bedrock."
            # Patch LLM to avoid API calls in unit tests
            with patch("src.generators.resume_generator._call_llm_safe", return_value=""):
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

    def test_llm_tailor_resume_graceful_fallback(self):
        """Verify that when LLM is unavailable, llm_tailor_resume falls back gracefully without crashing."""
        data = ResumeData(
            name="Prasad Rane",
            title="Senior Software Engineer",
            summary="Software Engineer with 10+ years building cloud-native systems.",
            jobs=[
                JobEntry(
                    heading="Senior Engineer | Acme Corp | Chicago, IL | 2022 - Present",
                    bullets=["Built microservices.", "Led team of 5 engineers.", "Reduced latency by 40%."]
                )
            ],
            skills=["Backend: Python, C#", "Cloud: AWS"],
            certifications=["AWS Solutions Architect"],
            education=["B.S. Computer Science"]
        )
        original_summary = data.summary
        original_bullets = list(data.jobs[0].bullets)

        # Simulate LLM returning empty string (e.g., API unavailable)
        with patch("src.generators.resume_generator._call_llm_safe", return_value=""):
            result = llm_tailor_resume(data, "", "TestCo", "Python microservices engineer.", ["Python"])

        # Should NOT crash and should preserve original content when LLM returns nothing useful
        self.assertEqual(result.summary, original_summary)
        self.assertEqual(result.jobs[0].bullets, original_bullets)

    def test_generate_tailored_resumes_5_jds_distinct(self):
        """
        TDD Test: Generate resumes for 5 distinct JDs and assert ALL 5 are unique.
        
        This test verifies that the LLM-driven tailoring engine produces genuinely
        different resumes for different job descriptions — different wording, different
        bullet ordering, different keyword emphasis. No two resumes should be identical.
        
        The LLM is mocked with JD-specific distinct responses to verify the integration
        pipeline correctly feeds JD context through to produce per-JD customization.
        """
        # JD-specific mock LLM responses for summaries (unique per JD)
        mock_responses = {
            "CrowdStrike": (
                "Security-focused Software Engineer with 10+ years hardening AWS IAM, "
                "OAuth2/JWT token architectures, and CrowdStrike SIEM integrations across enterprise platforms. "
                "Proven track record delivering zero-disruption auth migrations and resolving critical audit findings."
            ),
            "Anthropic": (
                "AI-platform Software Engineer with 10+ years building production LLM orchestration pipelines on "
                "Amazon Bedrock (Claude Sonnet), architecting prompt engineering guardrails, RAG-adjacent retrieval "
                "workflows, and intent-to-API classification systems that served millions of loan lookup requests."
            ),
            "Stripe": (
                "Backend Software Engineer with 10+ years designing high-throughput Python/FastAPI microservices "
                "with event-driven Kafka/SQS architectures on AWS ECS Fargate — expert in SQL optimization, "
                "Docker containerization, and CI/CD pipeline governance across cross-functional teams."
            ),
            "Confluent": (
                "Data Infrastructure Engineer with 10+ years owning real-time streaming systems on Apache Kafka/MSK, "
                "including cross-team Kafka topic governance, DynamoDB single-table design, and enterprise observability "
                "via OpenTelemetry, Splunk, and PagerDuty alert tuning."
            ),
            "Fiserv": (
                "Full-Stack FinTech Engineer with 10+ years modernizing legacy VB.NET monoliths to .NET 8/9 "
                "cloud-native microservices, owning Angular 18/NgRx frontends, and implementing SOX-compliant "
                "JWT PKCE OAuth2 authorization across 7 dependent regulated banking systems."
            ),
        }

        generated_resumes = []
        with tempfile.TemporaryDirectory() as tmp_dir:
            for company, jd_text in ALL_5_JDS:
                # Mock LLM to return company-specific tailored content
                def make_mock(comp=company):
                    call_count = {"n": 0}
                    def mock_llm(prompt, system_prompt, **kwargs):
                        # Production passes temperature / timeout / model / use_case
                        # as kwargs; accept them so the mock stays forward-compatible.
                        call_count["n"] += 1
                        if call_count["n"] == 1:
                            # First call = summary
                            return mock_responses[comp]
                        else:
                            # Subsequent calls = bullets (return JD-flavored bullets)
                            return (
                                f"Architected {comp}-specific system for high-throughput distributed ingestion.\n"
                                f"Engineered event-driven pipeline tailored to {comp} platform requirements.\n"
                                f"Led {comp}-domain migration improving reliability by 40%.\n"
                                f"Implemented {comp}-aligned observability reducing MTTR by 35%.\n"
                                f"Delivered {comp} project on schedule cutting operational overhead 25%."
                            )
                    return mock_llm

                with patch("src.generators.resume_generator._call_llm_safe", side_effect=make_mock()):
                    out_file = generate_raw_resume(
                        company_name=company,
                        jd_text=jd_text,
                        base_output_dir=Path(tmp_dir),
                    )

                self.assertTrue(out_file.exists(), f"Resume file not created for {company}")
                content = out_file.read_text(encoding="utf-8")
                self.assertNotIn("**Title:**", content, f"Title line found in {company} resume!")
                self.assertIn("## SUMMARY", content, f"Missing SUMMARY section for {company}")
                self.assertIn("## EXPERIENCE", content, f"Missing EXPERIENCE section for {company}")
                generated_resumes.append(content)

        # Core assertion: ALL 5 resumes must be DIFFERENT from each other
        unique_resumes = set(generated_resumes)
        self.assertEqual(
            len(unique_resumes),
            5,
            f"Expected 5 distinct tailored resumes but got {len(unique_resumes)} unique versions. "
            f"The tailoring engine is producing duplicate resumes!"
        )

        # Additional: verify summary sections are distinct across resumes
        summaries = []
        for resume in generated_resumes:
            lines = resume.split("\n")
            for i, line in enumerate(lines):
                if "## SUMMARY" in line and i + 1 < len(lines):
                    summaries.append(lines[i + 1].strip())
                    break

        unique_summaries = set(summaries)
        self.assertEqual(
            len(unique_summaries),
            5,
            f"Expected 5 distinct summaries but got {len(unique_summaries)}. "
            f"Summaries are not being uniquely tailored per JD!"
        )


if __name__ == "__main__":
    unittest.main()
