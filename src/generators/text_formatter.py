"""
text_formatter.py — Markdown formatting, bullet scoring, and ATS keyword bolding.

Formats structured ResumeData into clean Markdown adhering to ATS standards,
bolding ratios (<20%), and bullet length budgets.
"""

import re
from typing import List, Optional

from .constants import (
    BOLD_CAP_PCT,
    MARKDOWN_BULLET_PREFIX,
    MARKDOWN_H1_PREFIX,
    MARKDOWN_H2_PREFIX,
    MARKDOWN_H3_PREFIX,
    MAX_BOLD_PHRASES_PER_BULLET,
    SECTION_CERTIFICATIONS,
    SECTION_EDUCATION,
    SECTION_EXPERIENCE,
    SECTION_PROJECTS,
    SECTION_SKILLS,
    SECTION_SUMMARY,
)
from .models import ResumeData
from .prompt_builder import METRIC_PATTERN, STRONG_ACTION_VERBS
from .resume_parser import clean_em_dashes


def _can_bold_keyword(matched_len: int, current_bold_chars: int, total_chars: int, max_bold_ratio: float) -> bool:
    """Predicate to verify that bolding a keyword does not exceed max bold character ratio."""
    new_ratio = (current_bold_chars + matched_len) / total_chars
    return new_ratio <= (max_bold_ratio + 0.05)


def bold_keywords(
    text: str,
    keywords: List[str],
    max_bold_phrases: int = MAX_BOLD_PHRASES_PER_BULLET,
    max_bold_ratio: float = BOLD_CAP_PCT / 100,
    allow_first_word_bold: bool = False,
) -> str:
    """Highlight job description keywords judiciously (max 2-3 phrases, <20% bolded text total)."""
    if not text:
        return ""

    text = clean_em_dashes(text)
    if not allow_first_word_bold:
        text = re.sub(r"^\s*\*\*([A-Za-z0-9\-\s/]+?)\*\*(\s+)", r"\1\2", text)

    if not keywords:
        return text

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
            if not allow_first_word_bold and match.start() <= 2:
                continue
            matched_str = match.group(1)
            if _can_bold_keyword(len(matched_str), current_bold_chars, total_chars, max_bold_ratio):
                text = pattern.sub(r"**\1**", text, count=1)
                current_bold_chars += len(matched_str)
                bold_count += 1

    if not allow_first_word_bold:
        text = re.sub(r"^\s*\*\*([A-Za-z0-9\-\s/]+?)\*\*(\s+)", r"\1\2", text)

    return text


def score_and_select_bullets(
    bullets: List[str],
    keywords: List[str],
    max_bullets: int,
    bullet_stories: Optional[List[str]] = None,
) -> List[str]:
    """Score and reorder bullets using ATS keywords, quantitative metrics, story relevance, and action verbs."""
    if not bullets:
        return []

    scored = []
    for orig_idx, bullet in enumerate(bullets):
        score = 0
        bullet_upper = bullet.upper()

        # 1. Keyword match (+2 per keyword found in bullet)
        for kw in keywords:
            if kw.strip() and kw.upper() in bullet_upper:
                score += 2

        # 2. Metric bonus (+3 if bullet contains quantitative impact)
        if METRIC_PATTERN.search(bullet):
            score += 3

        # 3. Strong action verb bonus (+1)
        first_word = re.sub(r"\*+", "", bullet.split()[0]).upper() if bullet.split() else ""
        if first_word in STRONG_ACTION_VERBS:
            score += 1

        # 4. Story-title relevance bonus (+2 if story theme matches any JD keyword)
        if bullet_stories and orig_idx < len(bullet_stories) and bullet_stories[orig_idx]:
            story_upper = bullet_stories[orig_idx].upper()
            for kw in keywords:
                if kw.strip() and kw.upper() in story_upper:
                    score += 2
                    break

        scored.append((score, -orig_idx, bullet))

    scored.sort(reverse=True)
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


def format_tailored_markdown(data: ResumeData, keywords: Optional[List[str]] = None) -> str:
    """Format ResumeData Pydantic model into ATS-tailored raw Markdown resume text."""
    if keywords is None:
        keywords = []
    contact_parts = [
        p
        for p in [
            data.contact_location,
            data.contact_phone,
            data.contact_email,
            data.contact_linkedin,
            data.contact_github,
            data.contact_portfolio,
        ]
        if p
    ]
    contact_line = " | ".join(contact_parts)
    out_lines = [
        f"{MARKDOWN_H1_PREFIX}{data.name}",
        f"**Contact:** {contact_line}",
        "",
    ]

    # 1. SUMMARY
    out_lines.append(f"{MARKDOWN_H2_PREFIX}{SECTION_SUMMARY}")
    bolded_summary = bold_keywords(data.summary, keywords, max_bold_phrases=MAX_BOLD_PHRASES_PER_BULLET, max_bold_ratio=0.15)
    out_lines.append(bolded_summary)
    out_lines.append("")

    # 2. EXPERIENCE
    out_lines.append(f"{MARKDOWN_H2_PREFIX}{SECTION_EXPERIENCE}")
    for idx, job in enumerate(data.jobs):
        heading_parts = [p for p in [job.title, job.company, job.location, job.dates] if p]
        clean_heading = " | ".join(heading_parts) or job.heading
        out_lines.append(f"{MARKDOWN_H3_PREFIX}{clean_heading}")
        max_bullets = 7 if idx == 0 else 5
        selected_bullets = score_and_select_bullets(
            job.bullets, keywords, max_bullets, bullet_stories=job.bullet_stories
        )
        for b in selected_bullets:
            bolded_bullet = bold_keywords(b, keywords, max_bold_phrases=MAX_BOLD_PHRASES_PER_BULLET, max_bold_ratio=BOLD_CAP_PCT / 100)
            out_lines.append(f"{MARKDOWN_BULLET_PREFIX}{bolded_bullet}")
        out_lines.append("")

    # 3. PROJECTS
    if data.projects:
        out_lines.append(f"{MARKDOWN_H2_PREFIX}{SECTION_PROJECTS}")
        for idx, proj in enumerate(data.projects):
            heading_parts = [p for p in [proj.title, proj.company, proj.location, proj.dates] if p]
            clean_heading = " | ".join(heading_parts) or proj.heading
            out_lines.append(f"{MARKDOWN_H3_PREFIX}{clean_heading}")
            for b in proj.bullets:
                bolded_bullet = bold_keywords(b, keywords, max_bold_phrases=MAX_BOLD_PHRASES_PER_BULLET, max_bold_ratio=BOLD_CAP_PCT / 100)
                out_lines.append(f"{MARKDOWN_BULLET_PREFIX}{bolded_bullet}")
            out_lines.append("")

    # 4. SKILLS
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
