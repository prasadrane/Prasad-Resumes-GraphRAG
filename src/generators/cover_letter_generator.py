"""
cover_letter_generator.py — Tailored Cover Letter Generator.

Synthesizes a structured 1-page cover letter tailored to a target company and job description
using candidate achievements and metrics from the GraphRAG story bank.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from pathlib import Path
from typing import List, Optional

from src.generators.ats_matcher import extract_ats_keywords
from src.query.static_graph_reader import search_static_resume

logger = logging.getLogger(__name__)


@dataclass
class CoverLetterData:
    """Structured cover letter model."""
    candidate_name: str
    company_name: str
    role_title: str
    paragraphs: List[str] = field(default_factory=list)
    sign_off: str = "Sincerely,\n"


class CoverLetterGenerator:
    """
    Generates targeted cover letters from candidate knowledge graph and job descriptions.
    """

    @staticmethod
    def _sanitize(text: str) -> str:
        """Remove em dashes and hyphens per style rule."""
        # Named replacements for readability
        replacements = {
            "offline-first": "offline capable",
            "cross-functional": "collaborative",
            "high-throughput": "high throughput",
            "high-performance": "high performance",
            "real-time": "real time",
            "self-service": "self service",
            "SQL-centric": "SQL focused",
            "sql-centric": "sql focused",
            "data-driven": "data focused",
            "cost-effective": "cost effective",
            "large-scale": "large scale",
            "mission-critical": "critical",
            "enterprise-grade": "enterprise",
            "cloud-native": "cloud native",
            "event-driven": "event driven",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        # Remove em dashes and en dashes
        text = text.replace("—", ", ").replace("–", ", ").replace("--", ", ")
        return text

    def generate(
        self,
        company: str,
        jd_text: str,
        candidate_name: str = "Prasad Rane",
        role_title: str = "Senior Software Engineer",
    ) -> CoverLetterData:
        target_company = company.strip() if company and company.strip() else "Hiring Team"
        raw_keywords = extract_ats_keywords(jd_text, expand_ontology=False)
        seen = set()
        unique_skills = []
        for kw in raw_keywords:
            clean_kw = kw.strip()
            if clean_kw.lower() not in seen and len(clean_kw) > 1:
                seen.add(clean_kw.lower())
                unique_skills.append(clean_kw)

        top_skills = ", ".join(unique_skills[:4]) if unique_skills else "cloud architecture, microservices, and distributed systems"

        p1 = (
            f"I was excited to see the {role_title} opening at {target_company}. "
            f"Over the past decade I have been building cloud platforms and data systems at scale, "
            f"and the work your team is doing really resonates with the kind of problems I enjoy solving."
        )

        p2 = (
            f"I have spent years working with technologies like {top_skills}. "
            f"Most recently at Rocket Mortgage I led the migration of our core underwriter applications "
            f"to AWS ECS Fargate, which cut query latency by 70 percent and let us set up Kafka governance "
            f"standards that five different engineering teams now rely on."
        )

        p3 = (
            f"Before that, at London Computer Systems and EXFO, I spent a lot of time on database performance "
            f"and API reliability. One project I am particularly proud of involved rewriting our reporting queries "
            f"to bring generation time from 45 seconds down to under 3 seconds. I also built an offline capable "
            f"REST sync layer for field instruments that handled hundreds of deployments with zero data loss."
        )

        p4 = (
            f"I would love the chance to talk about how my experience with cloud architecture, streaming systems, "
            f"and backend engineering could help {target_company} continue to grow. Thank you for your time."
        )

        paragraphs = [self._sanitize(p) for p in [p1, p2, p3, p4]]

        return CoverLetterData(
            candidate_name=candidate_name,
            company_name=target_company,
            role_title=role_title,
            paragraphs=paragraphs,
        )

    def render_markdown(self, data: CoverLetterData) -> str:
        """Render cover letter as formatted markdown."""
        lines = [
            f"# Cover Letter for {data.candidate_name}",
            f"**Target Company:** {data.company_name} | **Role:** {data.role_title}\n",
            f"Dear Hiring Team at {data.company_name},\n",
        ]
        for p in data.paragraphs:
            lines.append(f"{p}\n")
        lines.append(f"{data.sign_off}{data.candidate_name}")
        return "\n".join(lines)

    def render_pdf(self, data: CoverLetterData, output_path: Path) -> Path:
        """Render cover letter as a 1-page PDF using ReportLab."""
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.enums import TA_LEFT

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=letter,
            leftMargin=0.75 * inch,
            rightMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
        )

        font_body = "Helvetica"
        font_bold = "Helvetica-Bold"
        color_dark = "#1a1a2e"
        color_body = "#374151"
        color_meta = "#6b7280"

        style_heading = ParagraphStyle(
            "CLHeading", fontName=font_bold, fontSize=14, leading=18,
            textColor=color_dark, alignment=TA_LEFT, spaceAfter=4,
        )
        style_subheading = ParagraphStyle(
            "CLSubheading", fontName=font_body, fontSize=10, leading=13,
            textColor=color_meta, alignment=TA_LEFT, spaceAfter=12,
        )
        style_body = ParagraphStyle(
            "CLBody", fontName=font_body, fontSize=10.5, leading=14.5,
            textColor=color_body, alignment=TA_LEFT, spaceAfter=10,
        )
        style_signoff = ParagraphStyle(
            "CLSignoff", fontName=font_body, fontSize=10.5, leading=14.5,
            textColor=color_body, alignment=TA_LEFT, spaceBefore=12,
        )

        story = []
        story.append(Paragraph(data.candidate_name, style_heading))
        story.append(Paragraph(
            f"{data.company_name} | {data.role_title}", style_subheading
        ))
        story.append(Spacer(1, 8))
        story.append(Paragraph(f"Dear Hiring Team at {data.company_name},", style_body))
        story.append(Spacer(1, 4))

        for p in data.paragraphs:
            safe = p.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            story.append(Paragraph(safe, style_body))

        story.append(Spacer(1, 12))
        for line in data.sign_off.strip().split("\n"):
            story.append(Paragraph(line, style_signoff))

        doc.build(story)
        return output_path
