"""
src/agents/pdf_typesetter.py — ATS Document & PDF Typesetting Subagent.

Wraps and coordinates existing ReportLab PDF rendering, margin constraints (0.55"),
KeepTogether job blocks, and 2-page strict budget.
"""

import logging
from pathlib import Path
from typing import List, Optional

from src.generators.models import ResumeData
from src.generators.pdf_renderer import render_pdf_resume
from src.generators.text_formatter import format_tailored_markdown

log = logging.getLogger(__name__)


class PDFTypesetterAgent:
    """Specialized Subagent for ReportLab PDF compilation and raw text formatting."""

    def __init__(self):
        pass

    def render(
        self,
        resume_data: ResumeData,
        target_pdf_path: Path,
        target_pages: int = 2,
        keywords: Optional[List[str]] = None,
    ) -> Path:
        """Format resume data into ATS markdown and compile into 2-page PDF."""
        target_pdf_path = Path(target_pdf_path)
        target_pdf_path.parent.mkdir(parents=True, exist_ok=True)

        # Write raw resume markdown file in same directory
        raw_text_path = target_pdf_path.parent / "raw_resume.txt"
        markdown_content = format_tailored_markdown(resume_data, keywords=keywords or [])
        raw_text_path.write_text(markdown_content, encoding="utf-8")

        # Compile ATS-compliant PDF using existing verified renderer
        rendered_pdf = render_pdf_resume(
            raw_resume_source=raw_text_path,
            output_pdf_path=target_pdf_path,
            target_pages=target_pages,
            keywords=keywords or [],
        )

        return Path(rendered_pdf)
