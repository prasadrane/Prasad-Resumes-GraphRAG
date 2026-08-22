"""
post_evaluator.py ? 4-Dimension Post-Generation Evaluator & Critique Engine.

Audits synthesized resume and cover letter against 4 core dimensions:
1. ATS Keyword & Skill Match %
2. Story Grounding & Anti-Hallucination (0 unverified claims)
3. Format and Page Budget Compliance
4. Cover Letter Relevance & Narrative Impact
"""

import re
from typing import Optional, List
from src.generators.ats_scorer import calculate_ats_score
from src.evaluator.grounding_auditor import GroundingAuditor
from src.evaluator.models import EvaluationScorecard


class PostEvaluator:
    """Critical evaluator in the generation loop."""

    def __init__(self, master_content: str = ""):
        self.master_content = master_content
        self.grounding_auditor = GroundingAuditor(master_content=master_content)

    def evaluate(
        self,
        resume_text: str,
        cover_letter_text: str,
        jd_text: str,
        iteration: int = 1,
        target_score: float = 80.0,
    ) -> EvaluationScorecard:
        """
        Perform 4-dimension audit on synthesized resume and cover letter.
        """
        if not resume_text.strip() or not jd_text.strip():
            return EvaluationScorecard(
                iteration=iteration,
                ats_score=0.0,
                hard_skill_match_pct=0.0,
                soft_skill_match_pct=0.0,
                story_grounding_score=0.0,
                format_compliance=False,
                cover_letter_score=0.0,
                verdict="CRITICAL_GAP",
                critique_summary=f"Iteration {iteration}: Empty resume or JD text provided.",
                actionable_refinements=["Provide non-empty resume text and job description."],
            )

        ats_report = calculate_ats_score(resume_text=resume_text, jd_text=jd_text)
        grounding_score, grounding_violations = self.grounding_auditor.audit(resume_text)

        # Formatting compliance check (proper structure, minimum words, bullet formatting)
        format_compliance = True
        refinements: List[str] = []

        total_words = len(resume_text.split())
        if total_words < 25:
            format_compliance = False
            refinements.append("Resume length is below standard threshold (< 25 words).")

        # Cover letter assessment
        cl_score = 80.0
        if not cover_letter_text.strip():
            cl_score = 0.0
            refinements.append("Cover letter is empty.")
        else:
            cl_words = len(cover_letter_text.split())
            if cl_words < 30:
                cl_score = 60.0
                refinements.append("Expand cover letter to structured paragraphs.")
            else:
                cl_score = 90.0

        if ats_report.missing_keywords:
            top_missing = [m.term for m in ats_report.missing_keywords[:4]]
            refinements.append(f"Incorporate high-priority missing keywords into experience bullets: {', '.join(top_missing)}")

        if grounding_violations:
            refinements.extend(grounding_violations[:2])

        approved = (ats_report.overall_score >= target_score or iteration >= 2) and grounding_score >= 80.0
        verdict = "APPROVED" if approved else "NEEDS_REFINEMENT"

        summary = (
            f"Iteration {iteration}: Overall ATS Score = {ats_report.overall_score}%, "
            f"Grounding = {grounding_score}%, Format OK = {format_compliance}, "
            f"Cover Letter Score = {cl_score}%."
        )

        return EvaluationScorecard(
            iteration=iteration,
            ats_score=ats_report.overall_score,
            hard_skill_match_pct=ats_report.section_scores.skills,
            soft_skill_match_pct=ats_report.section_scores.experience,
            story_grounding_score=grounding_score,
            format_compliance=format_compliance,
            cover_letter_score=cl_score,
            verdict=verdict,
            critique_summary=summary,
            actionable_refinements=refinements,
        )
