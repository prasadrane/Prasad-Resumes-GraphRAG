"""
resume_generator.py — Tailored raw resume content generator adhering to generic, candidate-agnostic resume rules.
Integrates LLM-driven per-JD tailoring: summary synthesis, bullet re-wording/re-ordering, and ATS keyword bolding.
Enhanced with GraphRAG knowledge graph context, gap-framing intelligence, and semantic bullet scoring.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .ats_matcher import extract_ats_keywords
from src.llm.service import call_llm_safe as _call_llm_safe


from .constants import (
    DEFAULT_CANDIDATE_NAME,
    DEFAULT_CANDIDATE_TITLE,
    MARKDOWN_BULLET_PREFIX,
    MARKDOWN_H1_PREFIX,
    MARKDOWN_H2_PREFIX,
    MARKDOWN_H3_PREFIX,
    RAW_RESUME_FILENAME,
    SECTION_CERTIFICATIONS,
    SECTION_EDUCATION,
    SECTION_EXPERIENCE,
    SECTION_SKILLS,
    SECTION_SUMMARY,
)
from .models import JobEntry, ResumeData
from .resume_parser import (
    _parse_contact_line,
    clean_em_dashes,
    clean_link_url,
    create_job_entry,
    extract_summary_variants,
    parse_job_heading_components,
    parse_master_resume,
    parse_resume_markdown,
)
from .pdf_renderer import render_pdf_resume

from src.config import MASTER_RESUME_PATH, ROOT_DIR

# ── Domain-category mapping for intelligent summary variant selection ──────────
DOMAIN_KEYWORDS = {
    "AI / LLM-Forward": [
        "AI", "ML", "LLM", "Bedrock", "chatbot", "NLP", "prompt", "Claude", "GPT",
        "machine learning", "deep learning", "generative", "RAG", "language model",
        "natural language", "neural", "transformer", "inference",
    ],
    "Cloud & Reliability-Forward": [
        "cloud", "AWS", "Azure", "GCP", "infrastructure", "reliability",
        "uptime", "SRE", "migration", "ECS", "Fargate", "Lambda", "containeriz",
        "scalab", "distributed system", "high availability",
    ],
    "Platform & DevEx-Forward": [
        "platform", "developer experience", "tooling", "onboarding", "DevEx",
        "DX", "developer productivity", "internal tools", "DevOps", "platform engineering",
    ],
    "Security & Auth-Forward": [
        "security", "authentication", "authorization", "OAuth", "JWT", "SSO",
        "IAM", "compliance", "zero trust", "RBAC", "identity", "penetration",
        "vulnerability", "SOC", "audit",
    ],
}

# ── Scoring constants for semantic bullet ranking ─────────────────────────────
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


# ── GraphRAG & Gap-Framing Context Retrieval ──────────────────────────────────

def _get_graphrag_context(jd_text: str, keywords: List[str]) -> str:
    """Query GraphRAG knowledge graph for relevant candidate achievements matching the JD."""
    try:
        from .ats_matcher import match_graphrag_stories
        stories = match_graphrag_stories(keywords)
        if stories:
            # Cap at 20 lines to avoid prompt bloat
            return "\n".join(stories[:20])
    except Exception as err:
        print(f"[WARN] GraphRAG context retrieval failed: {err}")
    return ""


def _extract_gap_framing(master_content: str, jd_text: str) -> str:
    """Extract relevant gap-framing rows from MASTER_RESUME for skills the JD mentions but candidate may lack."""
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
            # Parse table row: | **Requirement** | Experience | Strategy |
            cells = [c.strip() for c in stripped.split("|") if c.strip()]
            if len(cells) >= 3:
                req = cells[0].replace("**", "").strip()
                # Match if the JD requirement keyword or its sub-words appear in the JD text
                if req.upper() in jd_upper or any(
                    word.upper() in jd_upper for word in re.split(r"[/() ]+", req) if len(word.strip()) >= 3
                ):
                    gap_rows.append(f"- JD asks for {req}: {cells[2]}")

    return "\n".join(gap_rows) if gap_rows else ""


def _extract_top_metrics(parsed: "ResumeData") -> str:
    """Extract the most impactful quantified achievements from parsed resume data."""
    metrics = []
    for job in parsed.jobs:
        for bullet in job.bullets:
            if METRIC_PATTERN.search(bullet):
                clean = re.sub(r"\*+", "", bullet)  # Strip bold markers
                metrics.append(f"- [{job.title}] {clean[:200]}")

    if metrics:
        return "\n".join(metrics[:10])  # Top 10 metric-bearing bullets
    return ""


# ── Unchanged Utility Functions ───────────────────────────────────────────────

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

# Functions moved to resume_parser module and re-exported below:
# clean_em_dashes, clean_link_url, parse_job_heading_components, create_job_entry,
# _parse_contact_line, extract_summary_variants, parse_resume_markdown, parse_master_resume

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

# ── Improved Summary Variant Selection (Issue 5) ─────────────────────────────

def select_tailored_summary(content: str, keywords: List[str], company_name: str, jd_text: str = "") -> str:
    """Select best-matching summary variant using domain-category analysis instead of naive keyword counting."""
    variants = extract_summary_variants(content)
    if not variants:
        return ""

    # Use the full JD text for domain matching (extracted keywords alone miss many domain signals)
    match_text = (jd_text or " ".join(keywords)).upper()

    # Score each domain by how many domain-defining keywords appear in the JD
    domain_scores = {}
    for domain_name, domain_kws in DOMAIN_KEYWORDS.items():
        score = sum(1 for dkw in domain_kws if dkw.upper() in match_text)
        domain_scores[domain_name] = score

    # Pick the highest-scoring domain variant
    best_domain = max(domain_scores, key=domain_scores.get)
    best_score = domain_scores[best_domain]

    if best_score >= 2 and best_domain in variants:
        return variants[best_domain]

    # Fallback to canonical if no clear domain match (threshold of 2 prevents false positives)
    return variants.get("Canonical", "")


# ── Semantic Bullet Scoring (Issue 4) ─────────────────────────────────────────

def score_and_select_bullets(
    bullets: List[str],
    keywords: List[str],
    max_bullets: int,
    bullet_stories: Optional[List[str]] = None,
) -> List[str]:
    """Score and reorder bullets using ATS keywords, quantitative metrics, story relevance, and action verb strength."""
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
                    break  # Only one story bonus per bullet

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


# ── Tailored Markdown Formatter ───────────────────────────────────────────────

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
        selected_bullets = score_and_select_bullets(
            job.bullets, keywords, max_bullets, bullet_stories=job.bullet_stories
        )
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


# ── LLM-Driven Deep Tailoring (Issues 1, 2, 6) ──────────────────────────────

# ── Shared LLM tailoring prompts (used by both batch and stepwise paths) ─────

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


def tailor_summary_with_llm(parsed: "ResumeData", company_name: str, jd_text: str,
                            graphrag_context: str, gap_framing: str, top_metrics: str) -> "ResumeData":
    """Re-word the executive summary via LLM. Mutates and returns parsed."""
    summary_prompt_parts = [
        f"## Target Role\nCompany: {company_name}\n",
        f"## Full Job Description\n{jd_text}\n",
        f"## Original Summary\n{parsed.summary}\n",
    ]

    if top_metrics:
        summary_prompt_parts.append(
            f"## Candidate's Strongest Impact Metrics (choose the most relevant for this role)\n{top_metrics}\n"
        )

    if graphrag_context:
        summary_prompt_parts.append(
            f"## Relevant Candidate Achievements (from Knowledge Graph)\n{graphrag_context}\n"
        )

    if gap_framing:
        summary_prompt_parts.append(
            f"## Skill Bridging Notes\n"
            f"For skills the JD requires that the candidate doesn't directly have, use these framing strategies:\n"
            f"{gap_framing}\n"
        )

    summary_prompt_parts.append(
        "Rewrite the summary to position this candidate as the ideal hire for this specific role. "
        "Return only the rewritten summary paragraph."
    )

    summary_prompt = "\n".join(summary_prompt_parts)
    llm_summary = _call_llm_safe(summary_prompt, SUMMARY_SYSTEM_PROMPT).strip()
    # Strip any wrapping quotes or markdown the LLM might add
    llm_summary = re.sub(r'^["\']|["\']$', '', llm_summary).strip()
    llm_summary = re.sub(r'^#+\s+.*\n', '', llm_summary).strip()
    if llm_summary and len(llm_summary) > 50:
        parsed.summary = llm_summary
    return parsed


def tailor_bullets_with_llm(parsed: "ResumeData", company_name: str, jd_text: str,
                            graphrag_context: str, gap_framing: str) -> "ResumeData":
    """Re-word and re-order experience bullets per job via LLM. Mutates and returns parsed."""
    for job in parsed.jobs:
        if not job.bullets:
            continue

        # Build story-grouped bullets text for richer context
        bullets_with_context = []
        current_story = ""
        for i, b in enumerate(job.bullets):
            story = job.bullet_stories[i] if i < len(job.bullet_stories) else ""
            if story and story != current_story:
                bullets_with_context.append(f"\n[Story Context: {story}]")
                current_story = story
            bullets_with_context.append(f"- {b}")

        bullets_text = "\n".join(bullets_with_context)

        bullets_prompt_parts = [
            f"## Target Role\nCompany: {company_name}\n",
            f"## Full Job Description\n{jd_text}\n",
            f"## Role Being Rewritten\n{job.title} at {job.company} ({job.dates})\n",
            f"## Original Bullets (with story context for your understanding — do not include story labels in output)\n{bullets_text}\n",
        ]

        if graphrag_context:
            bullets_prompt_parts.append(
                f"## Relevant Candidate Achievements (from Knowledge Graph)\n{graphrag_context}\n"
            )

        if gap_framing:
            bullets_prompt_parts.append(
                f"## Skill Bridging Notes\n{gap_framing}\n"
            )

        bullets_prompt_parts.append(
            f"Rewrite and reorder these {len(job.bullets)} bullets to maximize relevance for this JD. "
            f"Return exactly {len(job.bullets)} plain bullet lines (no dashes, no numbering)."
        )

        bullets_prompt = "\n".join(bullets_prompt_parts)
        llm_bullets_raw = _call_llm_safe(bullets_prompt, BULLETS_SYSTEM_PROMPT).strip()
        if llm_bullets_raw:
            # Parse LLM output lines, stripping leading dashes/bullets
            new_bullets = []
            for line in llm_bullets_raw.split("\n"):
                cleaned = re.sub(r"^[\s\-\*\•\·\d\.]+", "", line).strip()
                if cleaned:
                    new_bullets.append(cleaned)
            # Only apply if we got back a reasonable number of bullets
            if len(new_bullets) >= max(1, len(job.bullets) - 2):
                job.bullets = new_bullets[:len(job.bullets) + 2]  # Allow slight expansion, then PDF will trim

    return parsed


def llm_tailor_resume(parsed: "ResumeData", master_content: str, company_name: str, jd_text: str, keywords: List[str]) -> "ResumeData":
    """
    Use LLM to produce a genuinely JD-customized resume:
    - Re-word the Executive Summary as a compelling, role-specific narrative
    - Re-word and re-order Experience bullets to best reflect the target role's needs
    - Inject GraphRAG knowledge graph context for richer cross-story understanding
    - Apply gap-framing strategies for skills the candidate doesn't directly have
    
    Rules strictly enforced:
    - No new facts invented - only re-framing/re-ordering existing content
    - No title line
    - 2-page budget preserved (bullet counts unchanged)
    - Bold keyword caps maintained (<20%)
    """
    # ── Compute shared context (once, reused across all LLM calls) ──
    graphrag_context = _get_graphrag_context(jd_text, keywords)
    gap_framing = _extract_gap_framing(master_content, jd_text)
    top_metrics = _extract_top_metrics(parsed)

    # ── 1. LLM-Tailored Executive Summary ──
    parsed = tailor_summary_with_llm(parsed, company_name, jd_text, graphrag_context, gap_framing, top_metrics)

    # ── 2. LLM-Tailored Experience Bullets (per job) ──
    parsed = tailor_bullets_with_llm(parsed, company_name, jd_text, graphrag_context, gap_framing)

    return parsed


# ── Main Entry Point ──────────────────────────────────────────────────────────

def generate_raw_resume(company_name: str, jd_text: str, base_output_dir: Optional[Path] = None) -> Path:
    """Generate LLM-tailored raw_resume.txt per-JD: re-worded, re-ordered, ATS-bolded, no title line."""
    out_dir = get_output_dir(company_name, base_output_dir=base_output_dir)
    raw_resume_path = out_dir / RAW_RESUME_FILENAME

    keywords = extract_ats_keywords(jd_text)

    # Read base MASTER_RESUME.txt if available
    master_path = MASTER_RESUME_PATH
    if master_path.exists():
        master_content = master_path.read_text(encoding="utf-8")
        parsed = parse_resume_markdown(master_content)
        # Step 1: Domain-aware best-match summary variant (fast pre-selection before LLM)
        tailored_summary = select_tailored_summary(master_content, keywords, company_name, jd_text=jd_text)
        if tailored_summary:
            parsed.summary = tailored_summary
        # Step 2: LLM-driven deep tailoring (re-word summary + bullets per JD with GraphRAG context)
        parsed = llm_tailor_resume(parsed, master_content, company_name, jd_text, keywords)
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


def generate_raw_resume_stepwise(company_name: str, jd_text: str, base_output_dir: Optional[Path] = None):
    """Generate LLM-tailored raw_resume.txt and PDF resume stepwise, yielding progress."""
    out_dir = get_output_dir(company_name, base_output_dir=base_output_dir)
    raw_resume_path = out_dir / RAW_RESUME_FILENAME
    pdf_path = out_dir / "Prasad_Rane_Resume.pdf"

    # Step 1: extracting_keywords (8%)
    yield ("extracting_keywords", "Extracting ATS keywords", 8, "Extracting ATS keywords from job description...")
    keywords = extract_ats_keywords(jd_text)

    # Step 2: loading_master (15%)
    yield ("loading_master", "Loading master resume", 15, "Reading and parsing MASTER_RESUME.txt...")
    master_path = MASTER_RESUME_PATH
    if master_path.exists():
        master_content = master_path.read_text(encoding="utf-8")
        parsed = parse_resume_markdown(master_content)
    else:
        master_content = ""
        parsed = ResumeData(
            name=DEFAULT_CANDIDATE_NAME,
            title=DEFAULT_CANDIDATE_TITLE,
            summary=f"{DEFAULT_CANDIDATE_TITLE} with experience building high-throughput software applications.",
            jobs=[create_job_entry("Software Engineer | Tech Corp | Remote | Jan 2023 - Present", ["Built scalable microservices."])],
            skills=["Backend & APIs: C#, Python, Cloud"],
            certifications=["Cloud Certification"],
            education=["B.S. in Computer Science"]
        )

    # Step 3: selecting_summary (25%)
    yield ("selecting_summary", "Selecting best summary variant", 25, "Selecting best matching executive summary variant...")
    if master_content:
        tailored_summary = select_tailored_summary(master_content, keywords, company_name, jd_text=jd_text)
        if tailored_summary:
            parsed.summary = tailored_summary

    # Step 4: tailoring_summary (38%)
    yield ("tailoring_summary", "LLM tailoring summary", 38, "LLM tailoring of executive summary to match target role...")
    if master_content:
        graphrag_context = _get_graphrag_context(jd_text, keywords)
        gap_framing = _extract_gap_framing(master_content, jd_text)
        top_metrics = _extract_top_metrics(parsed)
        parsed = tailor_summary_with_llm(parsed, company_name, jd_text, graphrag_context, gap_framing, top_metrics)
    else:
        graphrag_context = ""
        gap_framing = ""

    # Step 5: tailoring_bullets (55%)
    yield ("tailoring_bullets", "LLM tailoring experience bullets", 55, "LLM tailoring of experience bullets per job...")
    if master_content:
        parsed = tailor_bullets_with_llm(parsed, company_name, jd_text, graphrag_context, gap_framing)

    # Step 6: formatting (72%)
    yield ("formatting", "Formatting & bold marking", 72, "Formatting tailored markdown and marking bold keywords...")
    tailored_text = format_tailored_markdown(parsed, keywords)
    raw_resume_path.write_text(tailored_text, encoding="utf-8")

    # Step 7: rendering_pdf (88%)
    yield ("rendering_pdf", "Rendering PDF", 88, "Rendering standard 2-page PDF resume using ReportLab...")
    render_pdf_resume(raw_resume_path, pdf_path)

    # Step 8: complete (100%)
    yield (
        "complete",
        "Done",
        100,
        {
            "raw_resume_path": str(raw_resume_path),
            "raw_resume": tailored_text,
            "pdf_path": str(pdf_path)
        }
    )

