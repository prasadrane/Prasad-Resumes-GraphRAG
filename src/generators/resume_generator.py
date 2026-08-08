"""
resume_generator.py — Tailored raw resume content generator adhering to exact resume generation rules.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .ats_matcher import extract_ats_keywords, match_graphrag_stories
from .constants import (
    CREDLY_AWS_CERT_URL,
    DEFAULT_AWS_CERTIFICATE,
    DEFAULT_CANDIDATE_NAME,
    DEFAULT_CANDIDATE_TITLE,
    DEFAULT_EDUCATION,
    DEFAULT_EMAIL,
    DEFAULT_LINKEDIN_URL,
    DEFAULT_LOCATION,
    DEFAULT_PHONE,
    DEFAULT_PORTFOLIO_URL,
    MARKDOWN_BULLET_PREFIX,
    MARKDOWN_H1_PREFIX,
    MARKDOWN_H2_PREFIX,
    MARKDOWN_H3_PREFIX,
    MARKDOWN_H4_PREFIX,
    RAW_RESUME_FILENAME,
    SECTION_CERTIFICATIONS,
    SECTION_EDUCATION,
    SECTION_EXPERIENCE,
    SECTION_SKILLS,
    SECTION_SKIP,
    SECTION_SKIP_SUMMARY_VARIANTS,
    SECTION_SUMMARY,
)
from .models import JobEntry, ResumeData

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

def get_output_dir(company_name: str, base_output_dir: Optional[Path] = None) -> Path:
    """Return output directory: output/<MM-DD-YYYY>/<company_name>/."""
    if base_output_dir is None:
        base_output_dir = ROOT_DIR / "output"
    
    date_str = datetime.now().strftime("%m-%d-%Y")
    clean_company = re.sub(r"[^A-Za-z0-9_-]", "_", company_name.strip())
    target_dir = base_output_dir / date_str / clean_company
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir

def clean_em_dashes(text: str) -> str:
    """Replace em-dashes in prose text while preserving hyphens in dates and compound words."""
    if not text:
        return ""
    text = re.sub(r"(\b[A-Za-z]{3}\s+\d{4})\s+[—–-]\s+([A-Za-z]{3}\s+\d{4}|\bPresent\b)", r"\1 - \2", text)
    text = text.replace("—", ". ").replace(" – ", ". ")
    text = re.sub(r"\s+\.\s+", ". ", text)
    return text.strip()

def bold_keywords(text: str, keywords: List[str], max_bold_phrases: int = 3, max_bold_ratio: float = 0.20) -> str:
    """Highlight job description keywords judiciously (max 2-3 phrases, <20% bolded text total)."""
    if not text or not keywords:
        return clean_em_dashes(text)

    text = clean_em_dashes(text)
    
    existing_bolds = re.findall(r"\*\*(.*?)\*\*", text)
    current_bold_chars = sum(len(b) for b in existing_bolds)
    total_chars = max(len(text), 1)

    bold_count = len(existing_bolds)

    for kw in sorted(keywords, key=len, reverse=True):
        if not kw.strip() or len(kw.strip()) < 3:
            continue
        if bold_count >= max_bold_phrases:
            break
        if (current_bold_chars / total_chars) >= max_bold_ratio:
            break

        pattern = re.compile(rf"(?<!\*\*)\b({re.escape(kw)})\b(?!\*\*)", re.IGNORECASE)
        match = pattern.search(text)
        if match:
            matched_str = match.group(1)
            new_bold_chars = current_bold_chars + len(matched_str)
            if (new_bold_chars / total_chars) <= (max_bold_ratio + 0.05):
                text = pattern.sub(r"**\1**", text, count=1)
                current_bold_chars = new_bold_chars
                bold_count += 1

    return text

def parse_master_resume(content: str) -> ResumeData:
    """Parse raw master resume into structured ResumeData Pydantic model."""
    lines = [clean_em_dashes(l) for l in content.split("\n")]
    data = ResumeData()
    
    current_sec = SECTION_SUMMARY
    current_job_header = None
    current_job_bullets = []
    summary_lines = []

    for line in lines:
        if not line:
            continue
        if line.startswith(MARKDOWN_H1_PREFIX) and "MASTER RESUME" in line.upper():
            continue
        if line.startswith(MARKDOWN_H2_PREFIX):
            sec_upper = line.upper()
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

        if current_sec == SECTION_SKIP:
            continue

        if current_sec == SECTION_SUMMARY:
            if line.startswith("### Canonical Summary"):
                continue
            if line.startswith("### Domain-Specific"):
                current_sec = SECTION_SKIP_SUMMARY_VARIANTS
                continue
            if line.startswith("📍") or line.startswith(f"**{DEFAULT_CANDIDATE_NAME}**") or line.startswith(">") or line.startswith("**Work Authorization:**"):
                continue
            summary_lines.append(line)

        elif current_sec == SECTION_SKIP_SUMMARY_VARIANTS:
            continue

        elif current_sec == SECTION_EXPERIENCE:
            if line.startswith(MARKDOWN_H3_PREFIX):
                if current_job_header:
                    data.jobs.append(JobEntry(heading=current_job_header, bullets=current_job_bullets))
                current_job_header = line[len(MARKDOWN_H3_PREFIX):].strip()
                current_job_bullets = []
            elif line.startswith(MARKDOWN_H4_PREFIX):
                continue
            elif line.startswith(MARKDOWN_BULLET_PREFIX) or line.startswith("* "):
                current_job_bullets.append(line[2:].strip())

        elif current_sec == SECTION_SKILLS:
            if line.startswith(MARKDOWN_BULLET_PREFIX):
                data.skills.append(line[2:].strip())

        elif current_sec == SECTION_CERTIFICATIONS:
            if line.startswith(MARKDOWN_BULLET_PREFIX):
                data.certifications.append(line[2:].strip())

        elif current_sec == SECTION_EDUCATION:
            if line.startswith(MARKDOWN_BULLET_PREFIX):
                clean_edu = re.sub(r"\s*\(\d{4}\)", "", line[2:].strip())
                data.education.append(clean_edu)

    if current_job_header:
        data.jobs.append(JobEntry(heading=current_job_header, bullets=current_job_bullets))

    data.summary = " ".join(summary_lines)
    return data

def generate_raw_resume(company_name: str, jd_text: str, base_output_dir: Optional[Path] = None) -> Path:
    """Generate tailored raw_resume.txt adhering to exact ATS nomenclature and section order."""
    out_dir = get_output_dir(company_name, base_output_dir=base_output_dir)
    raw_resume_path = out_dir / RAW_RESUME_FILENAME

    keywords = extract_ats_keywords(jd_text)

    # Read base MASTER_RESUME.txt if available
    master_path = ROOT_DIR / "input" / "MASTER_RESUME.txt"
    if master_path.exists():
        master_content = master_path.read_text(encoding="utf-8")
        parsed: ResumeData = parse_master_resume(master_content)
    else:
        parsed = ResumeData(
            summary=f"{DEFAULT_CANDIDATE_TITLE} with 10+ years of experience building high-throughput systems.",
            jobs=[JobEntry(heading=f"Software Engineer | Rocket Mortgage | {DEFAULT_LOCATION} | Jan 2023 - Jul 2025", bullets=["Built Python and AWS microservices."])],
            skills=["Backend & APIs: C#, .NET Core, Python, AWS, Docker"],
            certifications=[DEFAULT_AWS_CERTIFICATE],
            education=DEFAULT_EDUCATION
        )

    # Format document in strict section order
    out_lines = [
        f"{MARKDOWN_H1_PREFIX}{parsed.name}",
        f"**Title:** {parsed.title}",
        f"**Contact:** {parsed.contact_location} | {parsed.contact_phone} | {parsed.contact_email} | linkedin.com/in/rane-prasad | prasadrane.vercel.app",
        ""
    ]

    # 1. SUMMARY
    out_lines.append(f"{MARKDOWN_H2_PREFIX}{SECTION_SUMMARY}")
    out_lines.append(bold_keywords(parsed.summary, keywords, max_bold_phrases=3, max_bold_ratio=0.15))
    out_lines.append("")

    # 2. EXPERIENCE
    out_lines.append(f"{MARKDOWN_H2_PREFIX}{SECTION_EXPERIENCE}")
    for job in parsed.jobs:
        clean_heading = clean_em_dashes(job.heading)
        out_lines.append(f"{MARKDOWN_H3_PREFIX}{clean_heading}")
        selected_bullets = job.bullets[:4] if "Rocket Mortgage" in job.heading else job.bullets[:3]
        for b in selected_bullets:
            bolded_bullet = bold_keywords(b, keywords, max_bold_phrases=3, max_bold_ratio=0.20)
            out_lines.append(f"{MARKDOWN_BULLET_PREFIX}{bolded_bullet}")
        out_lines.append("")

    # 3. SKILLS
    out_lines.append(f"{MARKDOWN_H2_PREFIX}{SECTION_SKILLS}")
    for sk in parsed.skills:
        out_lines.append(f"{MARKDOWN_BULLET_PREFIX}{clean_em_dashes(sk)}")
    out_lines.append("")

    # 4. CERTIFICATIONS
    out_lines.append(f"{MARKDOWN_H2_PREFIX}{SECTION_CERTIFICATIONS}")
    for cert in parsed.certifications:
        out_lines.append(f"{MARKDOWN_BULLET_PREFIX}{clean_em_dashes(cert)}")
    out_lines.append("")

    # 5. EDUCATION
    out_lines.append(f"{MARKDOWN_H2_PREFIX}{SECTION_EDUCATION}")
    for edu in parsed.education:
        clean_edu = re.sub(r"\s*\(\d{4}\)", "", clean_em_dashes(edu))
        out_lines.append(f"{MARKDOWN_BULLET_PREFIX}{clean_edu}")

    tailored_text = "\n".join(out_lines)
    raw_resume_path.write_text(tailored_text, encoding="utf-8")
    return raw_resume_path
