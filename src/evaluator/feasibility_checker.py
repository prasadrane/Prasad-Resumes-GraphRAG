"""
feasibility_checker.py ? Pre-generation candidate fit, feasibility & gap classifier.

Analyzes Job Descriptions against candidate master background, classifies gaps into
Fillable (transferable experience / story bank) vs Unfillable, and outputs tailored strategy blueprints.
"""

import re
from typing import Optional, List, Dict
from src.generators.ats_matcher import extract_ats_keywords
from src.generators.prompt_builder import extract_gap_framing
from src.evaluator.models import FeasibilityReport, FillableGap, TailoringStrategyBlueprint


class FeasibilityChecker:
    """Evaluates JD compatibility and creates tailoring strategy before synthesis."""

    def __init__(self, master_content: str = ""):
        self.master_content = master_content

    def check_feasibility(self, jd_text: str, company_name: str = "") -> FeasibilityReport:
        """Evaluate candidate match against JD and classify gaps."""
        if not jd_text.strip():
            return FeasibilityReport(
                baseline_match_pct=0.0,
                hard_skills_match_pct=0.0,
                soft_skills_match_pct=0.0,
                verdict="DO_NOT_APPLY",
                rationale="Empty Job Description text provided.",
            )

        jd_keywords = extract_ats_keywords(jd_text, expand_ontology=True)
        if not jd_keywords:
            jd_keywords = [
                w.strip()
                for w in re.findall(r"\b[A-Za-z0-9+#.-]{3,}\b", jd_text)
                if len(w) > 3 and w.lower() not in {"with", "that", "this", "from", "have", "will", "your"}
            ][:15]

        master_lower = self.master_content.lower()
        matched: List[str] = []
        fillable: List[FillableGap] = []
        unfillable: List[str] = []

        # Check gap framing table from master resume
        gap_framing_text = extract_gap_framing(self.master_content, jd_text)

        for kw in jd_keywords:
            kw_clean = kw.strip()
            pattern = rf"(?<!\w){re.escape(kw_clean.lower())}(?!\w)"
            if re.search(pattern, master_lower):
                matched.append(kw_clean)
            elif gap_framing_text and kw_clean.lower() in gap_framing_text.lower():
                fillable.append(
                    FillableGap(
                        skill=kw_clean,
                        company_context="Master Background / Transferable Experience",
                        evidence_snippet="Found in candidate Gap-Framing mapping.",
                    )
                )
            else:
                unfillable.append(kw_clean)

        total_kws = max(1, len(jd_keywords))
        effective_matched_count = len(matched) + (len(fillable) * 0.75)
        match_pct = min(100.0, round((effective_matched_count / total_kws) * 100.0, 1))

        if match_pct >= 65.0:
            verdict = "STRONG_MATCH"
            rationale = f"Strong candidate match ({match_pct}%). Direct experience in core skills."
        elif match_pct >= 40.0:
            verdict = "TAILORABLE"
            rationale = f"Viable match ({match_pct}%). Gaps can be bridged using Story Bank transferable experience."
        elif match_pct >= 25.0:
            verdict = "HIGH_GAP"
            rationale = f"Significant skill gap ({match_pct}%). Requires substantial domain framing."
        else:
            verdict = "DO_NOT_APPLY"
            rationale = f"Fatal skill gap ({match_pct}%). Core mandatory competencies are missing from candidate background."

        return FeasibilityReport(
            baseline_match_pct=match_pct,
            hard_skills_match_pct=match_pct,
            soft_skills_match_pct=match_pct,
            matched_skills=matched,
            fillable_gaps=fillable,
            unfillable_gaps=unfillable,
            verdict=verdict,
            rationale=rationale,
        )

    def build_strategy_blueprint(
        self, jd_text: str, company_name: str, feasibility: FeasibilityReport
    ) -> TailoringStrategyBlueprint:
        """Construct structured tailoring blueprint to guide generator."""
        must_include = feasibility.matched_skills[:8] + [g.skill for g in feasibility.fillable_gaps[:4]]
        role_title = "Senior Software Engineer"
        for title_candidate in ["Principal Engineer", "Lead Engineer", "Staff Engineer", "Engineering Manager", "Architect"]:
            if title_candidate.lower() in jd_text.lower():
                role_title = title_candidate
                break

        return TailoringStrategyBlueprint(
            target_role_title=role_title,
            target_company=company_name,
            recommended_summary_focus=f"Emphasize impact in {', '.join(must_include[:3])}" if must_include else "Emphasize high scale distributed architecture",
            must_include_keywords=must_include,
            cover_letter_hook_theme=f"Solving core technical challenges at {company_name} using verified experience in {', '.join(must_include[:2])}" if must_include else f"Driving software impact at {company_name}",
        )
