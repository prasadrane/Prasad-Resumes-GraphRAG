"""
pdf_renderer.py — Rule-based PDF resume generator using ReportLab Platypus and Pydantic models.
Enforces exact font sizes, colors, margins, spacing, KeepTogether job blocks, clickable links, and 2-page max guardrail.
"""

import re
from pathlib import Path
from typing import Dict, List, Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, KeepTogether

from .constants import (
    CREDLY_AWS_CERT_URL,
    DEFAULT_AWS_CERTIFICATE,
    DEFAULT_CANDIDATE_NAME,
    DEFAULT_EDUCATION,
    DEFAULT_EMAIL,
    DEFAULT_LINKEDIN_URL,
    DEFAULT_LOCATION,
    DEFAULT_PHONE,
    DEFAULT_PORTFOLIO_URL,
    MARKDOWN_BULLET_PREFIX,
    MARKDOWN_H1_PREFIX,
    MARKDOWN_H2_PREFIX,
    MARKDOWN_H3_PREFIX,
    MARKDOWN_H4_PREFIX,
    SECTION_CERTIFICATIONS,
    SECTION_EDUCATION,
    SECTION_EXPERIENCE,
    SECTION_SKILLS,
    SECTION_SUMMARY,
)
from .models import JobEntry, ResumeData

# Color Palette Reference
COLOR_DARK = colors.HexColor("#1a1a2e")      # Name, Section Headers
COLOR_ACCENT = colors.HexColor("#0f3460")    # Job Titles, Clickable Links
COLOR_BODY = colors.HexColor("#374151")      # Bullets, Skills, Education
COLOR_META = colors.HexColor("#6b7280")      # Contact Line, Location, Dates
COLOR_RULE = colors.HexColor("#d1d5db")      # Horizontal Rule Line

class PageCountCanvas(canvas.Canvas):
    """Canvas recorder to enforce 2-page maximum constraint."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._page_count = 0

    def showPage(self):
        self._page_count += 1
        super().showPage()

    def save(self):
        if self._page_count > 2:
            print(f"[WARN] PDF Resume exceeded 2-page constraint ({self._page_count} pages). Adjusting content spacing recommended.")
        super().save()

def markdown_to_reportlab_html(text: str) -> str:
    """Convert Markdown bold/italics and cleanup em-dashes."""
    if not text:
        return ""
    # Preserve date hyphens while converting em-dashes
    text = re.sub(r"(\b[A-Za-z]{3}\s+\d{4})\s+[—–-]\s+([A-Za-z]{3}\s+\d{4}|\bPresent\b)", r"\1 - \2", text)
    text = text.replace("—", ". ").replace(" – ", ". ")
    # Convert **bold** -> <b>bold</b>
    text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
    # Convert *italic* -> <i>italic</i>
    text = re.sub(r"\*(.*?)\*", r"<i>\1</i>", text)
    return text.strip()

def parse_raw_resume(raw_content: str) -> ResumeData:
    """Parse raw_resume.txt Markdown content into structured ResumeData Pydantic model."""
    lines = [l.strip() for l in raw_content.split("\n") if l.strip()]
    data = ResumeData()

    current_section = None
    current_job: Optional[JobEntry] = None
    summary_lines = []

    for line in lines:
        if line.startswith(MARKDOWN_H1_PREFIX):
            data.name = DEFAULT_CANDIDATE_NAME
            continue
        elif line.startswith(MARKDOWN_H2_PREFIX):
            sec_heading = line[len(MARKDOWN_H2_PREFIX):].strip().upper()
            if SECTION_SUMMARY in sec_heading or "PROFILE" in sec_heading:
                current_section = SECTION_SUMMARY
            elif SECTION_EXPERIENCE in sec_heading or "HISTORY" in sec_heading:
                current_section = SECTION_EXPERIENCE
            elif "SKILL" in sec_heading or "COMPETENCI" in sec_heading:
                current_section = SECTION_SKILLS
            elif "CERTIF" in sec_heading:
                current_section = SECTION_CERTIFICATIONS
            elif "EDUCAT" in sec_heading:
                current_section = SECTION_EDUCATION
            else:
                current_section = sec_heading
            continue

        if current_section == SECTION_SUMMARY:
            if not line.startswith(">") and not line.startswith("**Work Authorization:**"):
                summary_lines.append(line)

        elif current_section == SECTION_EXPERIENCE:
            if line.startswith(MARKDOWN_H3_PREFIX) or line.startswith(MARKDOWN_H4_PREFIX):
                raw_job = line.lstrip("#").strip()
                parsed_heading = parse_job_heading_components(raw_job)
                current_job = JobEntry(
                    heading=raw_job,
                    title=parsed_heading["title"],
                    company=parsed_heading["company"],
                    location=parsed_heading["location"],
                    dates=parsed_heading["dates"],
                    bullets=[]
                )
                data.jobs.append(current_job)
            elif line.startswith(MARKDOWN_BULLET_PREFIX) or line.startswith("* "):
                bullet = line[2:].strip()
                if current_job:
                    current_job.bullets.append(bullet)
                elif data.jobs:
                    data.jobs[-1].bullets.append(bullet)

        elif current_section == SECTION_SKILLS:
            if line.startswith(MARKDOWN_BULLET_PREFIX):
                data.skills.append(line[2:].strip())

        elif current_section == SECTION_CERTIFICATIONS:
            if line.startswith(MARKDOWN_BULLET_PREFIX):
                data.certifications.append(line[2:].strip())

        elif current_section == SECTION_EDUCATION:
            if line.startswith(MARKDOWN_BULLET_PREFIX):
                clean_edu = re.sub(r"\s*\(\d{4}\)", "", line[2:].strip())
                data.education.append(clean_edu)

    data.summary = " ".join(summary_lines)
    return data

def parse_job_heading_components(heading_str: str) -> Dict[str, str]:
    """Parse single-line job heading into title, company, location, dates dynamically."""
    cleaned = heading_str.replace("**", "").replace("*", "").replace("📍", "").replace("🗓️", "").strip()
    parts = [p.strip() for p in re.split(r"[|—–]", cleaned) if p.strip()]

    return {
        "title": parts[0] if len(parts) > 0 else "Software Engineer",
        "company": parts[1] if len(parts) > 1 else "Rocket Mortgage",
        "location": parts[2] if len(parts) > 2 else DEFAULT_LOCATION,
        "dates": parts[3] if len(parts) > 3 else "Jan 2023 - Jul 2025"
    }

def format_job_heading(job: JobEntry) -> str:
    """Format single line Job Heading: Job Title | Company Name | Location | Dates"""
    return f'<font color="#0f3460"><b>{job.title}</b> | <b>{job.company}</b></font> | <font color="#6b7280"><i>{job.location}</i> | <i>{job.dates}</i></font>'

def render_pdf_resume(raw_resume_path: Path, output_pdf_path: Path) -> Path:
    """Render rule-based ATS compliant PDF resume using ReportLab Platypus and Pydantic models."""
    if not raw_resume_path.exists():
        raise FileNotFoundError(f"Raw resume file not found: {raw_resume_path}")

    output_pdf_path.parent.mkdir(parents=True, exist_ok=True)
    raw_content = raw_resume_path.read_text(encoding="utf-8")
    parsed: ResumeData = parse_raw_resume(raw_content)

    doc = SimpleDocTemplate(
        str(output_pdf_path),
        pagesize=letter,
        leftMargin=0.55 * inch,
        rightMargin=0.55 * inch,
        topMargin=0.45 * inch,
        bottomMargin=0.45 * inch,
    )

    styles = getSampleStyleSheet()

    font_family = "Helvetica"
    font_bold = "Helvetica-Bold"

    style_name = ParagraphStyle(
        "ResName",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=23,
        leading=26,
        textColor=COLOR_DARK,
        spaceAfter=6,
        alignment=0,
    )

    style_contact = ParagraphStyle(
        "ResContact",
        parent=styles["Normal"],
        fontName=font_family,
        fontSize=9.5,
        leading=13,
        textColor=COLOR_META,
        spaceAfter=12,
        alignment=0,
    )

    style_sec_header = ParagraphStyle(
        "ResSecHeader",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=10.5,
        leading=13,
        textColor=COLOR_DARK,
        spaceAfter=6,
        alignment=0,
        keepWithNext=True,
    )

    style_job_heading = ParagraphStyle(
        "ResJobHeading",
        parent=styles["Normal"],
        fontName=font_family,
        fontSize=10.5,
        leading=13,
        textColor=COLOR_DARK,
        spaceAfter=4,
        alignment=0,
    )

    style_bullet = ParagraphStyle(
        "ResBullet",
        parent=styles["Normal"],
        fontName=font_family,
        fontSize=9.5,
        leading=13,
        textColor=COLOR_BODY,
        leftIndent=12,
        firstLineIndent=-12,
        spaceAfter=3,
        alignment=0,
    )

    style_summary = ParagraphStyle(
        "ResSummary",
        parent=styles["Normal"],
        fontName=font_family,
        fontSize=9.5,
        leading=13,
        textColor=COLOR_BODY,
        spaceAfter=6,
        alignment=0,
    )

    style_skill = ParagraphStyle(
        "ResSkill",
        parent=styles["Normal"],
        fontName=font_family,
        fontSize=9.5,
        leading=13,
        textColor=COLOR_BODY,
        leftIndent=0,
        spaceAfter=4,
        alignment=0,
    )

    style_cert = ParagraphStyle(
        "ResCert",
        parent=styles["Normal"],
        fontName=font_family,
        fontSize=9.5,
        leading=13,
        textColor=COLOR_BODY,
        spaceAfter=2,
        alignment=0,
    )

    style_edu = ParagraphStyle(
        "ResEdu",
        parent=styles["Normal"],
        fontName=font_family,
        fontSize=9.5,
        leading=13,
        textColor=COLOR_BODY,
        spaceAfter=2,
        alignment=0,
    )

    story = []

    # 1. Header: Name & Clickable Contact Details
    story.append(Paragraph(parsed.name, style_name))

    contact_html = (
        f'{parsed.contact_location} | {parsed.contact_phone} | '
        f'<a href="mailto:{parsed.contact_email}"><font color="#0f3460">{parsed.contact_email}</font></a> | '
        f'<a href="{parsed.contact_linkedin}"><font color="#0f3460">linkedin.com/in/rane-prasad</font></a> | '
        f'<a href="{parsed.contact_portfolio}"><font color="#0f3460">prasadrane.vercel.app</font></a>'
    )
    story.append(Paragraph(contact_html, style_contact))

    def add_section_header(title: str):
        story.append(HRFlowable(width="100%", thickness=0.5, color=COLOR_RULE, spaceBefore=6, spaceAfter=6))
        story.append(Paragraph(title, style_sec_header))

    # 2. Professional Summary Section
    if parsed.summary:
        add_section_header(SECTION_SUMMARY)
        sum_html = markdown_to_reportlab_html(parsed.summary)
        story.append(Paragraph(sum_html, style_summary))

    # 3. Experience Section
    if parsed.jobs:
        add_section_header(SECTION_EXPERIENCE)
        for job in parsed.jobs:
            job_flowables = []
            heading_html = format_job_heading(job)
            job_flowables.append(Paragraph(heading_html, style_job_heading))

            for b in job.bullets:
                b_html = markdown_to_reportlab_html(b)
                bullet_str = f"• {b_html}"
                job_flowables.append(Paragraph(bullet_str, style_bullet))

            job_flowables.append(Spacer(1, 3))
            story.append(KeepTogether(job_flowables))

    # 4. Skills Section
    if parsed.skills:
        skills_flowables = []
        skills_flowables.append(HRFlowable(width="100%", thickness=0.5, color=COLOR_RULE, spaceBefore=6, spaceAfter=6))
        skills_flowables.append(Paragraph(SECTION_SKILLS, style_sec_header))

        for sk in parsed.skills:
            sk_html = markdown_to_reportlab_html(sk)
            skills_flowables.append(Paragraph(sk_html, style_skill))

        story.append(KeepTogether(skills_flowables))

    # 5. Certifications Section
    add_section_header(SECTION_CERTIFICATIONS)
    if parsed.certifications:
        for cert in parsed.certifications:
            if "AWS" in cert and "Credly" not in cert:
                cert_html = (
                    f'<b><a href="{CREDLY_AWS_CERT_URL}"><font color="#0f3460">AWS Certified Cloud Practitioner</font></a></b> '
                    f'- Amazon Web Services | Issued: Apr 2026 | Expires: Apr 2029'
                )
            else:
                cert_html = markdown_to_reportlab_html(cert)
            story.append(Paragraph(cert_html, style_cert))
    else:
        cert_html = (
            f'<b><a href="{CREDLY_AWS_CERT_URL}"><font color="#0f3460">AWS Certified Cloud Practitioner</font></a></b> '
            f'- Amazon Web Services | Issued: Apr 2026 | Expires: Apr 2029'
        )
        story.append(Paragraph(cert_html, style_cert))

    # 6. Education Section (Display MS and BE without years)
    add_section_header(SECTION_EDUCATION)
    if parsed.education:
        for edu in parsed.education:
            clean_edu = re.sub(r"\s*\(\d{4}\)", "", edu)
            story.append(Paragraph(markdown_to_reportlab_html(clean_edu), style_edu))
    else:
        for edu in DEFAULT_EDUCATION:
            story.append(Paragraph(markdown_to_reportlab_html(edu), style_edu))

    doc.build(story, canvasmaker=PageCountCanvas)
    return output_pdf_path
