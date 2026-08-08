"""
pdf_renderer.py — Rule-based PDF resume generator using ReportLab.
"""

import re
from pathlib import Path
from typing import Dict, List, Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable

def parse_raw_resume(raw_content: str) -> Dict[str, Any]:
    """Parse raw_resume.txt Markdown content into structured data."""
    lines = [l.strip() for l in raw_content.split("\n") if l.strip()]
    data = {
        "name": "Prasad Rane",
        "title": "",
        "contact": "",
        "sections": {}
    }

    if not lines:
        return data

    if lines[0].startswith("# "):
        data["name"] = lines[0][2:].strip()
        lines = lines[1:]

    current_section = "Header"
    data["sections"][current_section] = []

    for line in lines:
        if line.startswith("**Title:**"):
            data["title"] = line.replace("**Title:**", "").strip()
        elif line.startswith("**Contact:**"):
            data["contact"] = line.replace("**Contact:**", "").strip()
        elif line.startswith("## "):
            current_section = line[3:].strip()
            data["sections"][current_section] = []
        else:
            data["sections"][current_section].append(line)

    return data

def markdown_to_reportlab_html(text: str) -> str:
    """Convert Markdown bold **text** to ReportLab <b>text</b> tags."""
    # Convert **bold** -> <b>bold</b>
    text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
    # Convert *italic* -> <i>italic</i>
    text = re.sub(r"\*(.*?)\*", r"<i>\1</i>", text)
    return text

def render_pdf_resume(raw_resume_path: Path, output_pdf_path: Path) -> Path:
    """Render a clean, ATS-compliant PDF resume from raw_resume.txt."""
    if not raw_resume_path.exists():
        raise FileNotFoundError(f"Raw resume file not found: {raw_resume_path}")

    output_pdf_path.parent.mkdir(parents=True, exist_ok=True)
    raw_content = raw_resume_path.read_text(encoding="utf-8")
    parsed = parse_raw_resume(raw_content)

    doc = SimpleDocTemplate(
        str(output_pdf_path),
        pagesize=letter,
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
    )

    styles = getSampleStyleSheet()

    # Custom typography styles
    name_style = ParagraphStyle(
        "ResumeName",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1A202C"),
        alignment=0,
    )
    title_style = ParagraphStyle(
        "ResumeTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#2B6CB0"),
        alignment=0,
    )
    contact_style = ParagraphStyle(
        "ResumeContact",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#4A5568"),
        alignment=0,
    )
    section_heading_style = ParagraphStyle(
        "ResumeSectionHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1A202C"),
        spaceBefore=8,
        spaceAfter=3,
    )
    body_style = ParagraphStyle(
        "ResumeBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#2D3748"),
        spaceBefore=2,
        spaceAfter=2,
    )

    story = []

    # Header: Name, Title, Contact
    story.append(Paragraph(markdown_to_reportlab_html(parsed["name"]), name_style))
    if parsed["title"]:
        story.append(Paragraph(markdown_to_reportlab_html(parsed["title"]), title_style))
    if parsed["contact"]:
        story.append(Paragraph(markdown_to_reportlab_html(parsed["contact"]), contact_style))
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2B6CB0"), spaceAfter=8))

    # Sections
    for section_name, section_lines in parsed["sections"].items():
        if section_name == "Header":
            continue

        story.append(Paragraph(section_name.upper(), section_heading_style))
        story.append(HRFlowable(width="100%", thickness=0.75, color=colors.HexColor("#CBD5E0"), spaceAfter=4))

        for line in section_lines:
            if not line:
                continue
            html_line = markdown_to_reportlab_html(line)
            story.append(Paragraph(html_line, body_style))

        story.append(Spacer(1, 6))

    doc.build(story)
    return output_pdf_path
