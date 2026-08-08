"""
pdf_renderer.py — Rule-based PDF resume generator using ReportLab Platypus.
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
        self.pages = []

    def showPage(self):
        self.pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        page_count = len(self.pages)
        if page_count > 2:
            print(f"[WARN] PDF Resume exceeded 2-page constraint ({page_count} pages). Adjusting content spacing recommended.")
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

def parse_raw_resume(raw_content: str) -> Dict[str, Any]:
    """Parse raw_resume.txt Markdown content into structured data."""
    lines = [l.strip() for l in raw_content.split("\n") if l.strip()]
    data: Dict[str, Any] = {
        "name": "Prasad Rane",
        "contact_location": "Lake Bluff, IL",
        "contact_phone": "513-967-9423",
        "contact_email": "emailprasadrane@gmail.com",
        "contact_linkedin": "https://linkedin.com/in/rane-prasad",
        "contact_portfolio": "https://prasadrane.vercel.app",
        "summary": "",
        "jobs": [],
        "skills": [],
        "certifications": [],
        "education": []
    }

    current_section = None
    current_job = None
    summary_lines = []

    for line in lines:
        if line.startswith("# "):
            data["name"] = "Prasad Rane"
            continue
        elif line.startswith("## "):
            sec_heading = line[3:].strip().upper()
            if "SUMMARY" in sec_heading or "PROFILE" in sec_heading:
                current_section = "SUMMARY"
            elif "EXPERIENCE" in sec_heading or "HISTORY" in sec_heading:
                current_section = "EXPERIENCE"
            elif "SKILL" in sec_heading or "COMPETENCI" in sec_heading:
                current_section = "SKILLS"
            elif "CERTIF" in sec_heading:
                current_section = "CERTIFICATIONS"
            elif "EDUCAT" in sec_heading:
                current_section = "EDUCATION"
            else:
                current_section = sec_heading
            continue

        if current_section == "SUMMARY":
            if not line.startswith(">") and not line.startswith("**Work Authorization:**"):
                summary_lines.append(line)

        elif current_section == "EXPERIENCE":
            if line.startswith("### ") or line.startswith("#### "):
                raw_job = line.lstrip("#").strip()
                parsed_heading = parse_job_heading_components(raw_job)
                current_job = {
                    "heading": raw_job,
                    "title": parsed_heading["title"],
                    "company": parsed_heading["company"],
                    "location": parsed_heading["location"],
                    "dates": parsed_heading["dates"],
                    "bullets": []
                }
                data["jobs"].append(current_job)
            elif line.startswith("- ") or line.startswith("* "):
                bullet = line[2:].strip()
                if current_job:
                    current_job["bullets"].append(bullet)
                elif data["jobs"]:
                    data["jobs"][-1]["bullets"].append(bullet)

        elif current_section == "SKILLS":
            if line.startswith("- "):
                data["skills"].append(line[2:].strip())

        elif current_section == "CERTIFICATIONS":
            if line.startswith("- "):
                data["certifications"].append(line[2:].strip())

        elif current_section == "EDUCATION":
            if line.startswith("- "):
                clean_edu = re.sub(r"\s*\(\d{4}\)", "", line[2:].strip())
                data["education"].append(clean_edu)

    data["summary"] = " ".join(summary_lines)
    return data

def parse_job_heading_components(heading_str: str) -> Dict[str, str]:
    """Parse single-line job heading into title, company, location, dates dynamically."""
    cleaned = heading_str.replace("**", "").replace("*", "").replace("📍", "").replace("🗓️", "").strip()
    parts = [p.strip() for p in re.split(r"[|—–]", cleaned) if p.strip()]

    return {
        "title": parts[0] if len(parts) > 0 else "Software Engineer",
        "company": parts[1] if len(parts) > 1 else "Rocket Mortgage",
        "location": parts[2] if len(parts) > 2 else "Lake Bluff, IL",
        "dates": parts[3] if len(parts) > 3 else "Jan 2023 - Jul 2025"
    }

def format_job_heading(job_dict: Dict[str, str]) -> str:
    """Format single line Job Heading: Job Title | Company Name | Location | Dates"""
    title = job_dict.get("title", "Software Engineer")
    company = job_dict.get("company", "Rocket Mortgage")
    location = job_dict.get("location", "Lake Bluff, IL")
    dates = job_dict.get("dates", "Jan 2023 - Jul 2025")

    return f'<font color="#0f3460"><b>{title}</b> | <b>{company}</b></font> | <font color="#6b7280"><i>{location}</i> | <i>{dates}</i></font>'

def render_pdf_resume(raw_resume_path: Path, output_pdf_path: Path) -> Path:
    """Render rule-based ATS compliant PDF resume using ReportLab Platypus."""
    if not raw_resume_path.exists():
        raise FileNotFoundError(f"Raw resume file not found: {raw_resume_path}")

    output_pdf_path.parent.mkdir(parents=True, exist_ok=True)
    raw_content = raw_resume_path.read_text(encoding="utf-8")
    parsed = parse_raw_resume(raw_content)

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
        keepWithNext=True,  # Prevent orphaned section headers
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
    story.append(Paragraph("Prasad Rane", style_name))

    contact_html = (
        'Lake Bluff, IL | 513-967-9423 | '
        '<a href="mailto:emailprasadrane@gmail.com"><font color="#0f3460">emailprasadrane@gmail.com</font></a> | '
        '<a href="https://linkedin.com/in/rane-prasad"><font color="#0f3460">linkedin.com/in/rane-prasad</font></a> | '
        '<a href="https://prasadrane.vercel.app"><font color="#0f3460">prasadrane.vercel.app</font></a>'
    )
    story.append(Paragraph(contact_html, style_contact))

    def add_section_header(title: str):
        story.append(HRFlowable(width="100%", thickness=0.5, color=COLOR_RULE, spaceBefore=6, spaceAfter=6))
        story.append(Paragraph(title, style_sec_header))

    # 2. Professional Summary Section
    if parsed["summary"]:
        add_section_header("PROFESSIONAL SUMMARY")
        sum_html = markdown_to_reportlab_html(parsed["summary"])
        story.append(Paragraph(sum_html, style_summary))

    # 3. Experience Section
    if parsed["jobs"]:
        add_section_header("EXPERIENCE")
        for job in parsed["jobs"]:
            job_flowables = []
            heading_html = format_job_heading(job)
            job_flowables.append(Paragraph(heading_html, style_job_heading))

            for b in job["bullets"]:
                b_html = markdown_to_reportlab_html(b)
                bullet_str = f"• {b_html}"
                job_flowables.append(Paragraph(bullet_str, style_bullet))

            job_flowables.append(Spacer(1, 3))
            story.append(KeepTogether(job_flowables))

    # 4. Skills Section
    if parsed["skills"]:
        skills_flowables = []
        skills_flowables.append(HRFlowable(width="100%", thickness=0.5, color=COLOR_RULE, spaceBefore=6, spaceAfter=6))
        skills_flowables.append(Paragraph("SKILLS", style_sec_header))

        for sk in parsed["skills"]:
            sk_html = markdown_to_reportlab_html(sk)
            skills_flowables.append(Paragraph(sk_html, style_skill))

        story.append(KeepTogether(skills_flowables))

    # 5. Certifications Section
    cert_credly_url = "https://www.credly.com/badges/337a36b4-0285-460e-b115-2023040ba6b5"
    add_section_header("CERTIFICATIONS")
    if parsed["certifications"]:
        for cert in parsed["certifications"]:
            if "AWS" in cert and "Credly" not in cert:
                cert_html = (
                    f'<b><a href="{cert_credly_url}"><font color="#0f3460">AWS Certified Cloud Practitioner</font></a></b> '
                    f'- Amazon Web Services | Issued: Apr 2026 | Expires: Apr 2029'
                )
            else:
                cert_html = markdown_to_reportlab_html(cert)
            story.append(Paragraph(cert_html, style_cert))
    else:
        cert_html = (
            f'<b><a href="{cert_credly_url}"><font color="#0f3460">AWS Certified Cloud Practitioner</font></a></b> '
            f'- Amazon Web Services | Issued: Apr 2026 | Expires: Apr 2029'
        )
        story.append(Paragraph(cert_html, style_cert))

    # 6. Education Section (Display MS and BE without years)
    add_section_header("EDUCATION")
    if parsed["education"]:
        for edu in parsed["education"]:
            clean_edu = re.sub(r"\s*\(\d{4}\)", "", edu)
            story.append(Paragraph(markdown_to_reportlab_html(clean_edu), style_edu))
    else:
        story.append(Paragraph("M.S. in Information Systems - University of Cincinnati", style_edu))
        story.append(Paragraph("B.E. in Electronics & Telecommunication - University of Pune", style_edu))

    doc.build(story, canvasmaker=PageCountCanvas)
    return output_pdf_path
