"""
resume_generator.py — Tailored raw resume content generator adhering to generic, candidate-agnostic resume rules.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .ats_matcher import extract_ats_keywords
from .constants import (
    DEFAULT_CANDIDATE_NAME,
    DEFAULT_CANDIDATE_TITLE,
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
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except (OSError, PermissionError):
        import tempfile
        base_output_dir = Path(tempfile.gettempdir()) / "output"
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

def _can_bold_keyword(matched_len: int, current_bold_chars: int, total_chars: int, max_bold_ratio: float) -> bool:
    """Helper predicate to check if bolding a keyword stays under max character ratio."""
    new_ratio = (current_bold_chars + matched_len) / total_chars
    return new_ratio <= (max_bold_ratio + 0.05)

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
        if not kw.strip() or len(kw.strip()) < 2:
            continue
        if bold_count >= max_bold_phrases or (current_bold_chars / total_chars) >= max_bold_ratio:
            break

        pattern = re.compile(rf"(?<!\*\*)\b({re.escape(kw)})\b(?!\*\*)", re.IGNORECASE)
        match = pattern.search(text)
        if match:
            matched_str = match.group(1)
            if _can_bold_keyword(len(matched_str), current_bold_chars, total_chars, max_bold_ratio):
                text = pattern.sub(r"**\1**", text, count=1)
                current_bold_chars += len(matched_str)
                bold_count += 1

    return text

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

def select_tailored_summary(content: str, keywords: List[str], company_name: str) -> str:
    """Select best-matching summary variant based on JD keywords."""
    variants = extract_summary_variants(content)
    if not variants:
        return ""

    best_summary = variants.get("Canonical", "")
    best_score = -1

    for name, summary in variants.items():
        score = 0
        s_upper = summary.upper()
        for kw in keywords:
            if kw.upper() in s_upper:
                score += 1
        if score > best_score:
            best_score = score
            best_summary = summary

    return best_summary

def parse_resume_markdown(content: str) -> ResumeData:
    """Unified Markdown resume parser building a generic ResumeData Pydantic model."""
    raw_lines = content.split("\n")
    data = ResumeData()
    
    current_sec = SECTION_SUMMARY
    current_job_header = None
    current_job_bullets = []
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
                if current_job_header:
                    data.jobs.append(create_job_entry(current_job_header, current_job_bullets))
                current_job_header = line[len(MARKDOWN_H3_PREFIX):].strip()
                current_job_bullets = []
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
                continue
            elif line.startswith(MARKDOWN_BULLET_PREFIX) or line.startswith("* "):
                current_job_bullets.append(clean_em_dashes(line[2:].strip()))

        elif current_sec == SECTION_SKILLS and line.startswith(MARKDOWN_BULLET_PREFIX):
            data.skills.append(clean_em_dashes(line[2:].strip()))

        elif current_sec == SECTION_CERTIFICATIONS and line.startswith(MARKDOWN_BULLET_PREFIX):
            data.certifications.append(clean_em_dashes(line[2:].strip()))

        elif current_sec == SECTION_EDUCATION and line.startswith(MARKDOWN_BULLET_PREFIX):
            data.education.append(clean_em_dashes(line[2:].strip()))

    if current_job_header:
        data.jobs.append(create_job_entry(current_job_header, current_job_bullets))

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

def score_and_select_bullets(bullets: List[str], keywords: List[str], max_bullets: int) -> List[str]:
    """Score and reorder bullets based on ATS keyword occurrences, preserving full bullet counts."""
    if not bullets:
        return []

    scored = []
    for orig_idx, bullet in enumerate(bullets):
        score = 0
        bullet_upper = bullet.upper()
        for kw in keywords:
            if kw.strip() and kw.upper() in bullet_upper:
                score += 2
        scored.append((score, -orig_idx, bullet))

    scored.sort(reverse=True)
    # Take up to max_bullets or all bullets if max_bullets >= len(bullets)
    target_count = min(len(bullets), max_bullets)
    selected_tuples = scored[:target_count]
    return [t[2] for t in selected_tuples]

def reorder_skills_by_relevance(skills: List[str], keywords: List[str]) -> List[str]:
    """Reorder skill categories by keyword relevance without dropping any category."""
    if not skills or not keywords:
        return skills

    scored = []
    for idx, sk in enumerate(skills):
        score = 0
        sk_upper = sk.upper()
        for kw in keywords:
            if kw.strip() and kw.upper() in sk_upper:
                score += 1
        scored.append((score, -idx, sk))

    scored.sort(reverse=True)
    return [t[2] for t in scored]

def format_tailored_markdown(data: ResumeData, keywords: List[str]) -> str:
    """Format ResumeData Pydantic model into ATS-tailored raw Markdown resume text (excluding Title line)."""
    # NOTE: Title line is completely excluded as per instructions!
    out_lines = [
        f"{MARKDOWN_H1_PREFIX}{data.name}",
        f"**Contact:** {data.contact_location} | {data.contact_phone} | {data.contact_email} | {data.contact_linkedin} | {data.contact_portfolio}",
        ""
    ]

    # 1. SUMMARY
    out_lines.append(f"{MARKDOWN_H2_PREFIX}{SECTION_SUMMARY}")
    bolded_summary = bold_keywords(data.summary, keywords, max_bold_phrases=3, max_bold_ratio=0.15)
    out_lines.append(bolded_summary)
    out_lines.append("")

    # 2. EXPERIENCE
    out_lines.append(f"{MARKDOWN_H2_PREFIX}{SECTION_EXPERIENCE}")
    for idx, job in enumerate(data.jobs):
        heading_parts = [p for p in [job.title, job.company, job.location, job.dates] if p]
        clean_heading = " | ".join(heading_parts)
        out_lines.append(f"{MARKDOWN_H3_PREFIX}{clean_heading}")
        # Keep generous bullet budget (7 for primary/recent job, 5 for prior) to preserve length
        max_bullets = 7 if idx == 0 else 5
        selected_bullets = score_and_select_bullets(job.bullets, keywords, max_bullets)
        for b in selected_bullets:
            bolded_bullet = bold_keywords(b, keywords, max_bold_phrases=3, max_bold_ratio=0.20)
            out_lines.append(f"{MARKDOWN_BULLET_PREFIX}{bolded_bullet}")
        out_lines.append("")

    # 3. SKILLS
    out_lines.append(f"{MARKDOWN_H2_PREFIX}{SECTION_SKILLS}")
    ordered_skills = reorder_skills_by_relevance(data.skills, keywords)
    for sk in ordered_skills:
        bolded_sk = bold_keywords(clean_em_dashes(sk), keywords, max_bold_phrases=2, max_bold_ratio=0.25)
        out_lines.append(f"{MARKDOWN_BULLET_PREFIX}{bolded_sk}")
    out_lines.append("")

    # 4. CERTIFICATIONS
    out_lines.append(f"{MARKDOWN_H2_PREFIX}{SECTION_CERTIFICATIONS}")
    for cert in data.certifications:
        out_lines.append(f"{MARKDOWN_BULLET_PREFIX}{clean_em_dashes(cert)}")
    out_lines.append("")

    # 5. EDUCATION
    out_lines.append(f"{MARKDOWN_H2_PREFIX}{SECTION_EDUCATION}")
    for edu in data.education:
        out_lines.append(f"{MARKDOWN_BULLET_PREFIX}{clean_em_dashes(edu)}")

    return "\n".join(out_lines)

def generate_raw_resume(company_name: str, jd_text: str, base_output_dir: Optional[Path] = None) -> Path:
    """Generate tailored raw_resume.txt adhering to exact ATS nomenclature and section order."""
    out_dir = get_output_dir(company_name, base_output_dir=base_output_dir)
    raw_resume_path = out_dir / RAW_RESUME_FILENAME

    keywords = extract_ats_keywords(jd_text)

    # Read base MASTER_RESUME.txt if available
    master_path = ROOT_DIR / "input" / "MASTER_RESUME.txt"
    if master_path.exists():
        master_content = master_path.read_text(encoding="utf-8")
        parsed = parse_resume_markdown(master_content)
        # Select best summary variant dynamically matching JD keywords
        tailored_summary = select_tailored_summary(master_content, keywords, company_name)
        if tailored_summary:
            parsed.summary = tailored_summary
    else:
        parsed = ResumeData(
            name=DEFAULT_CANDIDATE_NAME,
            title=DEFAULT_CANDIDATE_TITLE,
            summary=f"{DEFAULT_CANDIDATE_TITLE} with experience building high-throughput software applications.",
            jobs=[create_job_entry("Software Engineer | Tech Corp | Remote | Jan 2023 - Present", ["Built scalable microservices."])],
            skills=["Backend & APIs: C#, Python, Cloud"],
            certifications=["Cloud Certification"],
            education=["B.S. in Computer Science"]
        )

    tailored_text = format_tailored_markdown(parsed, keywords)
    raw_resume_path.write_text(tailored_text, encoding="utf-8")
    return raw_resume_path
