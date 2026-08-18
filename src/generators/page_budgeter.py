"""
page_budgeter.py — Candidate-agnostic page budgeter for 1-Page vs 2-Page resume layouts.
Applies Single Responsibility Principle (SRP) to curate bullets, prioritize ATS keywords,
and structure sections according to target page constraints.
"""

from typing import List, Optional
import copy

from .models import JobEntry, ResumeData
from .text_formatter import score_and_select_bullets


def budget_resume_for_pages(
    data: ResumeData,
    target_pages: int = 2,
    keywords: Optional[List[str]] = None,
) -> ResumeData:
    """
    Transform and curate a ResumeData model to strictly fit target_pages constraint.

    Args:
        data: Input ResumeData instance (parsed master or tailored resume).
        target_pages: 1 for ultra-dense 1-page layout, 2 for balanced Senior/Staff 2-page layout.
        keywords: Optional list of ATS keywords for metric/relevance scoring.

    Returns:
        New ResumeData instance formatted and budgeted for the requested page target.
    """
    budgeted = copy.deepcopy(data)
    kws = keywords or []

    if target_pages == 1:
        # 1-Page Constraints:
        # Role 1: Top 4 bullets (most recent, highest scope)
        # Role 2: Top 3 bullets
        # Role 3: Top 1-2 bullets
        # Role 4: Top 1 bullet
        role_bullet_limits = [4, 3, 1, 1]

        budgeted_jobs: List[JobEntry] = []
        for idx, job in enumerate(budgeted.jobs):
            max_b = role_bullet_limits[idx] if idx < len(role_bullet_limits) else 1
            curated_bullets = score_and_select_bullets(
                bullets=job.bullets,
                keywords=kws,
                max_bullets=max_b,
                bullet_stories=job.bullet_stories,
            )
            job_copy = job.model_copy(update={"bullets": curated_bullets})
            budgeted_jobs.append(job_copy)

        budgeted.jobs = budgeted_jobs

        # In 1-page mode, limit certifications and education to concise entries
        if len(budgeted.certifications) > 2:
            budgeted.certifications = budgeted.certifications[:2]

    else:
        # 2-Page Constraints:
        # Role 1: Up to 8 bullets
        # Role 2: Up to 5 bullets
        # Role 3: Up to 2 bullets
        # Role 4: Up to 2 bullets
        role_bullet_limits = [8, 5, 2, 2]

        budgeted_jobs: List[JobEntry] = []
        for idx, job in enumerate(budgeted.jobs):
            max_b = role_bullet_limits[idx] if idx < len(role_bullet_limits) else 2
            curated_bullets = score_and_select_bullets(
                bullets=job.bullets,
                keywords=kws,
                max_bullets=max_b,
                bullet_stories=job.bullet_stories,
            )
            job_copy = job.model_copy(update={"bullets": curated_bullets})
            budgeted_jobs.append(job_copy)

        budgeted.jobs = budgeted_jobs

    return budgeted
