"""
resume_generator.py — Tailored raw resume content generator adhering to generic, candidate-agnostic resume rules.

Orchestrates domain summary selection, LLM tailoring with GraphRAG context, ATS bolding,
and ReportLab PDF generation. Modularized to adhere to Single Responsibility Principle (SRP).
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from src.config import MASTER_RESUME_PATH, OUTPUT_DIR_PATH
from src.llm.service import call_llm_safe as _call_llm_safe

from .ats_matcher import extract_ats_keywords
from .constants import (
    DEFAULT_CANDIDATE_NAME,
    DEFAULT_CANDIDATE_TITLE,
    RAW_RESUME_FILENAME,
)
from .domain_matcher import (
    DOMAIN_KEYWORDS,
    _DEFAULT_DOMAIN_KEYWORDS,
    _load_domain_keywords,
    select_tailored_summary,
)
from .models import JobEntry, ResumeData
from .pdf_renderer import render_pdf_resume
from .prompt_builder import (
    BULLETS_SYSTEM_PROMPT,
    METRIC_PATTERN,
    STRONG_ACTION_VERBS,
    SUMMARY_SYSTEM_PROMPT,
    build_single_call_prompt,
    extract_gap_framing,
    extract_top_metrics,
    get_graphrag_context,
    parse_single_call_response,
)
from .resume_parser import (
    clean_em_dashes,
    create_job_entry,
    extract_summary_variants,
    parse_job_heading_components,
    parse_master_resume,
    parse_resume_markdown,
)
from .text_formatter import (
    _can_bold_keyword,
    bold_keywords,
    format_tailored_markdown,
    reorder_skills_by_relevance,
    score_and_select_bullets,
)

log = logging.getLogger(__name__)


# ── Factory Helpers ─────────────────────────────────────────────────────────

def _default_resume_data() -> ResumeData:
    """Return a baseline fallback ResumeData when MASTER_RESUME.txt is unavailable."""
    return ResumeData(
        name=DEFAULT_CANDIDATE_NAME,
        title=DEFAULT_CANDIDATE_TITLE,
        summary=f"{DEFAULT_CANDIDATE_TITLE} with experience building high-throughput software applications.",
        jobs=[create_job_entry("Software Engineer | Tech Corp | Remote | Jan 2023 - Present", ["Built scalable microservices."])],
        skills=["Backend & APIs: C#, Python, Cloud"],
        certifications=["Cloud Certification"],
        education=["B.S. in Computer Science"]
    )


def get_output_dir(company_name: str, base_output_dir: Optional[Path] = None) -> Path:
    """Return output directory: output/<MM-DD-YYYY>/<company_name>/."""
    if base_output_dir is None:
        base_output_dir = OUTPUT_DIR_PATH

    date_str = datetime.now().strftime("%m-%d-%Y")
    clean_company = re.sub(r"[^A-Za-z0-9_-]", "_", company_name.strip())
    target_dir = base_output_dir / date_str / clean_company
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except (OSError, PermissionError):
        import tempfile
        base_output_dir = Path(tempfile.gettempdir()) / "output"
        target_dir = base_output_dir / date_str / clean_company
        target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir


# ── LLM-Driven Tailoring Orchestration ──────────────────────────────────────

def tailor_resume_with_llm_single_call(
    parsed: ResumeData,
    company_name: str,
    jd_text: str,
    graphrag_context: str,
    gap_framing: str,
    top_metrics: str,
) -> ResumeData:
    """Execute single combined LLM call to rewrite summary and experience bullets."""
    prompt, jobs_with_bullets = build_single_call_prompt(
        parsed, company_name, jd_text, graphrag_context, gap_framing, top_metrics
    )

    from src.gateway import ALIBABA_RESUME_MODEL
    llm_response = _call_llm_safe(
        prompt,
        SUMMARY_SYSTEM_PROMPT,
        timeout=300,
        model=ALIBABA_RESUME_MODEL,
    ).strip()

    if not llm_response:
        return parsed

    return parse_single_call_response(llm_response, parsed, jobs_with_bullets)


def llm_tailor_resume(
    parsed: ResumeData,
    master_content: str,
    company_name: str,
    jd_text: str,
    keywords: List[str],
) -> ResumeData:
    """Produce a genuinely JD-customized resume narrative using GraphRAG context."""
    graphrag_context = get_graphrag_context(jd_text, keywords)
    gap_framing = extract_gap_framing(master_content, jd_text)
    top_metrics = extract_top_metrics(parsed)

    return tailor_resume_with_llm_single_call(
        parsed, company_name, jd_text, graphrag_context, gap_framing, top_metrics
    )


# ── Public Generation APIs ──────────────────────────────────────────────────

def generate_raw_resume(company_name: str, jd_text: str, base_output_dir: Optional[Path] = None, target_pages: int = 2) -> Path:
    """Generate LLM-tailored raw_resume.txt per-JD."""
    out_dir = get_output_dir(company_name, base_output_dir=base_output_dir)
    raw_resume_path = out_dir / RAW_RESUME_FILENAME

    keywords = extract_ats_keywords(jd_text)

    master_path = MASTER_RESUME_PATH
    if master_path.exists():
        master_content = master_path.read_text(encoding="utf-8")
        parsed = parse_resume_markdown(master_content)
        tailored_summary = select_tailored_summary(master_content, keywords, company_name, jd_text=jd_text)
        if tailored_summary:
            parsed.summary = tailored_summary
        parsed = llm_tailor_resume(parsed, master_content, company_name, jd_text, keywords)
    else:
        parsed = _default_resume_data()

    tailored_text = format_tailored_markdown(parsed, keywords)
    raw_resume_path.write_text(tailored_text, encoding="utf-8")
    return raw_resume_path


def generate_raw_resume_stepwise(company_name: str, jd_text: str, base_output_dir: Optional[Path] = None, target_pages: int = 2):
    """Generate LLM-tailored raw_resume.txt and PDF resume stepwise, yielding progress."""
    out_dir = get_output_dir(company_name, base_output_dir=base_output_dir)
    raw_resume_path = out_dir / RAW_RESUME_FILENAME
    pdf_path = out_dir / "Prasad_Rane_Resume.pdf"

    # Step 1: extracting_keywords (8%)
    yield ("extracting_keywords", "Extracting ATS keywords", 8, "Extracting ATS keywords from job description...")
    keywords = extract_ats_keywords(jd_text)

    # Step 2: loading_master (15%)
    yield ("loading_master", "Loading master resume", 15, "Reading and parsing MASTER_RESUME.txt...")
    master_path = MASTER_RESUME_PATH
    if master_path.exists():
        master_content = master_path.read_text(encoding="utf-8")
        parsed = parse_resume_markdown(master_content)
    else:
        master_content = ""
        parsed = _default_resume_data()

    # Step 3: selecting_summary (25%)
    yield ("selecting_summary", "Selecting best summary variant", 25, "Selecting best matching executive summary variant...")
    if master_content:
        tailored_summary = select_tailored_summary(master_content, keywords, company_name, jd_text=jd_text)
        if tailored_summary:
            parsed.summary = tailored_summary

    # Step 4: tailoring_summary (38%)
    yield ("tailoring_summary", "LLM tailoring summary", 38, "LLM tailoring of executive summary to match target role...")
    if master_content:
        parsed = llm_tailor_resume(parsed, master_content, company_name, jd_text, keywords)

    # Step 5: tailoring_bullets (55%)
    yield ("tailoring_bullets", "LLM tailoring experience bullets", 55, "LLM tailoring of experience bullets per job...")

    # Step 6: formatting (72%)
    yield ("formatting", "Formatting & bold marking", 72, "Formatting tailored markdown and marking bold keywords...")
    tailored_text = format_tailored_markdown(parsed, keywords)
    raw_resume_path.write_text(tailored_text, encoding="utf-8")

    # Step 7: rendering_pdf (88%)
    yield ("rendering_pdf", "Rendering PDF", 88, f"Rendering {target_pages}-page PDF resume using ReportLab...")
    render_pdf_resume(raw_resume_path, pdf_path, target_pages=target_pages, keywords=keywords)

    # Step 8: complete (100%)
    yield (
        "complete",
        "Done",
        100,
        {
            "raw_resume_path": str(raw_resume_path),
            "raw_resume": tailored_text,
            "pdf_path": str(pdf_path)
        }
    )


def generate_tailored_resume(
    company_name: str,
    jd_text: str,
    base_output_dir: Optional[Path] = None,
    target_pages: int = 2,
) -> dict:
    """High-level helper returning dict with raw_resume string, paths, and output_dir."""
    out_dir = get_output_dir(company_name, base_output_dir=base_output_dir)
    raw_path = generate_raw_resume(company_name, jd_text, base_output_dir=base_output_dir, target_pages=target_pages)
    pdf_path = out_dir / "Prasad_Rane_Resume.pdf"
    keywords = extract_ats_keywords(jd_text)
    try:
        render_pdf_resume(raw_path, pdf_path, target_pages=target_pages, keywords=keywords)
    except Exception as err:
        log.warning("PDF rendering encountered error: %s", err)

    raw_text = raw_path.read_text(encoding="utf-8") if raw_path.exists() else ""
    return {
        "raw_resume_path": str(raw_path),
        "raw_resume": raw_text,
        "pdf_path": str(pdf_path) if pdf_path.exists() else None,
        "output_dir": str(out_dir),
    }
