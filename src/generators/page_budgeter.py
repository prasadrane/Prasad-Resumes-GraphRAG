"""
page_budgeter.py — Candidate-agnostic page budgeter for 1-Page vs 2-Page resume layouts.
Applies Single Responsibility Principle (SRP) to curate bullets, prioritize ATS keywords,
and structure sections according to target page constraints.
"""

import re
from typing import List, Optional
import copy

from .models import JobEntry, ResumeData
from .text_formatter import score_and_select_bullets

# Categories to drop entirely in 1-page mode (matched against the bold label before the colon).
_1PAGE_DROP_CATEGORIES = {"Frontend"}

# Category pairs to merge in 1-page mode: (label_A, label_B) -> merged_label.
# Both source categories are removed and replaced with a single merged line.
_1PAGE_MERGE_MAP = {
    ("Generative AI & LLM Systems", "Observability, Testing & DevOps"): "AI & Observability",
}

# Max items (comma-separated skills) per category line in 1-page mode.
_1PAGE_MAX_ITEMS_PER_LINE = 8


def _extract_label_and_items(skill_line: str):
    """Parse a skill line like '**Label**: item1, item2' into (label, [items])."""
    # Strip leading bold markers: **Label**: items
    m = re.match(r"\*\*(.+?)\*\*\s*:\s*(.*)", skill_line)
    if not m:
        return None, []
    label = m.group(1).strip()
    raw_items = m.group(2).strip()
    items = [s.strip() for s in raw_items.split(",") if s.strip()]
    return label, items


def _format_skill_line(label: str, items: List[str]) -> str:
    """Reconstruct a skills line from label + items."""
    return f"**{label}**: {', '.join(items)}"


def _strip_annotations(item: str) -> str:
    """Remove parenthetical annotations like '(Single-Table Design)' to save space."""
    return re.sub(r"\s*\([^)]*\)", "", item).strip()


def compact_skills_for_1page(skills: List[str]) -> List[str]:
    """
    Derive a compact 1-page skills list from the full 2-page skills list.

    Rules applied:
      1. Drop categories listed in _1PAGE_DROP_CATEGORIES.
      2. Merge category pairs defined in _1PAGE_MERGE_MAP.
      3. Strip parenthetical annotations from individual items.
      4. Cap each category line at _1PAGE_MAX_ITEMS_PER_LINE items.
    """
    # Parse all lines into {label: [items]}
    parsed = {}
    order = []
    for line in skills:
        label, items = _extract_label_and_items(line)
        if label is None:
            # Pass through lines that don't match the pattern
            order.append(line)
            continue
        parsed[label] = items
        order.append(label)

    # 1. Drop categories
    for drop in _1PAGE_DROP_CATEGORIES:
        if drop in parsed:
            del parsed[drop]
            order = [o for o in order if o != drop]

    # 2. Merge category pairs
    for (label_a, label_b), merged_label in _1PAGE_MERGE_MAP.items():
        if label_a in parsed and label_b in parsed:
            merged_items = parsed.pop(label_a) + parsed.pop(label_b)
            parsed[merged_label] = merged_items
            # Replace first occurrence with merged, remove second
            replaced = False
            new_order = []
            for o in order:
                if o == label_a and not replaced:
                    new_order.append(merged_label)
                    replaced = True
                elif o == label_b:
                    continue
                else:
                    new_order.append(o)
            order = new_order

    # 3 & 4. Strip annotations and cap items, then reconstruct
    result = []
    for entry in order:
        if entry in parsed:
            items = [_strip_annotations(it) for it in parsed[entry]]
            # Deduplicate after stripping (e.g. "DynamoDB (Single-Table Design)" -> "DynamoDB")
            seen = set()
            deduped = []
            for it in items:
                if it not in seen:
                    seen.add(it)
                    deduped.append(it)
            capped = deduped[:_1PAGE_MAX_ITEMS_PER_LINE]
            result.append(_format_skill_line(entry, capped))
        else:
            result.append(entry)

    return result


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
        # Role 1 (Rocket Mortgage): 7 bullets, Role 2 (LCS): 2 bullets, Role 3 (EXFO): 1 bullet, Role 4 (Tanish): 1 bullet
        role_bullet_limits = [7, 2, 1, 1]

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

        budgeted_projects: List[JobEntry] = []
        for idx, proj in enumerate(budgeted.projects):
            if idx >= 1:
                break
            curated_bullets = score_and_select_bullets(
                bullets=proj.bullets,
                keywords=kws,
                max_bullets=2,
                bullet_stories=proj.bullet_stories,
            )
            proj_copy = proj.model_copy(update={"bullets": curated_bullets})
            budgeted_projects.append(proj_copy)

        budgeted.projects = budgeted_projects

        # In 1-page mode, limit certifications and education to concise entries
        if len(budgeted.certifications) > 2:
            budgeted.certifications = budgeted.certifications[:2]

        # In 1-page mode, derive compact skills from full skills
        budgeted.skills = compact_skills_for_1page(budgeted.skills)

    else:
        # 2-Page Constraints:
        # Role 1 (Rocket Mortgage): Up to 9 bullets
        # Role 2 (LCS): Up to 5 bullets
        # Role 3 (EXFO): Up to 2 bullets
        # Role 4 (Tanish): Up to 2 bullets
        role_bullet_limits = [9, 5, 2, 2]

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

        budgeted_projects: List[JobEntry] = []
        for proj in budgeted.projects:
            curated_bullets = score_and_select_bullets(
                bullets=proj.bullets,
                keywords=kws,
                max_bullets=3,
                bullet_stories=proj.bullet_stories,
            )
            proj_copy = proj.model_copy(update={"bullets": curated_bullets})
            budgeted_projects.append(proj_copy)

        budgeted.projects = budgeted_projects

    return budgeted

