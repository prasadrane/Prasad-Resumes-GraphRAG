"""
ats_scorer.py — Real-time ATS match scoring, section breakdown, and recommendations engine.

Evaluates resume text against target Job Descriptions, returning:
- Overall match score (0-100%)
- Section-by-section breakdown (Skills, Experience, Summary)
- Matched keywords with frequency & context
- Missing high-priority keywords
- Actionable suggestions to increase match rate
"""

import re
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from .ats_matcher import extract_ats_keywords
from .prompt_builder import METRIC_PATTERN
from .sme_ontology import SMEOntology


class KeywordMatch(BaseModel):
    term: str
    frequency: int = 1
    in_skills: bool = False
    in_experience: bool = False
    in_summary: bool = False


class SectionScores(BaseModel):
    skills: float = 0.0
    experience: float = 0.0
    summary: float = 0.0
    quantification: float = 0.0


class ATSScoreReport(BaseModel):
    overall_score: float = 0.0
    matched_keywords: List[KeywordMatch] = Field(default_factory=list)
    missing_keywords: List[KeywordMatch] = Field(default_factory=list)
    section_scores: SectionScores = Field(default_factory=SectionScores)
    suggestions: List[str] = Field(default_factory=list)
    total_jd_keywords: int = 0
    total_matched_count: int = 0


def _split_resume_sections(resume_text: str) -> Dict[str, str]:
    """Extract section text blocks from a markdown resume."""
    sections = {"summary": "", "experience": "", "skills": "", "other": ""}
    current_sec = "other"

    lines = resume_text.split("\n")
    buffer: Dict[str, List[str]] = {k: [] for k in sections}

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            header = stripped[3:].strip().upper()
            if "SUMMARY" in header:
                current_sec = "summary"
            elif "EXPERIENCE" in header or "EMPLOYMENT" in header:
                current_sec = "experience"
            elif "SKILL" in header or "TECHNOLOG" in header:
                current_sec = "skills"
            else:
                current_sec = "other"
            continue
        buffer[current_sec].append(line)

    for k in sections:
        sections[k] = "\n".join(buffer[k]).strip()

    return sections


def calculate_ats_score(resume_text: str, jd_text: str) -> ATSScoreReport:
    """Calculate detailed ATS match score and recommendations between resume and JD."""
    if not resume_text.strip() or not jd_text.strip():
        return ATSScoreReport()

    ontology = SMEOntology()
    jd_keywords = extract_ats_keywords(jd_text)
    if not jd_keywords:
        return ATSScoreReport()

    sections = _split_resume_sections(resume_text)
    summary_text = sections["summary"]
    exp_text = sections["experience"]
    skills_text = sections["skills"]
    full_resume_lower = resume_text.lower()

    matched: List[KeywordMatch] = []
    missing: List[KeywordMatch] = []

    skills_matched_count = 0
    exp_matched_count = 0
    summary_matched_count = 0

    for kw in jd_keywords:
        kw_clean = kw.strip()
        if not kw_clean:
            continue

        pattern = rf"(?<!\w){re.escape(kw_clean.lower())}(?!\w)"
        in_skills = bool(re.search(pattern, skills_text.lower()))
        in_exp = bool(re.search(pattern, exp_text.lower()))
        in_sum = bool(re.search(pattern, summary_text.lower()))

        matches = len(re.findall(pattern, full_resume_lower))

        if matches > 0:
            if in_skills:
                skills_matched_count += 1
            if in_exp:
                exp_matched_count += 1
            if in_sum:
                summary_matched_count += 1

            matched.append(KeywordMatch(
                term=kw_clean,
                frequency=matches,
                in_skills=in_skills,
                in_experience=in_exp,
                in_summary=in_sum,
            ))
        else:
            missing.append(KeywordMatch(
                term=kw_clean,
                frequency=0,
                in_skills=False,
                in_experience=False,
                in_summary=False,
            ))

    total_kws = len(jd_keywords)
    match_ratio = (len(matched) / total_kws) if total_kws > 0 else 0.0

    # Section scores
    skills_score = round((skills_matched_count / total_kws) * 100, 1) if total_kws else 0.0
    exp_score = round((exp_matched_count / total_kws) * 100, 1) if total_kws else 0.0
    sum_score = round((summary_matched_count / total_kws) * 100, 1) if total_kws else 0.0

    # Metric quantification score in experience bullets
    exp_bullets = [line.strip() for line in exp_text.split("\n") if line.strip().startswith("- ")]
    quant_count = sum(1 for b in exp_bullets if METRIC_PATTERN.search(b))
    quant_score = round((quant_count / len(exp_bullets)) * 100, 1) if exp_bullets else 0.0

    # Composite overall ATS score (weighted: 55% keyword coverage, 25% experience depth, 20% quantification)
    overall = min(100.0, round((match_ratio * 65.0) + (min(1.0, exp_score / 40.0) * 20.0) + (min(1.0, quant_score / 50.0) * 15.0), 1))

    # Actionable suggestions
    suggestions: List[str] = []
    if missing:
        top_missing = [m.term for m in missing[:5]]
        suggestions.append(f"Add key missing technologies to Skills or Experience: {', '.join(top_missing)}.")

    unmatched_in_exp = [m.term for m in matched if not m.in_experience][:3]
    if unmatched_in_exp:
        suggestions.append(f"Highlight {', '.join(unmatched_in_exp)} in your Experience bullet points to demonstrate hands-on impact.")

    if quant_score < 50:
        suggestions.append("Add measurable metrics (% improvements, latency reductions, user scale) to more bullet points.")

    if not summary_matched_count and total_kws > 0:
        suggestions.append("Incorporate target role domain keywords into your Executive Summary.")

    return ATSScoreReport(
        overall_score=overall,
        matched_keywords=matched,
        missing_keywords=missing,
        section_scores=SectionScores(
            skills=skills_score,
            experience=exp_score,
            summary=sum_score,
            quantification=quant_score,
        ),
        suggestions=suggestions,
        total_jd_keywords=total_kws,
        total_matched_count=len(matched),
    )
