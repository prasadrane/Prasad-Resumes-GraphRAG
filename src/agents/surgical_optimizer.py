"""
src/agents/surgical_optimizer.py — Surgical Delta Bullet Optimizer Subagent.

Optimizes only the lowest-scoring bullets (bottom 20-30%) with missing target skills,
achieving >70% token savings compared to full resume regeneration.
"""

import logging
import re
from typing import List, Tuple, Union

from src.gateway.facade import call_serverless_llm
from src.generators.models import ResumeData
from src.scrapers.models import JobPosting
from .models import CriticScoreBreakdown, OptimizationDiff

log = logging.getLogger(__name__)

OPTIMIZER_SYSTEM_PROMPT = """You are an elite ATS Resume Optimization Specialist.
Your task is to surgically rewrite only the specified weak resume bullets.

STRICT OPTIMIZATION RULES:
1. Grounding & Zero Hallucination: Use only the candidate's verified evidence. Do NOT fabricate companies, dates, or false metrics.
2. Strong Action Verbs: Begin each bullet with a Tier-1 action verb (e.g. Architected, Engineered, Spearheaded, Orchestrated, Designed).
3. Quantifiable Impact: Include concrete metrics (e.g. 40%, 50k req/s, 10M events, $2M, 50ms).
4. Bold Key Terms: Use markdown bold (**keyword**) for key technologies and metrics. Total bold text MUST be under 20% of the bullet length (max 3 bold phrases).
5. Output Format:
For each bullet, output strictly in this format:
Role: <role title>
Original: <original bullet text>
Refined: <refined bullet text>
Rationale: <brief 1-sentence reason>
"""


class SurgicalOptimizerAgent:
    """Specialized Subagent for targeted delta bullet refinement."""

    def __init__(self):
        pass

    def optimize_delta(
        self,
        resume: ResumeData,
        job_posting: Union[JobPosting, str],
        critic_breakdown: CriticScoreBreakdown,
        evidence: List[str],
    ) -> Tuple[ResumeData, List[OptimizationDiff]]:
        """Surgically optimize the weakest bullets in the resume."""
        weak_bullets = critic_breakdown.weakest_bullets
        if not weak_bullets:
            return resume, []

        missing_skills = critic_breakdown.missing_keywords[:6]
        evidence_text = "\n".join([f"- {ev}" for ev in evidence]) if evidence else "None provided."

        target_company = job_posting.company if isinstance(job_posting, JobPosting) else "Target Company"
        target_role = job_posting.role_title if isinstance(job_posting, JobPosting) else "Software Professional"

        # Build prompt listing only the weak bullets
        bullet_list_str = ""
        for i, item in enumerate(weak_bullets, 1):
            bullet_list_str += f"{i}. Role: {item['role']} at {item.get('company', '')}\n   Current Bullet: {item['bullet']}\n"

        prompt = (
            f"Target Company: {target_company}\n"
            f"Target Role: {target_role}\n"
            f"Missing Key Skills to Incorporate: {', '.join(missing_skills) if missing_skills else 'Observability, High-Throughput'}\n\n"
            f"Verified Candidate Evidence:\n{evidence_text}\n\n"
            f"Bullets to Surgically Refine:\n{bullet_list_str}\n\n"
            f"Please rewrite each bullet above following all optimization rules."
        )

        try:
            llm_response = call_serverless_llm(
                prompt=prompt,
                system_prompt=OPTIMIZER_SYSTEM_PROMPT,
                temperature=0.2,
            )
            return self._apply_refinements(resume, weak_bullets, llm_response, missing_skills)
        except Exception as exc:
            log.warning("Surgical optimization LLM call failed: %s. Returning unmodified resume.", exc)
            return resume, []

    def _apply_refinements(
        self,
        resume: ResumeData,
        weak_bullets: List[dict],
        llm_response: str,
        missing_skills: List[str],
    ) -> Tuple[ResumeData, List[OptimizationDiff]]:
        """Parse refined bullets from LLM response and apply them back into ResumeData."""
        refined_resume = resume.model_copy(deep=True)
        diffs: List[OptimizationDiff] = []

        # Parse sections from response
        # Matches blocks with Role:, Original:, Refined:, Rationale:
        pattern = re.compile(
            r"Role:\s*(?P<role>[^\n]+)\s*\n"
            r"Original:\s*(?P<original>[^\n]+)\s*\n"
            r"Refined:\s*(?P<refined>[^\n]+)\s*\n"
            r"Rationale:\s*(?P<rationale>[^\n]+)",
            re.IGNORECASE
        )

        matches = list(pattern.finditer(llm_response))

        if not matches:
            # Fallback simple line-by-line parsing if formatting deviated slightly
            lines = [l.strip() for l in llm_response.splitlines() if l.strip()]
            for item in weak_bullets:
                j_idx = item["job_index"]
                b_idx = item["bullet_index"]
                orig = item["bullet"]
                # Try to find a refined line
                for line in lines:
                    if line.startswith("Refined:") or (line.startswith("**") and orig[:15] not in line):
                        refined_text = re.sub(r"^Refined:\s*", "", line).strip()
                        if refined_text:
                            refined_resume.jobs[j_idx].bullets[b_idx] = refined_text
                            diffs.append(OptimizationDiff(
                                role_title=item["role"],
                                original_bullet=orig,
                                refined_bullet=refined_text,
                                rationale="Enhanced action verb and ATS keyword alignment.",
                                target_keywords=missing_skills[:3],
                            ))
                            break
            return refined_resume, diffs

        for match in matches:
            role = match.group("role").strip()
            orig = match.group("original").strip()
            refined = match.group("refined").strip()
            rationale = match.group("rationale").strip()

            # Locate matching bullet in weak_bullets or resume jobs
            applied = False
            for item in weak_bullets:
                j_idx = item["job_index"]
                b_idx = item["bullet_index"]
                orig_item = item["bullet"]
                if orig.lower() in orig_item.lower() or orig_item.lower() in orig.lower() or len(weak_bullets) == 1:
                    refined_resume.jobs[j_idx].bullets[b_idx] = refined
                    diffs.append(OptimizationDiff(
                        role_title=role or item["role"],
                        original_bullet=orig_item,
                        refined_bullet=refined,
                        rationale=rationale,
                        target_keywords=missing_skills[:3],
                    ))
                    applied = True
                    break

            if not applied and weak_bullets:
                # Apply to first weak bullet
                item = weak_bullets[0]
                refined_resume.jobs[item["job_index"]].bullets[item["bullet_index"]] = refined
                diffs.append(OptimizationDiff(
                    role_title=role or item["role"],
                    original_bullet=item["bullet"],
                    refined_bullet=refined,
                    rationale=rationale,
                    target_keywords=missing_skills[:3],
                ))

        return refined_resume, diffs
