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
    MAX_PAGES,
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


class AdaptivePageCanvas(PageCountCanvas):
    """Canvas that records total generated pages for adaptive two-pass compaction."""
    last_page_count = 0

    def showPage(self):
        super().showPage()
        AdaptivePageCanvas.last_page_count = self._page_count


def _build_header_story(parsed: ResumeData, styles: dict) -> List[Any]:
    """Build flowables for Name and Contact Header."""
    story = [Paragraph(parsed.name, styles["name"])]
    contact_html = format_contact_paragraph(parsed)
    if contact_html:
        story.append(Paragraph(contact_html, styles["contact"]))
    return story

def _build_summary_story(parsed: ResumeData, styles: dict) -> List[Any]:
    """Build flowables for Executive Summary."""
    if not parsed.summary:
        return []
    story = create_section_header_flowables(SECTION_SUMMARY, styles["sec_header"])
    story.append(Paragraph(markdown_to_reportlab_html(parsed.summary), styles["summary"]))
    return story

def _build_experience_story(parsed: ResumeData, styles: dict) -> List[Any]:
    """Build flowables for Experience section with KeepTogether job blocks."""
    if not parsed.jobs:
        return []
    story = create_section_header_flowables(SECTION_EXPERIENCE, styles["sec_header"])
    for job in parsed.jobs:
        job_flowables = [Paragraph(format_job_heading(job), styles["job_heading"])]
        for bullet in job.bullets:
            bullet_html = markdown_to_reportlab_html(bullet)
            job_flowables.append(Paragraph(f"&bull; {bullet_html}", styles["bullet"]))
        story.append(KeepTogether(job_flowables))
    return story

def _build_skills_story(parsed: ResumeData, styles: dict) -> List[Any]:
    """Build flowables for Technical Skills."""
    if not parsed.skills:
        return []
    story = create_section_header_flowables(SECTION_SKILLS, styles["sec_header"])
    for skill_cat in parsed.skills:
        skill_html = markdown_to_reportlab_html(skill_cat)
        story.append(Paragraph(f"&bull; {skill_html}", styles["skill"]))
    return story

def _build_certifications_story(parsed: ResumeData, styles: dict) -> List[Any]:
    """Build flowables for Certifications."""
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
    """Render PDF document directly from ResumeData Pydantic model with adaptive two-pass 2-page budgeting."""
    try:
        output_pdf_path.parent.mkdir(parents=True, exist_ok=True)
    except (OSError, PermissionError):
        import tempfile
        output_pdf_path = Path(tempfile.gettempdir()) / "output" / output_pdf_path.name
        output_pdf_path.parent.mkdir(parents=True, exist_ok=True)

    def _build_with_styles(styles_dict) -> int:
        doc = SimpleDocTemplate(
            str(output_pdf_path),
            pagesize=letter,
            leftMargin=MARGIN_LEFT_RIGHT,
            rightMargin=MARGIN_LEFT_RIGHT,
            topMargin=MARGIN_TOP_BOTTOM,
            bottomMargin=MARGIN_TOP_BOTTOM,
        )
        story = []
        story.extend(_build_header_story(parsed, styles_dict))
        story.extend(_build_summary_story(parsed, styles_dict))
        story.extend(_build_experience_story(parsed, styles_dict))
        story.extend(_build_skills_story(parsed, styles_dict))
        story.extend(_build_certifications_story(parsed, styles_dict))
        story.extend(_build_education_story(parsed, styles_dict))

        AdaptivePageCanvas.last_page_count = 0
        doc.build(story, canvasmaker=AdaptivePageCanvas)
        return AdaptivePageCanvas.last_page_count

    # Pass 1: standard layout
    styles = get_resume_styles()
    pages = _build_with_styles(styles)

    # Pass 2: adaptive compaction if content exceeds MAX_PAGES
    if pages > MAX_PAGES:
        compact_styles = get_resume_styles(compact=True)
        pages = _build_with_styles(compact_styles)
        if pages > MAX_PAGES:
            ultra_styles = get_resume_styles(ultra_compact=True)
            _build_with_styles(ultra_styles)

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


def pdf_to_data_uri(pdf_path: Path) -> str:
    """Read a PDF file and return base64 encoded data URI."""
    import base64
    pdf_bytes = Path(pdf_path).read_bytes()
    b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
    return f"data:application/pdf;base64,{b64_pdf}"


_pdf_to_data_uri = pdf_to_data_uri

