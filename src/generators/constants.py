"""
constants.py — Centralized constants and magic strings for resume generation and PDF rendering.
"""

from typing import List

# Default Candidate Information
DEFAULT_CANDIDATE_NAME = "Prasad Rane"
DEFAULT_CANDIDATE_TITLE = "Senior Software Engineer"
DEFAULT_LOCATION = "Lake Bluff, IL"
DEFAULT_PHONE = "513-967-9423"
DEFAULT_EMAIL = "emailprasadrane@gmail.com"
DEFAULT_LINKEDIN_URL = "https://linkedin.com/in/rane-prasad"
DEFAULT_PORTFOLIO_URL = "https://prasadrane.vercel.app"
CREDLY_AWS_CERT_URL = "https://www.credly.com/badges/337a36b4-0285-460e-b115-2023040ba6b5"

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

# Default Education Lines (stripped of graduation years per rules)
DEFAULT_EDUCATION: List[str] = [
    "M.S. in Information Systems - University of Cincinnati",
    "B.E. in Electronics & Telecommunication - University of Pune",
]

# Default AWS Certification Line
DEFAULT_AWS_CERTIFICATE = "AWS Certified Cloud Practitioner - Amazon Web Services | Issued: Apr 2026 | Expires: Apr 2029"

# Common Tech Keywords for ATS Fallback Matching
COMMON_ATS_KEYWORDS: List[str] = [
    "Python", "C#", ".NET", "Java", "JavaScript", "TypeScript", "Go", "Ruby", "Rust",
    "Angular", "React", "AWS", "Azure", "Docker", "Kubernetes", "GraphRAG", "Kafka",
    "Microservices", "REST", "GraphQL", "CI/CD", "Terraform", "DynamoDB", "SQL Server",
    "MySQL", "PostgreSQL", "Observability", "Dynatrace", "Splunk", "PagerDuty",
    "OAuth2", "JWT", "Copilot", "Bedrock", "LLM", "Prompt Engineering", "Billing",
    "Licensing", "Payments", "Subscriptions", "Agile", "Scrum", "TDD"
]
