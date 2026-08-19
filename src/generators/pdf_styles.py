"""
pdf_styles.py — ReportLab styling, color palettes, ParagraphStyles, and HTML formatting helpers for PDF rendering.
"""

import re
from typing import Dict, Tuple
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

def get_resume_styles(compact: bool = False, ultra_compact: bool = False) -> Dict[str, ParagraphStyle]:
    """Return configured ReportLab ParagraphStyles for ATS resume layout with adaptive compact modes."""
    styles = getSampleStyleSheet()
    font_family = "Helvetica"
    font_bold = "Helvetica-Bold"

    if ultra_compact:
        body_size, body_lead, bullet_space = 8.8, 11.8, 1.8
        sec_size, sec_lead, sec_space = 9.8, 12.0, 3.5
        name_size, name_lead, name_space = 19.5, 22.5, 4.0
        contact_size, contact_lead, contact_space = 8.6, 11.2, 5.5
    elif compact:
        body_size, body_lead, bullet_space = 9.0, 12.2, 2.2
        sec_size, sec_lead, sec_space = 10.0, 12.5, 4.0
        name_size, name_lead, name_space = 20.0, 23.0, 4.0
        contact_size, contact_lead, contact_space = 8.8, 11.5, 6.0
    else:
        body_size, body_lead, bullet_space = 9.2, 12.5, 2.8
        sec_size, sec_lead, sec_space = 10.2, 12.8, 4.5
        name_size, name_lead, name_space = 21.0, 24.0, 5.0
        contact_size, contact_lead, contact_space = 9.0, 12.0, 8.0

    return {
        "name": ParagraphStyle(
            "ResName",
            parent=styles["Normal"],
            fontName=font_bold,
            fontSize=name_size,
            leading=name_lead,
            textColor=COLOR_DARK,
            spaceAfter=name_space,
            alignment=0,
        ),
        "contact": ParagraphStyle(
            "ResContact",
            parent=styles["Normal"],
            fontName=font_family,
            fontSize=contact_size,
            leading=contact_lead,
            textColor=COLOR_META,
            spaceAfter=contact_space,
            alignment=0,
        ),
        "sec_header": ParagraphStyle(
            "ResSecHeader",
            parent=styles["Normal"],
            fontName=font_bold,
            fontSize=sec_size,
            leading=sec_lead,
            textColor=COLOR_DARK,
            spaceAfter=sec_space,
            alignment=0,
            keepWithNext=True,
        ),
        "job_heading": ParagraphStyle(
            "ResJobHeading",
            parent=styles["Normal"],
            fontName=font_family,
            fontSize=sec_size,
            leading=sec_lead,
            textColor=COLOR_DARK,
            spaceAfter=3 if (compact or ultra_compact) else 4,
            alignment=0,
        ),
        "job_heading_left": ParagraphStyle(
            "ResJobHeadingLeft",
            parent=styles["Normal"],
            fontName=font_family,
            fontSize=sec_size,
            leading=sec_lead,
            textColor=COLOR_DARK,
            spaceAfter=0,
            alignment=0,
        ),
        "job_heading_right": ParagraphStyle(
            "ResJobHeadingRight",
            parent=styles["Normal"],
            fontName=font_family,
            fontSize=body_size,
            leading=sec_lead,
            textColor=COLOR_META,
            spaceAfter=0,
            alignment=2,
        ),
        "bullet": ParagraphStyle(
            "ResBullet",
            parent=styles["Normal"],
            fontName=font_family,
            fontSize=body_size,
            leading=body_lead,
            textColor=COLOR_BODY,
            leftIndent=0,
            firstLineIndent=0,
            spaceAfter=bullet_space,
            alignment=0,
        ),
        "summary": ParagraphStyle(
            "ResSummary",
            parent=styles["Normal"],
            fontName=font_family,
            fontSize=body_size,
            leading=body_lead,
            textColor=COLOR_BODY,
            spaceAfter=4 if (compact or ultra_compact) else 6,
            alignment=0,
        ),
        "skill": ParagraphStyle(
            "ResSkill",
            parent=styles["Normal"],
            fontName=font_family,
            fontSize=body_size,
            leading=body_lead,
            textColor=COLOR_BODY,
            leftIndent=0,
            spaceAfter=2.5 if (compact or ultra_compact) else 4,
            alignment=0,
        ),
        "cert": ParagraphStyle(
            "ResCert",
            parent=styles["Normal"],
            fontName=font_family,
            fontSize=body_size,
            leading=body_lead,
            textColor=COLOR_BODY,
            spaceAfter=1.5 if (compact or ultra_compact) else 2,
            alignment=0,
        ),
        "edu": ParagraphStyle(
            "ResEdu",
            parent=styles["Normal"],
            fontName=font_family,
            fontSize=body_size,
            leading=body_lead,
            textColor=COLOR_BODY,
            spaceAfter=1.5 if (compact or ultra_compact) else 2,
            alignment=0,
        ),
    }

def markdown_to_reportlab_html(text: str) -> str:
    """Convert Markdown bold/italics/backticks and cleanup dashes."""
    if not text:
        return ""
    # Preserve date hyphens while converting em-dashes
    text = re.sub(r"(\b[A-Za-z]{3}\s+\d{4})\s+[—–-]\s+([A-Za-z]{3}\s+\d{4}|\bPresent\b)", r"\1 - \2", text)
    text = text.replace("—", ". ").replace("–", " - ")
    # Convert markdown code backticks `code` -> <b>code</b>
    text = re.sub(r"`([^`]+)`", r"<b>\1</b>", text)
    # Convert **bold** -> <b>bold</b>
    text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
    # Convert *italic* -> <i>italic</i>
    text = re.sub(r"\*(.*?)\*", r"<i>\1</i>", text)
    # Convert markdown links [text](url) -> <a href="url"><font color="#0f3460">\1</font></a>
    text = re.sub(r"\[(.*?)\]\((.*?)\)", r'<a href="\2"><font color="#0f3460">\1</font></a>', text)
    return text.strip()

def format_job_heading_split(job: JobEntry) -> Tuple[str, str]:
    """Format job heading into (left_html, right_html) for two-column presentation."""
    left_parts = []
    if job.title and job.company:
        left_parts.append(f'<font color="#0f3460"><b>{job.title}</b></font> | <b>{job.company}</b>')
    elif job.title or job.company:
        left_parts.append(f'<font color="#0f3460"><b>{job.title or job.company}</b></font>')
    else:
        left_parts.append(job.heading or "")

    right_parts = []
    if job.location:
        right_parts.append(f'<i>{job.location}</i>')
    if job.dates:
        dates_clean = job.dates.replace("–", " - ").replace("—", " - ")
        right_parts.append(f'<i>{dates_clean}</i>')

    left_html = " | ".join(left_parts)
    right_html = f'<font color="#6b7280">{" | ".join(right_parts)}</font>' if right_parts else ""
    return left_html, right_html

def format_education_split(edu_str: str) -> Tuple[str, str]:
    """Format education item into (left_html, right_html) for two-column presentation."""
    if not edu_str:
        return "", ""

    clean = edu_str.replace("—", " - ").replace("–", " - ")

    # Extract date range in parentheses e.g. (2018 - 2019) or (2009 - 2013)
    date_match = re.search(r"\(([^)]*\d{4}[^)]*)\)", clean)
    dates = date_match.group(1).strip() if date_match else ""
    clean_no_date = re.sub(r"\s*\([^)]*\d{4}[^)]*\)", "", clean).strip()

    # Extract GPA if present e.g. **GPA: 3.87**
    gpa_match = re.search(r"\bGPA:\s*([0-9\.]+)\b", clean_no_date, flags=re.IGNORECASE)
    gpa_str = f"GPA: {gpa_match.group(1)}" if gpa_match else ""
    clean_no_gpa = re.sub(r"\|\s*\*?\*?GPA:[^|]*\*?\*?", "", clean_no_date, flags=re.IGNORECASE).strip()

    # Degree is typically before comma or in bold **Degree**
    degree = ""
    deg_match = re.search(r"\*\*(.*?)\*\*", clean_no_gpa)
    if deg_match:
        degree = deg_match.group(1).strip().rstrip(",")
        rest = re.sub(r"\*\*.*?\*\*\s*[,—–-]*\s*", "", clean_no_gpa).strip()
    elif "," in clean_no_gpa:
        parts = [p.strip() for p in clean_no_gpa.split(",") if p.strip()]
        degree = parts[0]
        rest = ", ".join(parts[1:])
    else:
        degree = clean_no_gpa
        rest = ""

    # Parse university and location from rest e.g. "University of Cincinnati, Cincinnati, OH"
    sub_parts = [s.strip() for s in rest.split(",") if s.strip()]
    if len(sub_parts) >= 3:
        school = sub_parts[0]
        location = f"{sub_parts[1]}, {sub_parts[2]}"
    elif len(sub_parts) == 2:
        school = sub_parts[0]
        location = sub_parts[1]
    elif len(sub_parts) == 1:
        school = sub_parts[0]
        location = ""
    else:
        school = ""
        location = ""

    left_parts = []
    if degree:
        left_parts.append(f'<font color="#0f3460"><b>{degree}</b></font>')
    if school:
        left_parts.append(f"<b>{school}</b>")
    if gpa_str:
        left_parts.append(f'<font color="#374151"><b>{gpa_str}</b></font>')

    left_html = " | ".join(left_parts) if left_parts else markdown_to_reportlab_html(edu_str)

    right_parts = []
    if location:
        right_parts.append(location)
    if dates:
        right_parts.append(dates)

    right_html = f'<font color="#6b7280"><i>{" | ".join(right_parts)}</i></font>' if right_parts else ""
    return left_html, right_html

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
        dates_clean = job.dates.replace("–", " - ").replace("—", " - ")
        meta_parts.append(f'<i>{dates_clean}</i>')

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
        display_text = data.contact_linkedin.replace("https://", "").replace("http://", "").replace("www.", "")
        # Use compact handle if github is also present to guarantee 1-line header
        if data.contact_github and "linkedin.com/in/" in display_text:
            display_text = display_text.replace("linkedin.com/in/", "in/")
        items.append(f'<a href="{link_url}"><font color="#0f3460">{display_text}</font></a>')
    if data.contact_github:
        gh_url = data.contact_github if data.contact_github.startswith("http") else f"https://{data.contact_github}"
        display_gh = data.contact_github.replace("https://", "").replace("http://", "").replace("www.", "")
        items.append(f'<a href="{gh_url}"><font color="#0f3460">{display_gh}</font></a>')
    if data.contact_portfolio:
        port_url = data.contact_portfolio if data.contact_portfolio.startswith("http") else f"https://{data.contact_portfolio}"
        display_text = data.contact_portfolio.replace("https://", "").replace("http://", "").replace("www.", "")
        items.append(f'<a href="{port_url}"><font color="#0f3460">{display_text}</font></a>')

    return " | ".join(items)

def create_section_header_flowables(title: str, sec_style: ParagraphStyle) -> list:
    """Create divider line and section header flowables."""
    return [
        HRFlowable(width="100%", thickness=0.5, color=COLOR_RULE, spaceBefore=6, spaceAfter=6),
        Paragraph(title, sec_style)
    ]
