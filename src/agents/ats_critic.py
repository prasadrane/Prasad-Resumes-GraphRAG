"""
src/agents/ats_critic.py — Deterministic ATS Evaluator & Critic Subagent ($0.00 / 0 tokens).

Wraps and leverages existing scoring, ontology, and ATS matching engines to provide
instantaneous, mathematically reproducible resume alignment scoring.
"""

import logging
import re
from typing import Any, Dict, List, Set, Union

from src.generators.ats_matcher import extract_ats_keywords
from src.generators.models import ResumeData
from src.generators.scoring import ImpactScorer, METRIC_PATTERNS
from src.generators.sme_ontology import SMEOntology
from src.scrapers.models import JobPosting
from .models import CriticScoreBreakdown

log = logging.getLogger(__name__)


class ATSCriticAgent:
    """Specialized Critic subagent for deterministic ATS scoring and gap analysis."""

    def __init__(self):
        self.scorer = ImpactScorer()
        self.ontology = SMEOntology()

    def evaluate(self, resume: ResumeData, job: Union[JobPosting, str]) -> CriticScoreBreakdown:
        """Deterministically evaluate resume alignment against job requirements."""
        if isinstance(job, JobPosting):
            jd_text = f"{job.role_title} {job.company}\n{' '.join(job.required_skills)}\n{' '.join(job.preferred_skills)}\n{job.raw_description}"
            explicit_skills = set(job.required_skills + job.preferred_skills)
        else:
            jd_text = str(job)
            explicit_skills = set()

        # 1. Extract Target Keywords
        extracted_keywords = extract_ats_keywords(jd_text, expand_ontology=True)
        all_target_skills = set(extracted_keywords).union(explicit_skills)

        # 2. Build full resume text representation
        resume_text_parts = [
            resume.name,
            resume.title,
            resume.summary,
            " ".join(resume.skills),
            " ".join(resume.certifications),
            " ".join(resume.education),
        ]
        all_bullets: List[Dict[str, Any]] = []
        for j_idx, job_entry in enumerate(resume.jobs):
            resume_text_parts.append(job_entry.title)
            resume_text_parts.append(job_entry.company)
            for b_idx, bullet in enumerate(job_entry.bullets):
                resume_text_parts.append(bullet)
                all_bullets.append({
                    "job_index": j_idx,
                    "bullet_index": b_idx,
                    "role": job_entry.title,
                    "company": job_entry.company,
                    "bullet": bullet,
                })

        full_resume_text = " ".join(resume_text_parts)
        full_resume_upper = full_resume_text.upper()

        # 3. Keyword Coverage Calculation (40%)
        matched_keywords: List[str] = []
        missing_keywords: List[str] = []

        for skill in all_target_skills:
            if not skill or len(skill.strip()) < 2:
                continue
            skill_clean = skill.strip()
            # Check direct match or regex word boundary
            pattern = re.compile(rf"\b{re.escape(skill_clean)}\b", re.IGNORECASE)
            if pattern.search(full_resume_text) or skill_clean.upper() in full_resume_upper:
                matched_keywords.append(skill_clean)
            else:
                missing_keywords.append(skill_clean)

        total_target_count = len(matched_keywords) + len(missing_keywords)
        keyword_coverage = (
            (len(matched_keywords) / total_target_count * 100.0)
            if total_target_count > 0 else 100.0
        )

        # 4. Impact Metric & Action-Verb Scoring (25%)
        bullet_scores = []
        for item in all_bullets:
            bullet = item["bullet"]
            # Action Verb Tier
            verb_tier = self.scorer.get_verb_tier(bullet)
            tier_mult = 1.0 if verb_tier == 1 else (0.75 if verb_tier == 2 else (0.4 if verb_tier == 3 else 0.5))

            # Quantified Metric Bonus
            has_metric = any(pat.search(bullet) for pat in METRIC_PATTERNS)
            metric_mult = 1.2 if has_metric else 0.8

            # Target skill presence in bullet
            contains_target_skill = any(re.search(rf"\b{re.escape(k)}\b", bullet, re.I) for k in matched_keywords)
            skill_mult = 1.1 if contains_target_skill else 0.9

            b_score = min(100.0, max(10.0, 60.0 * tier_mult * metric_mult * skill_mult))
            item["score"] = round(b_score, 1)
            item["has_metric"] = has_metric
            item["verb_tier"] = verb_tier
            bullet_scores.append(b_score)

        avg_impact_score = (sum(bullet_scores) / len(bullet_scores)) if bullet_scores else 80.0

        # 5. Bolding Compliance (<20% bold character cap) (15%)
        bolding_violations = 0
        for item in all_bullets:
            b_text = item["bullet"]
            bold_matches = re.findall(r"\*\*(.+?)\*\*", b_text)
            bold_char_count = sum(len(m) for m in bold_matches)
            total_chars = max(1, len(b_text))
            density = bold_char_count / total_chars
            if density > 0.25 or len(bold_matches) > 3:
                bolding_violations += 1

        bolding_compliance = max(0.0, 100.0 - (bolding_violations * 15.0))

        # 6. Page Budget Score (20%) - Target 2-page fit
        total_chars = len(full_resume_text)
        # Optimal character count for 2-page ReportLab layout with 0.55" margins is 3200 - 5400 chars
        if 2800 <= total_chars <= 5600:
            page_budget_score = 100.0
        elif total_chars < 2800:
            page_budget_score = max(50.0, 100.0 - (2800 - total_chars) / 30.0)
        else:
            page_budget_score = max(40.0, 100.0 - (total_chars - 5600) / 40.0)

        # 7. Composite ATS Score (0 - 100)
        composite = (
            0.40 * keyword_coverage +
            0.25 * avg_impact_score +
            0.15 * bolding_compliance +
            0.20 * page_budget_score
        )

        # 8. Identify Weakest Bullets (Sorted ascending by score)
        sorted_bullets = sorted(all_bullets, key=lambda x: x["score"])
        # Select bottom 25-30% or at most top 3 weakest bullets
        weak_count = min(3, max(1, len(sorted_bullets) // 3))
        weakest_bullets = sorted_bullets[:weak_count]

        return CriticScoreBreakdown(
            composite_score=round(composite, 1),
            keyword_coverage=round(keyword_coverage, 1),
            impact_metric_score=round(avg_impact_score, 1),
            bolding_compliance_score=round(bolding_compliance, 1),
            page_budget_score=round(page_budget_score, 1),
            matched_keywords=sorted(matched_keywords),
            missing_keywords=sorted(missing_keywords),
            weakest_bullets=weakest_bullets,
        )
