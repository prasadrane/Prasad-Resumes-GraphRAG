"""
resume_parser.py — Markdown resume parsing into the ResumeData Pydantic model.

Extracted from resume_generator.py so that pdf_renderer.py can parse resumes
without importing the generator (breaking the generator <-> renderer import
cycle). Parsing only — no LLM, no tailoring, no I/O.
"""

import re
from typing import Dict, List

from .constants import (
    DEFAULT_CANDIDATE_NAME,
    DEFAULT_CANDIDATE_TITLE,
    MARKDOWN_BULLET_PREFIX,
    MARKDOWN_H1_PREFIX,
    MARKDOWN_H2_PREFIX,
    MARKDOWN_H3_PREFIX,
    MARKDOWN_H4_PREFIX,
    SECTION_CERTIFICATIONS,
    SECTION_EDUCATION,
    SECTION_EXPERIENCE,
    SECTION_SKILLS,
    SECTION_SKIP,
    SECTION_SKIP_SUMMARY_VARIANTS,
    SECTION_SUMMARY,
)
from .models import JobEntry, ResumeData

def clean_em_dashes(text: str) -> str:
    """Replace em-dashes in prose text while preserving hyphens in dates and compound words."""
    if not text:
        return ""
    text = re.sub(r"(\b[A-Za-z]{3}\s+\d{4})\s+[—–-]\s+([A-Za-z]{3}\s+\d{4}|\bPresent\b)", r"\1 - \2", text)
    text = text.replace("—", ". ").replace(" – ", ". ")
    text = re.sub(r"\s+\.\s+", ". ", text)
    return text.strip()

def clean_link_url(text: str) -> str:
    """Extract clean URL from markdown link [Text](url) or return text as is."""
    match = re.search(r"\[.*?\]\((.*?)\)", text)
    if match:
        return match.group(1).strip()
    return text.strip()

def parse_job_heading_components(heading_str: str) -> Dict[str, str]:
    """Parse single-line or multi-line job heading into title, company, location, dates dynamically."""
    cleaned = heading_str.replace("**", "").replace("*", "").replace("📍", "").replace("🗓️", "").strip()

    if "|" in cleaned:
        parts = [p.strip() for p in cleaned.split("|") if p.strip()]
        return {
            "title": parts[0] if len(parts) > 0 else "",
            "company": parts[1] if len(parts) > 1 else "",
            "location": parts[2] if len(parts) > 2 else "",
            "dates": parts[3] if len(parts) > 3 else ""
        }

    title = ""
    company = ""

    match_dash = re.split(r"\s*[—–-]\s*", cleaned, maxsplit=1)
    if len(match_dash) == 2:
        title = match_dash[0].strip()
        company = match_dash[1].strip()
    else:
        title = cleaned

    return {
        "title": title,
        "company": company,
        "location": "",
        "dates": ""
    }

def create_job_entry(heading: str, bullets: List[str]) -> JobEntry:
    """Helper to instantiate JobEntry with parsed component fields."""
    parsed_comp = parse_job_heading_components(heading)
    return JobEntry(
        heading=heading,
        title=parsed_comp["title"],
        company=parsed_comp["company"],
        location=parsed_comp["location"],
        dates=parsed_comp["dates"],
        bullets=bullets,
    )

def _parse_contact_line(contact_str: str, data: ResumeData) -> None:
    """Parse contact header line into structured ResumeData contact fields."""
    raw_parts = [p.strip() for p in contact_str.split("|") if p.strip()]
    parts = []
    for p in raw_parts:
        cleaned_p = re.sub(r"[📍📞✉️🌐💻📱📧🏠]", "", p).strip()
        if cleaned_p:
            parts.append(cleaned_p)

    if len(parts) >= 1: data.contact_location = parts[0]
    if len(parts) >= 2: data.contact_phone = parts[1]
    if len(parts) >= 3: data.contact_email = parts[2]
    if len(parts) >= 4: data.contact_linkedin = clean_link_url(parts[3])
    if len(parts) >= 5: data.contact_portfolio = clean_link_url(parts[4])

def extract_summary_variants(content: str) -> Dict[str, str]:
    """Extract canonical summary and domain variant summaries from MASTER_RESUME text."""
    variants = {}
    lines = content.split("\n")
    current_key = "Canonical"
    buffer = []

    for line in lines:
        l = line.strip()
        if l.startswith("### Canonical Summary"):
            if buffer and current_key:
                variants[current_key] = " ".join(buffer).strip()
            current_key = "Canonical"
            buffer = []
        elif l.startswith("### Domain-Specific Summary Variants"):
            if buffer and current_key:
                variants[current_key] = " ".join(buffer).strip()
            current_key = None
            buffer = []
        elif current_key == "Canonical" and l and not l.startswith("#") and not l.startswith(">"):
            buffer.append(l)
        elif l.startswith("- **") and "**: " in l:
            match = re.match(r"^-\s*\*\*(.*?)\*\*:\s*(.*)", l)
            if match:
                variant_name = match.group(1).strip()
                variant_text = match.group(2).strip()
                variants[variant_name] = variant_text

    if buffer and current_key:
        variants[current_key] = " ".join(buffer).strip()

    return variants


# ── Resume Markdown Parser (Updated for Story Title Tracking) ─────────────────

def parse_resume_markdown(content: str) -> ResumeData:
    """Unified Markdown resume parser building a generic ResumeData Pydantic model.
    Now captures story titles (#### Story N — Title) into bullet_stories for
    story-level context in LLM prompts and semantic bullet scoring."""
    raw_lines = content.split("\n")
    data = ResumeData()

    current_sec = SECTION_SUMMARY
    current_job_header = None
    current_job_bullets = []
    current_bullet_stories = []
    current_story_title = ""
    summary_lines = []

    for raw_line in raw_lines:
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith(MARKDOWN_H1_PREFIX):
            header_text = line[len(MARKDOWN_H1_PREFIX):].strip()
            header_text = re.sub(r"(?i)\s*[\.—–|-]*\s*MASTER RESUME.*$", "", header_text).strip()
            name_match = re.split(r"\s*[\.—–|-]\s*", header_text)[0].strip()
            if name_match:
                data.name = name_match
            continue

        if line.startswith("**Title:**"):
            data.title = line.replace("**Title:**", "").strip()
            continue

        if line.startswith("**Contact:**") or ((current_sec == SECTION_SUMMARY) and ("✉️" in line or "📞" in line or (line.startswith("📍") and "email" in line.lower()))):
            contact_str = line.replace("**Contact:**", "").strip()
            _parse_contact_line(contact_str, data)
            continue

        if line.startswith(MARKDOWN_H2_PREFIX):
            sec_upper = line[len(MARKDOWN_H2_PREFIX):].strip().upper()
            if SECTION_SUMMARY in sec_upper or "PROFILES" in sec_upper:
                current_sec = SECTION_SUMMARY
            elif SECTION_EXPERIENCE in sec_upper or "BULLET" in sec_upper:
                current_sec = SECTION_EXPERIENCE
            elif "SKILL" in sec_upper:
                current_sec = SECTION_SKILLS
            elif "CERTIF" in sec_upper:
                current_sec = SECTION_CERTIFICATIONS
            elif "EDUCAT" in sec_upper:
                current_sec = SECTION_EDUCATION
            elif "GAP-FRAMING" in sec_upper:
                current_sec = SECTION_SKIP
            continue

        if current_sec == SECTION_SKIP or current_sec == SECTION_SKIP_SUMMARY_VARIANTS:
            continue

        if current_sec == SECTION_SUMMARY:
            if line.startswith("### Canonical Summary"):
                continue
            if line.startswith("### Domain-Specific"):
                current_sec = SECTION_SKIP_SUMMARY_VARIANTS
                continue
            if line.startswith(">") or line.startswith("**Work Authorization:**"):
                if line.startswith("**") and not data.name:
                    bold_name = re.findall(r"\*\*(.*?)\*\*", line)
                    if bold_name:
                        data.name = bold_name[0]
                continue
            if (line.startswith("**") or line == data.name) and (data.name.lower() in line.lower() or "master resume" in line.lower()):
                continue
            summary_lines.append(clean_em_dashes(line))

        elif current_sec == SECTION_EXPERIENCE:
            if line.startswith(MARKDOWN_H3_PREFIX):
                # Flush previous job entry
                if current_job_header:
                    job = create_job_entry(current_job_header, current_job_bullets)
                    job.bullet_stories = current_bullet_stories[:]
                    data.jobs.append(job)
                current_job_header = line[len(MARKDOWN_H3_PREFIX):].strip()
                current_job_bullets = []
                current_bullet_stories = []
                current_story_title = ""
            elif line.startswith("📍") or line.startswith("🗓️"):
                sub_clean = line.replace("**", "").replace("*", "").replace("📍", "").replace("🗓️", "").strip()
                parts = [p.strip() for p in sub_clean.split("|") if p.strip()]
                loc_part = ""
                dates_part = ""
                for p in parts:
                    if re.search(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|\d{4}|Present)\b", p, re.IGNORECASE):
                        dates_part = p
                    else:
                        loc_part = p
                if current_job_header:
                    comp = parse_job_heading_components(current_job_header)
                    t = comp["title"]
                    c = comp["company"]
                    l = loc_part or comp["location"]
                    d = dates_part or comp["dates"]
                    current_job_header = f"{t} | {c} | {l} | {d}"
            elif line.startswith(MARKDOWN_H4_PREFIX):
                # Capture story titles like "#### Story 1 — Observability & Fannie Mae Integration"
                h4_text = line[len(MARKDOWN_H4_PREFIX):].strip()
                story_match = re.sub(r"^\*?\*?Story\s*\d+\s*[—–-]\s*", "", h4_text, flags=re.IGNORECASE).strip()
                if story_match:
                    current_story_title = story_match.rstrip("*")
            elif line.startswith(MARKDOWN_BULLET_PREFIX) or line.startswith("* "):
                current_job_bullets.append(clean_em_dashes(line[2:].strip()))
                current_bullet_stories.append(current_story_title)

        elif current_sec == SECTION_SKILLS and line.startswith(MARKDOWN_BULLET_PREFIX):
            data.skills.append(clean_em_dashes(line[2:].strip()))

        elif current_sec == SECTION_CERTIFICATIONS and line.startswith(MARKDOWN_BULLET_PREFIX):
            data.certifications.append(clean_em_dashes(line[2:].strip()))

        elif current_sec == SECTION_EDUCATION and line.startswith(MARKDOWN_BULLET_PREFIX):
            data.education.append(clean_em_dashes(line[2:].strip()))

    # Flush final job entry
    if current_job_header:
        job = create_job_entry(current_job_header, current_job_bullets)
        job.bullet_stories = current_bullet_stories[:]
        data.jobs.append(job)

    if not data.name:
        data.name = DEFAULT_CANDIDATE_NAME
    if not data.title:
        data.title = DEFAULT_CANDIDATE_TITLE

    clean_summary = " ".join(summary_lines)
    if data.name:
        clean_summary = re.sub(rf"^(?:\*\*)?{re.escape(data.name)}(?:\*\*)?\s*[\.—–|-]*\s*", "", clean_summary, flags=re.IGNORECASE).strip()
    clean_summary = re.sub(r"^[\.—–|-]+\s*", "", clean_summary).strip()
    data.summary = clean_summary
    return data

parse_master_resume = parse_resume_markdown
