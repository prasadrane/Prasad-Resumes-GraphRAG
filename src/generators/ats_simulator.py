"""
ats_simulator.py — Automated ATS Score Simulator & Keyword Gap Analyzer.

Simulates standard applicant tracking systems (ATS) parsing rules, computing an overall
Match Score (0-100%), keyword coverage ratio, missing target skills, and formatting compliance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import List, Set

from src.generators.ats_matcher import extract_ats_keywords

logger = logging.getLogger(__name__)


@dataclass
class ATSReport:
    """Quantitative ATS analysis and gap report."""
    overall_score: float  # 0.0 to 100.0
    keyword_coverage: float  # 0.0 to 1.0
    covered_keywords: List[str] = field(default_factory=list)
    missing_keywords: List[str] = field(default_factory=list)
    formatting_issues: List[str] = field(default_factory=list)
    is_compliant: bool = True


class ATSSimulator:
    """
    ATS parser simulator and compatibility scorer.
    """

    def simulate(self, resume_text: str, jd_text: str) -> ATSReport:
        """Evaluate resume text against target job description."""
        if not resume_text or not jd_text:
            return ATSReport(
                overall_score=0.0,
                keyword_coverage=0.0,
                is_compliant=False,
                formatting_issues=["Empty resume or job description text."],
            )

        # 1. Extract target keywords from Job Description
        target_keywords = extract_ats_keywords(jd_text, expand_ontology=False)
        if not target_keywords:
            target_keywords = [w.strip() for w in jd_text.split() if len(w.strip()) > 3][:10]

        resume_lower = resume_text.lower()

        covered: List[str] = []
        missing: List[str] = []

        for kw in target_keywords:
            if kw.lower() in resume_lower:
                covered.append(kw)
            else:
                missing.append(kw)

        coverage = len(covered) / len(target_keywords) if target_keywords else 1.0

        # 2. Check formatting compliance
        formatting_issues: List[str] = []
        if len(resume_text.split()) < 20:
            formatting_issues.append("Resume token count is unusually low (<20 words).")
        if "\x00" in resume_text:
            formatting_issues.append("Contains null bytes or binary corruption.")

        # Compute overall score out of 100
        format_penalty = len(formatting_issues) * 5.0
        score = max(0.0, min(100.0, (coverage * 95.0 + 5.0) - format_penalty))

        return ATSReport(
            overall_score=round(score, 1),
            keyword_coverage=round(coverage, 2),
            covered_keywords=covered,
            missing_keywords=missing,
            formatting_issues=formatting_issues,
            is_compliant=len(formatting_issues) == 0,
        )
