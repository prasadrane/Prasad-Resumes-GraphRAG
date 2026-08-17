"""
pdf_styles.py — ReportLab styling, color palettes, ParagraphStyles, and HTML formatting helpers for PDF rendering.
"""

import re
from typing import Dict
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.platypus import HRFlowable, Paragraph

from .constants import MAX_PAGES
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
        if self._page_count > MAX_PAGES:
            print(f"[WARN] PDF Resume exceeded {MAX_PAGES}-page constraint ({self._page_count} pages). Adjusting content spacing recommended.")
        super().save()

def get_resume_styles() -> Dict[str, ParagraphStyle]:
    """Return configured ReportLab ParagraphStyles for ATS resume layout."""
    styles = getSampleStyleSheet()
    font_family = "Helvetica"
    font_bold = "Helvetica-Bold"

    return {
        "name": ParagraphStyle(
            "ResName",
            parent=styles["Normal"],
            fontName=font_bold,
            fontSize=23,
            leading=26,
            textColor=COLOR_DARK,
            spaceAfter=6,
            alignment=0,
        ),
        "contact": ParagraphStyle(
            "ResContact",
            parent=styles["Normal"],
            fontName=font_family,
            fontSize=9.5,
            leading=13,
            textColor=COLOR_META,
            spaceAfter=12,
            alignment=0,
        ),
        "sec_header": ParagraphStyle(
            "ResSecHeader",
            parent=styles["Normal"],
            fontName=font_bold,
            fontSize=10.5,
            leading=13,
            textColor=COLOR_DARK,
            spaceAfter=6,
            alignment=0,
            keepWithNext=True,
        ),
        "job_heading": ParagraphStyle(
            "ResJobHeading",
            parent=styles["Normal"],
            fontName=font_family,
            fontSize=10.5,
            leading=13,
            textColor=COLOR_DARK,
            spaceAfter=4,
            alignment=0,
        ),
        "bullet": ParagraphStyle(
            "ResBullet",
            parent=styles["Normal"],
            fontName=font_family,
            fontSize=9.5,
            leading=13,
            textColor=COLOR_BODY,
            leftIndent=0,
            firstLineIndent=0,
            spaceAfter=3,
            alignment=0,
        ),
        "summary": ParagraphStyle(
            "ResSummary",
            parent=styles["Normal"],
            fontName=font_family,
            fontSize=9.5,
            leading=13,
            textColor=COLOR_BODY,
            spaceAfter=6,
            alignment=0,
        ),
        "skill": ParagraphStyle(
            "ResSkill",
            parent=styles["Normal"],
            fontName=font_family,
            fontSize=9.5,
            leading=13,
            textColor=COLOR_BODY,
            leftIndent=0,
            spaceAfter=4,
            alignment=0,
        ),
        "cert": ParagraphStyle(
            "ResCert",
            parent=styles["Normal"],
            fontName=font_family,
            fontSize=9.5,
            leading=13,
            textColor=COLOR_BODY,
            spaceAfter=2,
            alignment=0,
        ),
        "edu": ParagraphStyle(
            "ResEdu",
            parent=styles["Normal"],
            fontName=font_family,
            fontSize=9.5,
            leading=13,
            textColor=COLOR_BODY,
            spaceAfter=2,
            alignment=0,
        ),
    }

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
    # Convert markdown links [text](url) -> <a href="url"><font color="#0f3460">\1</font></a>
    text = re.sub(r"\[(.*?)\]\((.*?)\)", r'<a href="\2"><font color="#0f3460">\1</font></a>', text)
    return text.strip()

def format_job_heading(job: JobEntry) -> str:
    """Format single line Job Heading: Job Title | Company Name | Location | Dates"""
    heading_parts = []
    if job.title and job.company:
        heading_parts.append(f'<font color="#0f3460"><b>{job.title}</b> | <b>{job.company}</b></font>')
    elif job.title or job.company:
        heading_parts.append(f'<font color="#0f3460"><b>{job.title or job.company}</b></font>')

    meta_parts = []
    if job.location:
        meta_parts.append(f'<i>{job.location}</i>')
    if job.dates:
        meta_parts.append(f'<i>{job.dates}</i>')

    if meta_parts:
        heading_parts.append(f'<font color="#6b7280">{" | ".join(meta_parts)}</font>')

    return " | ".join(heading_parts) if heading_parts else job.heading

def format_contact_paragraph(data: ResumeData) -> str:
    """Format contact items into reportlab clickable HTML paragraph string dynamically."""
    items = []
    if data.contact_location:
        items.append(data.contact_location)
    if data.contact_phone:
        items.append(data.contact_phone)
    if data.contact_email:
        email_clean = data.contact_email.replace("mailto:", "")
        items.append(f'<a href="mailto:{email_clean}"><font color="#0f3460">{email_clean}</font></a>')
    if data.contact_linkedin:
        link_url = data.contact_linkedin if data.contact_linkedin.startswith("http") else f"https://{data.contact_linkedin}"
        display_text = data.contact_linkedin.replace("https://", "").replace("http://", "")
        items.append(f'<a href="{link_url}"><font color="#0f3460">{display_text}</font></a>')
    if data.contact_portfolio:
        port_url = data.contact_portfolio if data.contact_portfolio.startswith("http") else f"https://{data.contact_portfolio}"
        display_text = data.contact_portfolio.replace("https://", "").replace("http://", "")
        items.append(f'<a href="{port_url}"><font color="#0f3460">{display_text}</font></a>')

    return " | ".join(items)

def create_section_header_flowables(title: str, sec_style: ParagraphStyle) -> list:
    """Create divider line and section header flowables."""
    return [
        HRFlowable(width="100%", thickness=0.5, color=COLOR_RULE, spaceBefore=6, spaceAfter=6),
        Paragraph(title, sec_style)
    ]
