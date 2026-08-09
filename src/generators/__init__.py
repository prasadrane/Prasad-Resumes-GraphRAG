"""
generators package — ATS keyword analysis, raw resume generation, and PDF rendering.
"""

from .ats_matcher import extract_ats_keywords, match_graphrag_stories
from .resume_generator import generate_raw_resume, bold_keywords, get_output_dir, generate_raw_resume_stepwise
from .pdf_renderer import render_pdf_resume, parse_raw_resume
from .pdf_styles import get_resume_styles, format_contact_paragraph, format_job_heading
from .constants import (
    SECTION_SUMMARY,
    SECTION_EXPERIENCE,
    SECTION_SKILLS,
    SECTION_CERTIFICATIONS,
    SECTION_EDUCATION,
    RAW_RESUME_FILENAME,
    PDF_RESUME_FILENAME,
)
