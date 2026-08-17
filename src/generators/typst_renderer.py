"""
typst_renderer.py — Modern Typst Resume Markup Generator.

Generates high-typography Typst markup adhering to strict margin and 2-page standards.
"""

from __future__ import annotations

from src.generators.models import ResumeData


def render_typst_markup(data: ResumeData) -> str:
    """Generate Typst markup (.typ) from ResumeData model."""
    lines = [
        "#set page(paper: \"us-letter\", margin: (x: 0.45in, top: 0.40in, bottom: 0.40in))",
        "#set text(font: \"Liberation Sans\", size: 10pt)",
        "#set par(justify: true, leading: 0.55em)",
        "",
        f"= {data.name or 'Candidate'}",
        f"*{data.title or ''}* \\",
        f"{data.contact_email or ''} | {data.contact_phone or ''} | {data.contact_location or ''} | {data.contact_linkedin or ''}",
        "",
        "== Professional Summary",
        f"{data.summary or ''}",
        "",
        "== Technical Skills",
    ]

    for skill in data.skills:
        lines.append(f"- {skill}")

    lines.append("")
    lines.append("== Professional Experience")

    for job in data.jobs:
        heading = f"=== {job.title} — *{job.company}* ({job.dates})"
        lines.append(heading)
        for bullet in job.bullets:
            clean_b = bullet.replace("•", "").strip()
            lines.append(f"- {clean_b}")
        lines.append("")

    if data.education:
        lines.append("== Education & Certifications")
        for edu in data.education:
            lines.append(f"- {edu}")

    return "\n".join(lines)
