"""
pdf_renderer.py — Rule-based PDF resume generator using ReportLab Platypus, Pydantic models, and pdf_styles.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether, HRFlowable

from .constants import (
    DEFAULT_CANDIDATE_NAME,
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
from .pdf_styles import (
    COLOR_RULE,
    PageCountCanvas,
    create_section_header_flowables,
    format_contact_paragraph,
    format_job_heading,
    get_resume_styles,
    markdown_to_reportlab_html,
)

def parse_job_heading_components(heading_str: str) -> Dict[str, str]:
    """Parse single-line job heading into title, company, location, dates dynamically."""
    cleaned = heading_str.replace("**", "").replace("*", "").replace("📍", "").replace("🗓️", "").strip()
    parts = [p.strip() for p in re.split(r"[|—–]", cleaned) if p.strip()]

    return {
        "title": parts[0] if len(parts) > 0 else "Software Engineer",
        "company": parts[1] if len(parts) > 1 else "",
        "location": parts[2] if len(parts) > 2 else "",
        "dates": parts[3] if len(parts) > 3 else ""
    }

def parse_raw_resume(raw_content: str) -> ResumeData:
    """Parse raw_resume.txt Markdown content generically into ResumeData Pydantic model."""
    lines = [l.strip() for l in raw_content.split("\n") if l.strip()]
    data = ResumeData()

    current_section = None
    current_job: Optional[JobEntry] = None
    summary_lines = []

    for line in lines:
        if line.startswith(MARKDOWN_H1_PREFIX):
            data.name = line[len(MARKDOWN_H1_PREFIX):].strip()
            continue
        elif line.startswith("**Title:**"):
            data.title = line.replace("**Title:**", "").strip()
            continue
        elif line.startswith("**Contact:**"):
            contact_str = line.replace("**Contact:**", "").strip()
            parts = [p.strip() for p in contact_str.split("|") if p.strip()]
            if len(parts) >= 1: data.contact_location = parts[0]
            if len(parts) >= 2: data.contact_phone = parts[1]
            if len(parts) >= 3: data.contact_email = parts[2]
            if len(parts) >= 4: data.contact_linkedin = parts[3]
            if len(parts) >= 5: data.contact_portfolio = parts[4]
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

        elif current_section == SECTION_SKILLS and line.startswith(MARKDOWN_BULLET_PREFIX):
            data.skills.append(line[2:].strip())

        elif current_section == SECTION_CERTIFICATIONS and line.startswith(MARKDOWN_BULLET_PREFIX):
            data.certifications.append(line[2:].strip())

        elif current_section == SECTION_EDUCATION and line.startswith(MARKDOWN_BULLET_PREFIX):
            clean_edu = re.sub(r"\s*\(\d{4}\)", "", line[2:].strip())
            data.education.append(clean_edu)

    if not data.name:
        data.name = DEFAULT_CANDIDATE_NAME

    data.summary = " ".join(summary_lines)
    return data

def render_pdf_resume(raw_resume_path: Path, output_pdf_path: Path) -> Path:
    """Render rule-based ATS compliant PDF resume using ReportLab Platypus, Pydantic models, and pdf_styles."""
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

    styles = get_resume_styles()
    story = []

    # 1. Header: Name & Contact Paragraph
    story.append(Paragraph(parsed.name, styles["name"]))
    contact_html = format_contact_paragraph(parsed)
    if contact_html:
        story.append(Paragraph(contact_html, styles["contact"]))

    # 2. Professional Summary Section
    if parsed.summary:
        story.extend(create_section_header_flowables(SECTION_SUMMARY, styles["sec_header"]))
        sum_html = markdown_to_reportlab_html(parsed.summary)
        story.append(Paragraph(sum_html, styles["summary"]))

    # 3. Experience Section
    if parsed.jobs:
        story.extend(create_section_header_flowables(SECTION_EXPERIENCE, styles["sec_header"]))
        for job in parsed.jobs:
            job_flowables = [Paragraph(format_job_heading(job), styles["job_heading"])]
            for b in job.bullets:
                b_html = markdown_to_reportlab_html(b)
                job_flowables.append(Paragraph(f"• {b_html}", styles["bullet"]))

            job_flowables.append(Spacer(1, 3))
            story.append(KeepTogether(job_flowables))

    # 4. Skills Section
    if parsed.skills:
        skills_flowables = create_section_header_flowables(SECTION_SKILLS, styles["sec_header"])
        for sk in parsed.skills:
            sk_html = markdown_to_reportlab_html(sk)
            skills_flowables.append(Paragraph(sk_html, styles["skill"]))

        story.append(KeepTogether(skills_flowables))

    # 5. Certifications Section
    if parsed.certifications:
        story.extend(create_section_header_flowables(SECTION_CERTIFICATIONS, styles["sec_header"]))
        for cert in parsed.certifications:
            cert_html = markdown_to_reportlab_html(cert)
            story.append(Paragraph(cert_html, styles["cert"]))

    # 6. Education Section
    if parsed.education:
        story.extend(create_section_header_flowables(SECTION_EDUCATION, styles["sec_header"]))
        for edu in parsed.education:
            clean_edu = re.sub(r"\s*\(\d{4}\)", "", edu)
            story.append(Paragraph(markdown_to_reportlab_html(clean_edu), styles["edu"]))

    doc.build(story, canvasmaker=PageCountCanvas)
    return output_pdf_path
