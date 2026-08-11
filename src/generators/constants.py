"""
constants.py — Generic constants for resume generation and PDF rendering.
"""

from typing import List

from reportlab.lib.units import inch

# Generic Candidate Defaults
DEFAULT_CANDIDATE_NAME = "Candidate Name"
DEFAULT_CANDIDATE_TITLE = "Software Engineer"

# Output Filenames
RAW_RESUME_FILENAME = "raw_resume.txt"
PDF_RESUME_FILENAME = "Prasad_Rane_Resume.pdf"

# Standard Resume Section Keys
SECTION_SUMMARY = "SUMMARY"
SECTION_EXPERIENCE = "EXPERIENCE"
SECTION_SKILLS = "SKILLS"
SECTION_CERTIFICATIONS = "CERTIFICATIONS"
SECTION_EDUCATION = "EDUCATION"
SECTION_SKIP = "SKIP"
SECTION_SKIP_SUMMARY_VARIANTS = "SKIP_SUMMARY_VARIANTS"

# Section Display Titles & Canonical Order
ORDERED_SECTIONS: List[str] = [
    SECTION_SUMMARY,
    SECTION_EXPERIENCE,
    SECTION_SKILLS,
    SECTION_CERTIFICATIONS,
    SECTION_EDUCATION,
]

# Section Markdown Prefixes
MARKDOWN_H1_PREFIX = "# "
MARKDOWN_H2_PREFIX = "## "
MARKDOWN_H3_PREFIX = "### "
MARKDOWN_H4_PREFIX = "#### "
MARKDOWN_BULLET_PREFIX = "- "

# Common Tech Keywords for ATS Fallback Matching
COMMON_ATS_KEYWORDS: List[str] = [
    "Python", "C#", ".NET", "Java", "JavaScript", "TypeScript", "Go", "Ruby", "Rust",
    "Angular", "React", "AWS", "Azure", "Docker", "Kubernetes", "GraphRAG", "Kafka",
    "Microservices", "REST", "GraphQL", "CI/CD", "Terraform", "DynamoDB", "SQL Server",
    "MySQL", "PostgreSQL", "Observability", "Dynatrace", "Splunk", "PagerDuty",
    "OAuth2", "JWT", "Copilot", "Bedrock", "LLM", "Prompt Engineering", "Billing",
    "Licensing", "Payments", "Subscriptions", "Agile", "Scrum", "TDD"
]

# PDF Page Layout
MARGIN_LEFT_RIGHT = 0.55 * inch
MARGIN_TOP_BOTTOM = 0.45 * inch
MAX_PAGES = 2

# ATS Bolding Constraints
BOLD_CAP_PCT = 20  # percent (use as BOLD_CAP_PCT / 100 for ratio)
MAX_BOLD_PHRASES_PER_BULLET = 3
