"""
pdf_renderer.py — Rule-based, candidate-agnostic PDF resume generator using ReportLab Platypus and Pydantic models.
Applies SOLID (SRP, OCP) and DRY principles by reusing unified markdown parsing and modular story builders.
Supports 1-Page and 2-Page targeted budgeting.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether, Table, TableStyle

from .constants import (
    MARGIN_LEFT_RIGHT,
    MARGIN_TOP_BOTTOM,
    MAX_PAGES,
    SECTION_CERTIFICATIONS,
    SECTION_EDUCATION,
    SECTION_EXPERIENCE,
    SECTION_PROJECTS,
    SECTION_SKILLS,
    SECTION_SUMMARY,
)
from .models import JobEntry, ResumeData
from .page_budgeter import budget_resume_for_pages
from .pdf_styles import (
    PageCountCanvas,
    create_section_header_flowables,
    format_contact_paragraph,
    format_education_split,
    format_job_heading,
    format_job_heading_split,
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

def _build_skills_story(parsed: ResumeData, styles: dict) -> List[Any]:
    """Build flowables for Technical Skills."""
    if not parsed.skills:
        return []
    story = create_section_header_flowables(SECTION_SKILLS, styles["sec_header"])
    for skill_cat in parsed.skills:
        skill_html = markdown_to_reportlab_html(skill_cat)
        story.append(Paragraph(f"&bull; {skill_html}", styles["skill"]))
    return story

def _build_job_heading_flowable(
    job: JobEntry,
    styles: dict,
    is_first: bool = False,
    space_before: float = 6.0,
    col_widths: Optional[List[float]] = None,
) -> Any:
    """Build two-column left/right job heading table flowable with inter-company spacing and zero left indent."""
    left_html, right_html = format_job_heading_split(job)
    if not right_html:
        p_style = ParagraphStyle(
            "JobHeadSingle",
            parent=styles["job_heading"],
            leftIndent=0,
            firstLineIndent=0,
            spaceBefore=0 if is_first else space_before,
        )
        return Paragraph(format_job_heading(job), p_style)

    left_p = Paragraph(left_html, styles["job_heading_left"])
    right_p = Paragraph(right_html, styles["job_heading_right"])

    # Total usable printable width is 540pt (8.5*72 - 2*36)
    widths = col_widths or [385, 155]
    table = Table([[left_p, right_p]], colWidths=widths, hAlign='LEFT')
    table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    table.spaceBefore = 0 if is_first else space_before
    table.spaceAfter = styles["job_heading"].spaceAfter
    return table


def _build_experience_story(parsed: ResumeData, styles: dict, space_before: float = 6.0) -> List[Any]:
    """Build flowables for Experience section with heading orphan prevention."""
    if not parsed.jobs:
        return []
    story = create_section_header_flowables(SECTION_EXPERIENCE, styles["sec_header"])
    for idx, job in enumerate(parsed.jobs):
        is_first = (idx == 0)
        heading_flowable = _build_job_heading_flowable(job, styles, is_first=is_first, space_before=space_before, col_widths=[385, 155])
        if job.bullets:
            first_b = Paragraph(f"&bull; {markdown_to_reportlab_html(job.bullets[0])}", styles["bullet"])
            story.append(KeepTogether([heading_flowable, first_b]))
            for bullet in job.bullets[1:]:
                bullet_html = markdown_to_reportlab_html(bullet)
                story.append(Paragraph(f"&bull; {bullet_html}", styles["bullet"]))
        else:
            story.append(heading_flowable)
    return story


def _build_projects_story(parsed: ResumeData, styles: dict, space_before: float = 6.0) -> List[Any]:
    """Build flowables for Projects section with heading orphan prevention."""
    if not parsed.projects:
        return []
    story = create_section_header_flowables(SECTION_PROJECTS, styles["sec_header"])
    for idx, proj in enumerate(parsed.projects):
        is_first = (idx == 0)
        heading_flowable = _build_job_heading_flowable(proj, styles, is_first=is_first, space_before=space_before, col_widths=[445, 95])
        if proj.bullets:
            first_b = Paragraph(f"&bull; {markdown_to_reportlab_html(proj.bullets[0])}", styles["bullet"])
            story.append(KeepTogether([heading_flowable, first_b]))
            for bullet in proj.bullets[1:]:
                bullet_html = markdown_to_reportlab_html(bullet)
                story.append(Paragraph(f"&bull; {bullet_html}", styles["bullet"]))
        else:
            story.append(heading_flowable)
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
    """Build flowables for Education section with two-column left/right alignment and zero left indent."""
    if not parsed.education:
        return []
    story = create_section_header_flowables(SECTION_EDUCATION, styles["sec_header"])
    for idx, edu in enumerate(parsed.education):
        left_html, right_html = format_education_split(edu)
        if not right_html:
            story.append(Paragraph(markdown_to_reportlab_html(edu), styles["edu"]))
        else:
            left_p = Paragraph(left_html, styles["job_heading_left"])
            right_p = Paragraph(right_html, styles["job_heading_right"])
            table = Table([[left_p, right_p]], colWidths=[385, 155], hAlign='LEFT')
            table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ]))
            table.spaceBefore = 0 if idx == 0 else 2.5
            table.spaceAfter = styles["edu"].spaceAfter
            story.append(table)
    return story

def render_pdf_from_model(
    parsed: ResumeData,
    output_pdf_path: Path,
    target_pages: int = 2,
    keywords: Optional[List[str]] = None,
) -> Path:
    """Render PDF document directly from ResumeData Pydantic model with adaptive multi-pass page budgeting."""
    try:
        output_pdf_path.parent.mkdir(parents=True, exist_ok=True)
    except (OSError, PermissionError):
        import tempfile
        output_pdf_path = Path(tempfile.gettempdir()) / "output" / output_pdf_path.name
        output_pdf_path.parent.mkdir(parents=True, exist_ok=True)

    # Budget the resume model for the target page count
    budgeted = budget_resume_for_pages(parsed, target_pages=target_pages, keywords=keywords)

    def _build_with_styles(styles_dict) -> int:
        tb_margin = 22.0 if target_pages == 1 else MARGIN_TOP_BOTTOM
        doc = SimpleDocTemplate(
            str(output_pdf_path),
            pagesize=letter,
            leftMargin=MARGIN_LEFT_RIGHT,
            rightMargin=MARGIN_LEFT_RIGHT,
            topMargin=tb_margin,
            bottomMargin=tb_margin,
        )
        story = []
        story.extend(_build_header_story(budgeted, styles_dict))
        story.extend(_build_summary_story(budgeted, styles_dict))
        story.extend(_build_skills_story(budgeted, styles_dict))
        space_before = 5.0 if target_pages == 1 else 7.5
        story.extend(_build_experience_story(budgeted, styles_dict, space_before=space_before))
        story.extend(_build_projects_story(budgeted, styles_dict, space_before=space_before))
        story.extend(_build_certifications_story(budgeted, styles_dict))
        story.extend(_build_education_story(budgeted, styles_dict))

        AdaptivePageCanvas.last_page_count = 0
        doc.build(story, canvasmaker=AdaptivePageCanvas)
        return AdaptivePageCanvas.last_page_count

    if target_pages == 1:
        # Pass 1: Try compact styles
        compact_styles = get_resume_styles(compact=True)
        pages = _build_with_styles(compact_styles)
        if pages > 1:
            ultra_styles = get_resume_styles(ultra_compact=True)
            _build_with_styles(ultra_styles)
    else:
        # Pass 1: Standard styles
        styles = get_resume_styles()
        pages = _build_with_styles(styles)
        if pages > 2:
            compact_styles = get_resume_styles(compact=True)
            pages = _build_with_styles(compact_styles)
            if pages > 2:
                ultra_styles = get_resume_styles(ultra_compact=True)
                _build_with_styles(ultra_styles)

    return output_pdf_path

def render_pdf_resume(
    raw_resume_source: Union[Path, str],
    output_pdf_path: Path,
    parsed_data: Optional[ResumeData] = None,
    target_pages: int = 2,
    keywords: Optional[List[str]] = None,
) -> Path:
    """Render rule-based ATS compliant PDF resume supporting Path or pre-parsed ResumeData (OCP/DIP)."""
    if parsed_data is not None:
        return render_pdf_from_model(parsed_data, output_pdf_path, target_pages=target_pages, keywords=keywords)

    raw_path = Path(raw_resume_source)
    if not raw_path.exists():
        raise FileNotFoundError(f"Raw resume file not found: {raw_path}")

    raw_content = raw_path.read_text(encoding="utf-8")
    parsed = parse_resume_markdown(raw_content)
    return render_pdf_from_model(parsed, output_pdf_path, target_pages=target_pages, keywords=keywords)


def pdf_to_data_uri(pdf_path: Path) -> str:
    """Read a PDF file and return base64 encoded data URI."""
    import base64
    pdf_bytes = Path(pdf_path).read_bytes()
    b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
    return f"data:application/pdf;base64,{b64_pdf}"


_pdf_to_data_uri = pdf_to_data_uri
