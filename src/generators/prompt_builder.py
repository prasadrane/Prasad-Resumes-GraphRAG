"""
prompt_builder.py — LLM prompt construction, context extraction, and response parsing.

Handles formatting of job experience bullets, metric extraction, GraphRAG context,
and structured parsing of LLM outputs for resume tailoring.
"""

import logging
import re
from typing import List, Tuple

from src.config.llm_constants import GRAPHRAG_STORY_CAP
from .models import JobEntry, ResumeData

log = logging.getLogger(__name__)

STRONG_ACTION_VERBS = {
    "LED", "ARCHITECTED", "DESIGNED", "BUILT", "DIAGNOSED", "OWNED", "ESTABLISHED",
    "IMPLEMENTED", "ENGINEERED", "REDUCED", "ACHIEVED", "REPLACED", "MIGRATED",
    "REVERSE-ENGINEERED", "AUTOMATED", "RESOLVED", "ROOT-CAUSED", "DELIVERED",
    "REDESIGNED", "REFACTORED", "EXECUTED", "INFLUENCED", "SPEARHEADED",
    "ORCHESTRATED", "PIONEERED", "TRANSFORMED", "OPTIMIZED", "STREAMLINED",
}

METRIC_PATTERN = re.compile(
    r"\b\d+\.?\d*\s*%|"           # Percentages: 40%, 99.95%
    r"\b\d+[xX]\b|"               # Multipliers: 3x
    r"\$\d+|"                      # Dollar amounts
    r"\b\d+\s*(?:seconds?|minutes?|hours?|days?|weeks?|months?)\b|"  # Durations
    r"\b\d{2,}[,\d]*\+?\s*(?:daily|monthly|weekly|users?|transactions?|applications?)\b",  # Volume
    re.IGNORECASE
)

SUMMARY_SYSTEM_PROMPT = (
    "You are an elite technical resume strategist who has placed 500+ senior engineers "
    "at top-tier technology companies. You specialize in transforming generic professional "
    "summaries into compelling, role-specific executive narratives that make hiring managers "
    "immediately see the candidate as the ideal hire.\n\n"
    "Your approach:\n"
    "- Lead with the candidate's single strongest quantified achievement relevant to THIS specific role\n"
    "- Mirror the job description's seniority language and domain terminology naturally\n"
    "- Weave in 2-3 specific metrics that demonstrate impact at the scale this role requires\n"
    "- Position the candidate as someone who has ALREADY solved the problems this role will face\n"
    "- Write in a confident, executive tone — not a mechanical skills inventory\n\n"
    "Strict rules:\n"
    "- Do NOT invent any facts, experiences, metrics, or technologies not in the source material\n"
    "- Do NOT produce a mechanical list of skills or technologies — write a compelling narrative\n"
    "- Do NOT use clichés: 'Results-driven', 'Highly motivated', 'Passionate about', 'Detail-oriented', "
    "'Proven track record of excellence'\n"
    "- Do NOT start with an adjective — start with the role title and years of experience\n"
    "- Preserve the exact career level and year count from the original\n"
    "- Keep length to 2-4 sentences (match the original summary length)\n"
    "- Return ONLY the rewritten summary paragraph — no labels, headers, quotes, or explanations\n"
)

BULLETS_SYSTEM_PROMPT = (
    "You are an elite technical resume strategist specializing in rewriting experience bullets "
    "to maximize relevance for a specific job description while preserving complete authenticity.\n\n"
    "Your approach:\n"
    "- Reorder bullets so the most JD-relevant achievements appear FIRST\n"
    "- Reframe each bullet to emphasize the aspects most relevant to the target role\n"
    "- Use the JD's exact technical terminology and domain language where the candidate has matching experience\n"
    "- Every bullet MUST follow: Strong Action Verb → Technical Context → Measurable Impact\n\n"
    "CRITICAL rules — violations will produce a rejected resume:\n"
    "- NEVER change, drop, round, or omit any number, percentage, time duration, or dollar amount\n"
    "  (e.g., '99.95%' must stay '99.95%', '40%' must stay '40%', '70% reduction' must stay '70% reduction')\n"
    "- NEVER invent new experiences, technologies, projects, or outcomes not in the originals\n"
    "- NEVER genericize specific technologies (e.g., do NOT turn 'DynamoDB' into 'NoSQL database', "
    "do NOT turn 'SemaphoreSlim' into 'concurrency control')\n"
    "- NEVER drop the problem statement or context — the reader needs to understand WHAT was broken/needed\n"
    "- Keep the EXACT same number of bullets as provided\n"
    "- Each bullet must start with a past-tense action verb (Led, Architected, Designed, Built, Diagnosed, etc.)\n"
    "- Return ONLY the rewritten bullets as plain text, one per line\n"
    "- No dashes, no numbering, no headers, no explanations\n"
)


def get_graphrag_context(jd_text: str, keywords: List[str]) -> str:
    """Query GraphRAG knowledge graph for relevant candidate achievements matching the JD."""
    try:
        from .ats_matcher import match_graphrag_stories
        stories = match_graphrag_stories(keywords)
        if stories:
            return "\n".join(stories[:GRAPHRAG_STORY_CAP])
    except Exception as err:
        log.warning("GraphRAG context retrieval failed: %s", err)
    return ""


def extract_gap_framing(master_content: str, jd_text: str) -> str:
    """Extract relevant gap-framing rows from MASTER_RESUME for skills the JD mentions."""
    gap_rows = []
    in_gap_section = False
    jd_upper = jd_text.upper()

    for line in master_content.split("\n"):
        stripped = line.strip()
        if "Gap-Framing" in stripped and stripped.startswith("##"):
            in_gap_section = True
            continue
        if in_gap_section and stripped.startswith("##"):
            break
        if in_gap_section and stripped.startswith("|") and "**" in stripped:
            cells = [c.strip() for c in stripped.split("|") if c.strip()]
            if len(cells) >= 3:
                req = cells[0].replace("**", "").strip()
                if req.upper() in jd_upper or any(
                    word.upper() in jd_upper for word in re.split(r"[/() ]+", req) if len(word.strip()) >= 3
                ):
                    gap_rows.append(f"- JD asks for {req}: {cells[2]}")

    return "\n".join(gap_rows) if gap_rows else ""


def extract_top_metrics(parsed: ResumeData) -> str:
    """Extract the most impactful quantified achievements from parsed resume data."""
    metrics = []
    for job in parsed.jobs:
        for bullet in job.bullets:
            if METRIC_PATTERN.search(bullet):
                clean = re.sub(r"\*+", "", bullet)
                metrics.append(f"- [{job.title}] {clean[:200]}")

    if metrics:
        return "\n".join(metrics[:10])
    return ""


def build_single_call_prompt(
    parsed: ResumeData,
    company_name: str,
    jd_text: str,
    graphrag_context: str,
    gap_framing: str,
    top_metrics: str,
) -> Tuple[str, List[JobEntry]]:
    """Build the consolidated single-call LLM prompt for rewriting summary and bullets."""
    jobs_with_bullets = [job for job in parsed.jobs if job.bullets]

    prompt_parts = [
        f"## Target Role\nCompany: {company_name}\n",
        f"## Full Job Description\n{jd_text}\n",
        f"## Original Summary\n{parsed.summary}\n",
    ]

    if top_metrics:
        prompt_parts.append(f"## Candidate's Strongest Impact Metrics\n{top_metrics}\n")

    if graphrag_context:
        prompt_parts.append(f"## Relevant Candidate Achievements (from Knowledge Graph)\n{graphrag_context}\n")

    if gap_framing:
        prompt_parts.append(f"## Skill Bridging Notes\n{gap_framing}\n")

    prompt_parts.append("## Experience Bullets to Rewrite\n")
    for idx, job in enumerate(jobs_with_bullets):
        prompt_parts.append(f"### Job {idx + 1}: {job.title} at {job.company} ({job.dates})")
        prompt_parts.append(f"Original bullets ({len(job.bullets)} total):")
        for i, b in enumerate(job.bullets):
            story = job.bullet_stories[i] if i < len(job.bullet_stories) else ""
            if story:
                prompt_parts.append(f"  [Context: {story}]")
            prompt_parts.append(f"  - {b}")
        prompt_parts.append("")

    prompt_parts.append(
        "## Your Task\n"
        "1. REWRITE THE SUMMARY: Create a compelling executive summary positioned for this specific role. "
        "Start your response with '### SUMMARY:' followed by the rewritten summary.\n\n"
        "2. REWRITE THE BULLETS: Rewrite and reorder bullets for each job to maximize JD relevance. "
        "Use '### JOB N:' headers followed by plain bullet lines (no dashes, no numbering). "
        "Preserve the exact number of bullets per job.\n\n"
        "Format your response EXACTLY like this:\n"
        "### SUMMARY:\n"
        "[rewritten summary here]\n\n"
        "### JOB 1:\n"
        "[bullet 1]\n"
        "[bullet 2]\n"
        "... etc.\n\n"
        "### JOB 2:\n"
        "[bullet 1]\n"
        "... etc."
    )

    return "\n".join(prompt_parts), jobs_with_bullets


def parse_single_call_response(
    llm_response: str,
    parsed: ResumeData,
    jobs_with_bullets: List[JobEntry],
) -> ResumeData:
    """Parse the combined LLM response into parsed ResumeData."""
    lines = llm_response.split("\n")
    if not any(l.strip().startswith("###") for l in lines):
        clean_text = re.sub(r'^["\']|["\']$', '', llm_response.strip()).strip()
        if len(clean_text) > 20:
            parsed.summary = clean_text
        return parsed

    in_summary = False
    current_job_idx = -1
    summary_lines = []
    current_bullets = []

    def apply_job_bullets(job_idx, bullets):
        if 0 <= job_idx < len(jobs_with_bullets) and bullets:
            job = jobs_with_bullets[job_idx]
            if len(bullets) >= max(1, len(job.bullets) - 2):
                job.bullets = bullets[:len(job.bullets) + 2]

    for line in lines:
        line = line.strip()

        if line.startswith("### SUMMARY:"):
            in_summary = True
            current_job_idx = -1
            if len(line) > len("### SUMMARY:"):
                summary_lines.append(line[len("### SUMMARY:"):].strip())
            continue

        if line.startswith("### JOB"):
            in_summary = False
            if current_job_idx >= 0 and current_bullets:
                apply_job_bullets(current_job_idx, current_bullets)
            try:
                current_job_idx = int(line.split("JOB")[1].split(":")[0].strip()) - 1
            except Exception:
                current_job_idx = -1
            current_bullets = []
            continue

        if in_summary:
            if line:
                summary_lines.append(line)
        elif current_job_idx >= 0 and line:
            cleaned = re.sub(r"^[\s\-\*\•\·\d\.]+", "", line).strip()
            cleaned = re.sub(r"^\*\*([A-Za-z0-9\-\s/]+?)\*\*(\s+)", r"\1\2", cleaned)
            if cleaned:
                current_bullets.append(cleaned)

    if current_job_idx >= 0 and current_bullets:
        apply_job_bullets(current_job_idx, current_bullets)

    if summary_lines:
        new_summary = " ".join(summary_lines).strip()
        new_summary = re.sub(r'^["\']|["\']$', '', new_summary).strip()
        if len(new_summary) > 50:
            parsed.summary = new_summary

    return parsed
