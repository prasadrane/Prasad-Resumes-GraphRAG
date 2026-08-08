"""
resume_generator.py — Tailored raw resume content generator adhering to exact resume generation rules.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .ats_matcher import extract_ats_keywords, match_graphrag_stories

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
    """Remove em dashes and replace with periods or colons per resume rules."""
    text = text.replace("—", ". ").replace(" – ", ". ")
    return text

def bold_keywords(text: str, keywords: List[str], max_bold_phrases: int = 3) -> str:
    """Highlight job description keywords judiciously (max 2-3 phrases, <20% bolded text total)."""
    if not text or not keywords:
        return clean_em_dashes(text)

    text = clean_em_dashes(text)
    bold_count = 0

    for kw in sorted(keywords, key=len, reverse=True):
        if not kw.strip() or len(kw.strip()) < 3:
            continue
        if bold_count >= max_bold_phrases:
            break
        pattern = re.compile(rf"(?<!\*\*)\b({re.escape(kw)})\b(?!\*\*)", re.IGNORECASE)
        new_text, count = pattern.subn(r"**\1**", text, count=1)
        if count > 0:
            text = new_text
            bold_count += count

    return text

def generate_raw_resume(company_name: str, jd_text: str, base_output_dir: Optional[Path] = None) -> Path:
    """Generate tailored raw_resume.txt adhering to exact ATS nomenclature and section order."""
    out_dir = get_output_dir(company_name, base_output_dir=base_output_dir)
    raw_resume_path = out_dir / "raw_resume.txt"

    keywords = extract_ats_keywords(jd_text)

    # Read base MASTER_RESUME.txt if available
    master_path = ROOT_DIR / "input" / "MASTER_RESUME.txt"
    if master_path.exists():
        base_content = master_path.read_text(encoding="utf-8")
    else:
        base_content = f"# Prasad Rane\n**Title:** Senior Software Engineer\n\n## SUMMARY\nExperienced Software Engineer specializing in cloud architecture and AI systems.\n"

    # Tailor summary and bullet text with exact ATS keyword nomenclature
    lines = base_content.split("\n")
    processed_lines = []

    for line in lines:
        if line.startswith("- ") or line.startswith("* "):
            bullet_text = line[2:].strip()
            bolded_bullet = bold_keywords(bullet_text, keywords, max_bold_phrases=3)
            processed_lines.append(f"- {bolded_bullet}")
        else:
            processed_lines.append(clean_em_dashes(line))

    tailored_text = "\n".join(processed_lines)

    # Write raw_resume.txt
    raw_resume_path.write_text(tailored_text, encoding="utf-8")
    return raw_resume_path
