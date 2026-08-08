"""
resume_generator.py — Tailored raw resume content generator adhering to exact resume generation rules.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

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
    """Replace em-dashes in prose text while preserving hyphens in dates and compound words."""
    if not text:
        return ""
    # Preserve date ranges (e.g. Jan 2023 – Jul 2025 -> Jan 2023 - Jul 2025)
    text = re.sub(r"(\b[A-Za-z]{3}\s+\d{4})\s+[—–-]\s+([A-Za-z]{3}\s+\d{4}|\bPresent\b)", r"\1 - \2", text)
    # Replace em-dashes in prose with period
    text = text.replace("—", ". ").replace(" – ", ". ")
    text = re.sub(r"\s+\.\s+", ". ", text)
    return text.strip()

def bold_keywords(text: str, keywords: List[str], max_bold_phrases: int = 3, max_bold_ratio: float = 0.20) -> str:
    """Highlight job description keywords judiciously (max 2-3 phrases, <20% bolded text total)."""
    if not text or not keywords:
        return clean_em_dashes(text)

    text = clean_em_dashes(text)
    
    # Calculate current bold character count if text already contains bolding
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
            if (new_bold_chars / total_chars) <= (max_bold_ratio + 0.05):  # Slight margin for multi-word
                text = pattern.sub(r"**\1**", text, count=1)
                current_bold_chars = new_bold_chars
                bold_count += 1

    return text

def parse_master_resume(content: str) -> Dict[str, Any]:
    """Parse raw master resume into structured canonical sections."""
    lines = [clean_em_dashes(l) for l in content.split("\n")]
    sections: Dict[str, List[str]] = {
        "SUMMARY": [],
        "EXPERIENCE": [],
        "SKILLS": [],
        "CERTIFICATIONS": [],
        "EDUCATION": []
    }
    
    current_sec = "SUMMARY"
    current_job_header = None
    current_job_bullets = []

    for line in lines:
        if not line:
            continue
        if line.startswith("# ") and "MASTER RESUME" in line.upper():
            continue
        if line.startswith("## "):
            sec_upper = line.upper()
            if "SUMMARY" in sec_upper or "PROFILES" in sec_upper:
                current_sec = "SUMMARY"
            elif "EXPERIENCE" in sec_upper or "BULLET" in sec_upper:
                current_sec = "EXPERIENCE"
            elif "SKILL" in sec_upper:
                current_sec = "SKILLS"
            elif "CERTIF" in sec_upper:
                current_sec = "CERTIFICATIONS"
            elif "EDUCAT" in sec_upper:
                current_sec = "EDUCATION"
            elif "GAP-FRAMING" in sec_upper:
                current_sec = "SKIP"
            continue

        if current_sec == "SKIP":
            continue

        if current_sec == "SUMMARY":
            if line.startswith("### Canonical Summary"):
                continue
            if line.startswith("### Domain-Specific"):
                current_sec = "SKIP_SUMMARY_VARIANTS"
                continue
            if line.startswith("📍") or line.startswith("**Prasad Rane**") or line.startswith(">") or line.startswith("**Work Authorization:**"):
                continue
            sections["SUMMARY"].append(line)

        elif current_sec == "SKIP_SUMMARY_VARIANTS":
            continue

        elif current_sec == "EXPERIENCE":
            if line.startswith("### "):
                if current_job_header:
                    sections["EXPERIENCE"].append((current_job_header, current_job_bullets))
                current_job_header = line[4:].strip()
                current_job_bullets = []
            elif line.startswith("#### "):
                # Story title header -> skip or add clean context
                continue
            elif line.startswith("- ") or line.startswith("* "):
                current_job_bullets.append(line[2:].strip())

        elif current_sec == "SKILLS":
            if line.startswith("- "):
                sections["SKILLS"].append(line[2:].strip())

        elif current_sec == "CERTIFICATIONS":
            if line.startswith("- "):
                sections["CERTIFICATIONS"].append(line[2:].strip())

        elif current_sec == "EDUCATION":
            if line.startswith("- "):
                # Strip graduation year e.g. (2019) or (2013)
                clean_edu = re.sub(r"\s*\(\d{4}\)", "", line[2:].strip())
                sections["EDUCATION"].append(clean_edu)

    if current_job_header:
        sections["EXPERIENCE"].append((current_job_header, current_job_bullets))

    return sections

def generate_raw_resume(company_name: str, jd_text: str, base_output_dir: Optional[Path] = None) -> Path:
    """Generate tailored raw_resume.txt adhering to exact ATS nomenclature and section order."""
    out_dir = get_output_dir(company_name, base_output_dir=base_output_dir)
    raw_resume_path = out_dir / "raw_resume.txt"

    keywords = extract_ats_keywords(jd_text)

    # Read base MASTER_RESUME.txt if available
    master_path = ROOT_DIR / "input" / "MASTER_RESUME.txt"
    if master_path.exists():
        master_content = master_path.read_text(encoding="utf-8")
        parsed = parse_master_resume(master_content)
    else:
        parsed = {
            "SUMMARY": ["Senior Software Engineer with 10+ years of experience building high-throughput systems."],
            "EXPERIENCE": [
                ("Software Engineer | Rocket Mortgage | Lake Bluff, IL | Jan 2023 - Jul 2025", ["Built Python and AWS microservices."])
            ],
            "SKILLS": ["Backend & APIs: C#, .NET Core, Python, AWS, Docker"],
            "CERTIFICATIONS": ["AWS Certified Cloud Practitioner - Amazon Web Services | Issued: Apr 2026 | Expires: Apr 2029"],
            "EDUCATION": ["M.S. in Information Systems - University of Cincinnati", "B.E. in Electronics & Telecommunication - University of Pune"]
        }

    # Format document in strict section order
    out_lines = [
        "# Prasad Rane",
        "**Title:** Senior Software Engineer",
        "**Contact:** Lake Bluff, IL | 513-967-9423 | emailprasadrane@gmail.com | linkedin.com/in/rane-prasad | prasadrane.vercel.app",
        ""
    ]

    # 1. SUMMARY
    out_lines.append("## SUMMARY")
    sum_text = " ".join(parsed["SUMMARY"])
    out_lines.append(bold_keywords(sum_text, keywords, max_bold_phrases=3, max_bold_ratio=0.15))
    out_lines.append("")

    # 2. EXPERIENCE (Filter top bullets per job to fit 2-page page budget)
    out_lines.append("## EXPERIENCE")
    for job_heading, bullets in parsed["EXPERIENCE"]:
        clean_heading = clean_em_dashes(job_heading)
        out_lines.append(f"### {clean_heading}")
        # Limit to top 3-4 bullets per company role to enforce 2-page cap
        selected_bullets = bullets[:4] if "Rocket Mortgage" in job_heading else bullets[:3]
        for b in selected_bullets:
            bolded_bullet = bold_keywords(b, keywords, max_bold_phrases=3, max_bold_ratio=0.20)
            out_lines.append(f"- {bolded_bullet}")
        out_lines.append("")

    # 3. SKILLS
    out_lines.append("## SKILLS")
    for sk in parsed["SKILLS"]:
        out_lines.append(f"- {clean_em_dashes(sk)}")
    out_lines.append("")

    # 4. CERTIFICATIONS
    out_lines.append("## CERTIFICATIONS")
    for cert in parsed["CERTIFICATIONS"]:
        out_lines.append(f"- {clean_em_dashes(cert)}")
    out_lines.append("")

    # 5. EDUCATION
    out_lines.append("## EDUCATION")
    for edu in parsed["EDUCATION"]:
        # Ensure graduation years are stripped
        clean_edu = re.sub(r"\s*\(\d{4}\)", "", clean_em_dashes(edu))
        out_lines.append(f"- {clean_edu}")

    tailored_text = "\n".join(out_lines)
    raw_resume_path.write_text(tailored_text, encoding="utf-8")
    return raw_resume_path
