"""
Convert master resume from markdown to structured JSON before GraphRAG indexing.

Usage:
    python scripts/convert_structured_resume.py [--input <path>] [--output <path>]
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
log = logging.getLogger(__name__)


def _parse_master_resume(text: str) -> dict:
    """Parse the raw MASTER_RESUME.md into structured sections."""
    result: dict = {}

    # --- Contact / Header ---
    contact_line_match = re.search(
        r"^[^#].*\|.*\|.*\@.*\|\s*\[LinkedIn\]",
        text, re.MULTILINE
    )
    if contact_line_match:
        line = contact_line_match.group(0).strip()
        name_match = re.match(r"#?\s*(.+?)\s*[–—]\s*MASTER", line)
        result["name"] = name_match.group(1).strip() if name_match else ""
        # Extract LinkedIn URL
        linkedin = re.search(r'\[LinkedIn\]\((https?://[^)]+)\)', line)
        result["linkedin"] = linkedin.group(1) if linkedin else ""
        # Extract email
        email_match = re.search(r'✉️\s*(\S+@\S+)', line)
        result["email"] = email_match.group(1) if email_match else ""
        # Extract phone
        phone_match = re.search(r'📞\s*(\d[\d\-]*)', line)
        result["phone"] = phone_match.group(1) if phone_match else ""
        # Extract location
        loc_match = re.search(r'📍\s*([A-Za-z\s,IL]+)', line)
        result["location"] = loc_match.group(1).strip() if loc_match else ""
        # Extract portfolio
        port_match = re.search(r'💻\s*\[Portfolio\]\((https?://[^)]+)\)', line)
        result["portfolio"] = port_match.group(1) if port_match else ""

    # --- Sections by level 2 heading (##) ---
    sections: dict[str, str] = {}
    current_section: str | None = None
    lines = text.split("\n")
    i = 0
    header_done = False
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^##+\s*(.*)", line)
        if m and not header_done:
            if "Executive" in m.group(1) or "Summary" in m.group(1):
                current_section = "SUMMARY"
                header_done = True
                i += 1
                continue
            if "Technical Skills" in m.group(1) or "Skills" in m.group(1):
                current_section = "SKILLS"
                header_done = True
                i += 1
                continue
            if "Certifications" in m.group(1):
                current_section = "CERTIFICATIONS"
                header_done = True
                i += 1
                continue
            if "Experience" in m.group(1):
                current_section = "EXPERIENCE"
                header_done = True
                i += 1
                continue
            if "Education" in m.group(1):
                current_section = "EDUCATION"
                header_done = True
                i += 1
                continue
            if "Gap-Framing" in m.group(1):
                current_section = "GAP_FRAMING"
                header_done = True
                i += 1
                continue
            current_section = None
            i += 1
            continue
        if current_section:
            sections.setdefault(current_section, [])
            sections[current_section].append(line.strip())
        i += 1

    # --- Summary ---
    summary_variants: list[dict] = []
    summary_text = ""
    for line in sections.get("SUMMARY", []):
        m_summary = re.match(r"###\s*(Canonical|AI\s*/\s*LLM-Forward|Cloud\s*&\s*Reliability-Forward|Platform\s*&\s*DevEx-Forward|Security\s*&\s*Auth-Forward)\s*Summary", line)
        if m_summary:
            variant: dict = {"category": m_summary.group(1)}
            summary_text += line + "\n"
        elif line.startswith("- **") and "Summary" not in line:
            pass  # skip domain listing line
        elif line.startswith("- ") and summary_variants:
            cat = summary_variants[-1]["category"]
            content = re.sub(r"^- \*\*[^*]+\*\*:\s*", "", line)
            summary_variants.append({"category": cat, "text": content})
        elif line and not line.startswith("#") and summary_variants:
            summary_variants[-1]["text"] = line
        elif line and not line.startswith("#"):
            summary_text += line + "\n"

    result["summary_variants"] = summary_variants
    result["canonical_summary"] = summary_text.strip()

    # --- Skills ---
    skills: dict[str, list[str]] = {}
    current_cat = None
    for line in sections.get("SKILLS", []):
        cat_match = re.match(r"- \*\*([^*]+)\*\*:", line)
        if cat_match:
            current_cat = cat_match.group(1)
            skills[current_cat] = [s.strip() for s in re.split(r"[,•]", line.split(":", 1)[1].strip()) if s.strip()]
        elif current_cat and line.startswith("- **"):
            skills.setdefault(current_cat, [])
            skills[current_cat].append(line.strip())
        elif current_cat and line.startswith("-"):
            skills.setdefault(current_cat, [])
            skills[current_cat].append(re.sub(r"^-\s*", "", line).strip())

    result["skills"] = skills

    # --- Certifications ---
    certs: list[str] = []
    for line in sections.get("CERTIFICATIONS", []):
        if line.startswith("-") and "**" in line:
            cert_text = re.sub(r"^-\s*\[?", "", line)
            cert_text = cert_text.replace("**", "").strip()
            # Remove trailing link
            cert_text = re.sub(r"\]\(https?://[^)]+\).*", "", cert_text).strip()
            if cert_text:
                certs.append(cert_text)
        elif line and not line.startswith("-") and line.startswith("("):
            pass  # planned certification note
    result["certifications"] = certs

    # --- Experience ---
    jobs: list[dict] = []
    exp_lines = sections.get("EXPERIENCE", [])
    job_idx = -1
    bullet_stories: dict[int, list[str]] = {}  # job_idx -> [story_text]
    current_job: dict | None = None
    current_story: list[str] = []

    def flush_job() -> None:
        nonlocal current_job, current_story
        if current_job is None:
            return
        bullets: list[str] = []
        for bl in current_job.pop("_bullets", []):
            bullets.append(bl)
        current_job["bullets"] = bullets
        current_job["bullet_stories"] = bullet_stories.get(job_idx, [])
        jobs.append(current_job)
        current_job = None
        current_story = []

    for line in exp_lines:
        # Story header
        story_m = re.match(r"####\s+(Story \d+)\s?[–—]\s*(.+)", line)
        if story_m:
            flush_job()
            current_story = [f"{story_m.group(1)}: {story_m.group(2)}"]
            continue
        if current_story and line.startswith("-"):
            current_story.append(line)
            continue

        # Job header pattern: ### **Title** — *Company*
        job_m = re.match(
            r"###\s+\*\*([^*]+?)\*\*\s*[—––]\s*\*([^*]+?)\*?(?:\s*\*\*|)",
            line
        )
        if not job_m:
            job_m = re.match(
                r"###\s+(.+?)\s*[—––]\s*(.+?)(?:\s*$)",
                line
            )
        if job_m:
            flush_job()
            job_idx += 1
            title = job_m.group(1).strip()
            company = job_m.group(2).strip()
            current_job = {
                "title": title,
                "company": company,
                "location": "",
                "dates": "",
                "_bullets": [],
            }
            bullet_stories[job_idx] = []
            continue

        # Location/dates subheading
        if current_job is not None and "📍" in line:
            loc_m = re.search(r"📍\s*([^\|]+?)\|\s*🗓️\s*(.+)", line)
            if loc_m:
                current_job["location"] = loc_m.group(1).strip()
                current_job["dates"] = loc_m.group(2).strip()
            continue

        # Bullet lines (only within a job context)
        if current_job is not None and line.startswith("- "):
            current_job["_bullets"].append(line[2:].strip())
            continue

        # Flush stories from last story block into current job
        if current_job is not None and current_story and not line.startswith("-"):
            story_text = "\n".join(current_story)
            bullet_stories[job_idx].append(story_text)
            current_story = []

    flush_job()

    result["jobs"] = jobs
    result["experience_sections"] = {str(k): v for k, v in bullet_stories.items()}
    result["raw_experience"] = sections.get("EXPERIENCE", [])

    # --- Gap Framing ---
    gap_raw = sections.get("GAP_FRAMING", [])
    result["gap_framing"] = gap_raw if gap_raw else []

    # --- Education (if present) ---
    edu_lines = sections.get("EDUCATION", [])
    if edu_lines:
        result["education"] = [l for l in edu_lines if l and l.startswith("-")]

    return result


def main() -> None:
    ap = argparse.ArgumentParser(description="Convert MASTER_RESUME.txt to structured JSON")
    ap.add_argument("--input", default=None, help="Path to MASTER_RESUME.txt")
    ap.add_argument("--output", default=None, help="Output JSON path (default: input/.structured.json)")
    args = ap.parse_args()

    input_path = Path(args.input) if args.input else Path(__file__).resolve().parent.parent / "input" / "MASTER_RESUME.txt"
    output_path = Path(args.output) if args.output else Path(str(input_path) + ".structured.json")

    if not input_path.exists():
        log.error("Input not found: %s", input_path)
        sys.exit(1)

    text = input_path.read_text(encoding="utf-8")
    structured = _parse_master_resume(text)

    output_path.write_text(json.dumps(structured, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote structured resume to {output_path}")

    # Print quick stats
    print(f"  Jobs parsed       : {len(structured.get('jobs', []))}")
    print(f"  Skill categories  : {len(structured.get('skills', {}))}")
    print(f"  Certifications    : {len(structured.get('certifications', []))}")
    print(f"  Summary variants  : {len(structured.get('summary_variants', []))}")


if __name__ == "__main__":
    main()
