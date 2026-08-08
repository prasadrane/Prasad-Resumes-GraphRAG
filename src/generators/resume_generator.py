"""
resume_generator.py — Raw resume builder with ATS keyword bolding and date-based output directory structure.
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

def bold_keywords(text: str, keywords: List[str]) -> str:
    """Format matching ATS keywords in **bold** while avoiding double bolding."""
    if not text or not keywords:
        return text

    for kw in sorted(keywords, key=len, reverse=True):
        if not kw.strip():
            continue
        # Pattern to match keyword if not already enclosed in asterisks
        pattern = re.compile(rf"(?<!\*\*)\b({re.escape(kw)})\b(?!\*\*)", re.IGNORECASE)
        text = pattern.sub(r"**\1**", text)

    return text

def generate_raw_resume(company_name: str, jd_text: str, base_output_dir: Optional[Path] = None) -> Path:
    """Generate tailored raw_resume.txt with ATS keywords bolded."""
    out_dir = get_output_dir(company_name, base_output_dir=base_output_dir)
    raw_resume_path = out_dir / "raw_resume.txt"

    keywords = extract_ats_keywords(jd_text)

    # Read base MASTER_RESUME.txt if available
    master_path = ROOT_DIR / "input" / "MASTER_RESUME.txt"
    if master_path.exists():
        base_content = master_path.read_text(encoding="utf-8")
    else:
        base_content = f"# Prasad Rane\n**Title:** Senior Software Engineer\n\n## SUMMARY\nExperienced Software Engineer specializing in cloud architecture and AI systems.\n"

    # Apply bolding to keywords in resume text
    tailored_text = bold_keywords(base_content, keywords)

    # Write raw_resume.txt
    raw_resume_path.write_text(tailored_text, encoding="utf-8")
    return raw_resume_path
