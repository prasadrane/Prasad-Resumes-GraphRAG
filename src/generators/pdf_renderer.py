"""
pdf_renderer.py — Rule-based, candidate-agnostic PDF resume generator using ReportLab Platypus and Pydantic models.
Applies SOLID (SRP, OCP) and DRY principles by reusing unified markdown parsing and modular story builders.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether

from .constants import (
    MARGIN_LEFT_RIGHT,
    MARGIN_TOP_BOTTOM,
    SECTION_CERTIFICATIONS,
    SECTION_EDUCATION,
    SECTION_EXPERIENCE,
    SECTION_SKILLS,
    SECTION_SUMMARY,
)
from .models import ResumeData
from .pdf_styles import (
    PageCountCanvas,
    create_section_header_flowables,
    format_contact_paragraph,
    format_job_heading,
    get_resume_styles,
    markdown_to_reportlab_html,
)
from .resume_parser import parse_resume_markdown

# Alias for backward compatibility
parse_raw_resume = parse_resume_markdown

def _build_header_story(parsed: ResumeData, styles: dict) -> List[Any]:
    """Build flowables for Name and Contact Header."""
    story = [Paragraph(parsed.name, styles["name"])]
    contact_html = format_contact_paragraph(parsed)
    if contact_html:
        story.append(Paragraph(contact_html, styles["contact"]))
    return story

def _build_summary_story(parsed: ResumeData, styles: dict) -> List[Any]:
    """Build flowables for Professional Summary section."""
    if not parsed.summary:
        return []
    story = create_section_header_flowables(SECTION_SUMMARY, styles["sec_header"])
    sum_html = markdown_to_reportlab_html(parsed.summary)
    story.append(Paragraph(sum_html, styles["summary"]))
    return story

def _build_experience_story(parsed: ResumeData, styles: dict) -> List[Any]:
    """Build flowables for Experience section with KeepTogether job blocks."""
    if not parsed.jobs:
        return []
    story = create_section_header_flowables(SECTION_EXPERIENCE, styles["sec_header"])
    for job in parsed.jobs:
        job_flowables = [Paragraph(format_job_heading(job), styles["job_heading"])]
        for b in job.bullets:
            b_html = markdown_to_reportlab_html(b)
            job_flowables.append(Paragraph(f"• {b_html}", styles["bullet"]))
        job_flowables.append(Spacer(1, 3))
        story.append(KeepTogether(job_flowables))
    return story

def _build_skills_story(parsed: ResumeData, styles: dict) -> List[Any]:
    """Build flowables for Skills section."""
    if not parsed.skills:
        return []
    skills_flowables = create_section_header_flowables(SECTION_SKILLS, styles["sec_header"])
    for sk in parsed.skills:
        sk_html = markdown_to_reportlab_html(sk)
        skills_flowables.append(Paragraph(sk_html, styles["skill"]))
    return [KeepTogether(skills_flowables)]

def _build_certifications_story(parsed: ResumeData, styles: dict) -> List[Any]:
    """Build flowables for Certifications section."""
    if not parsed.certifications:
        return []
    story = create_section_header_flowables(SECTION_CERTIFICATIONS, styles["sec_header"])
    for cert in parsed.certifications:
        cert_html = markdown_to_reportlab_html(cert)
        story.append(Paragraph(cert_html, styles["cert"]))
    return story

def _build_education_story(parsed: ResumeData, styles: dict) -> List[Any]:
    """Build flowables for Education section."""
    if not parsed.education:
        return []
    story = create_section_header_flowables(SECTION_EDUCATION, styles["sec_header"])
    for edu in parsed.education:
        story.append(Paragraph(markdown_to_reportlab_html(edu), styles["edu"]))
    return story

def render_pdf_from_model(parsed: ResumeData, output_pdf_path: Path) -> Path:
    """Render PDF document directly from ResumeData Pydantic model using modular story builders."""
    try:
        output_pdf_path.parent.mkdir(parents=True, exist_ok=True)
    except (OSError, PermissionError):
        import tempfile
        output_pdf_path = Path(tempfile.gettempdir()) / "output" / output_pdf_path.name
        output_pdf_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(output_pdf_path),
        pagesize=letter,
        leftMargin=MARGIN_LEFT_RIGHT,
        rightMargin=MARGIN_LEFT_RIGHT,
        topMargin=MARGIN_TOP_BOTTOM,
        bottomMargin=MARGIN_TOP_BOTTOM,
    )

    styles = get_resume_styles()
    story = []

    # Build story modularly per section
    story.extend(_build_header_story(parsed, styles))
    story.extend(_build_summary_story(parsed, styles))
    story.extend(_build_experience_story(parsed, styles))
    story.extend(_build_skills_story(parsed, styles))
    story.extend(_build_certifications_story(parsed, styles))
    story.extend(_build_education_story(parsed, styles))

    doc.build(story, canvasmaker=PageCountCanvas)
    return output_pdf_path

def render_pdf_resume(raw_resume_source: Union[Path, str], output_pdf_path: Path, parsed_data: Optional[ResumeData] = None) -> Path:
    """Render rule-based ATS compliant PDF resume supporting Path or pre-parsed ResumeData (OCP/DIP)."""
    if parsed_data is not None:
        return render_pdf_from_model(parsed_data, output_pdf_path)

    raw_path = Path(raw_resume_source)
    if not raw_path.exists():
        raise FileNotFoundError(f"Raw resume file not found: {raw_path}")

    raw_content = raw_path.read_text(encoding="utf-8")
    parsed = parse_resume_markdown(raw_content)
    return render_pdf_from_model(parsed, output_pdf_path)
