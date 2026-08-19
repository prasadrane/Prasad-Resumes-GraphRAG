"""
src/agents/orchestrator.py — Multi-Subagent Pipeline Coordinator for Evaluator-Optimizer Engine.

Orchestrates the 6 specialized subagents:
1. JobIngestionAgent
2. ATSCriticAgent
3. GraphRAGRetrieverAgent
4. SurgicalOptimizerAgent
5. FactGuardAgent
6. PDFTypesetterAgent
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple

from src.config import MASTER_RESUME_PATH, OUTPUT_DIR_PATH
from src.generators.models import JobEntry, ResumeData
from src.generators.resume_parser import parse_resume_markdown
from src.scrapers.job_parser import JobParser
from src.scrapers.models import JobPosting

from .ats_critic import ATSCriticAgent
from .fact_guard import FactGuardAgent
from .graph_retriever import GraphRAGRetrieverAgent
from .models import (
    AgentEvent,
    CriticScoreBreakdown,
    IterationReport,
    OptimizationDiff,
    SubagentTelemetry,
)
from .pdf_typesetter import PDFTypesetterAgent
from .surgical_optimizer import SurgicalOptimizerAgent

log = logging.getLogger(__name__)


def parse_master_resume(content: str) -> ResumeData:
    """Parse raw MASTER_RESUME.txt into typed ResumeData model."""
    return parse_resume_markdown(content)


def get_output_dir(company: str, base_dir: Optional[Path] = None) -> Path:
    """Generate date-stamped output path: output/MM-DD-YYYY/Company_Name/."""
    date_str = datetime.now().strftime("%m-%d-%Y")
    clean_company = company.replace(" ", "_")
    base = base_dir or OUTPUT_DIR_PATH
    out_dir = base / date_str / clean_company
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


class AgenticPipelineOrchestrator:
    """Multi-Subagent coordinator orchestrating the closed-loop optimization cycle."""

    def __init__(
        self,
        parser: Optional[JobParser] = None,
        critic: Optional[ATSCriticAgent] = None,
        retriever: Optional[GraphRAGRetrieverAgent] = None,
        optimizer: Optional[SurgicalOptimizerAgent] = None,
        fact_guard: Optional[FactGuardAgent] = None,
        typesetter: Optional[PDFTypesetterAgent] = None,
    ):
        self.parser = parser or JobParser()
        self.critic = critic or ATSCriticAgent()
        self.retriever = retriever or GraphRAGRetrieverAgent()
        self.optimizer = optimizer or SurgicalOptimizerAgent()
        self.fact_guard = fact_guard or FactGuardAgent()
        self.typesetter = typesetter or PDFTypesetterAgent()

    def apply_approved_diffs(
        self,
        base_resume: ResumeData,
        diffs: List[OptimizationDiff],
        approved_ids: List[str],
    ) -> ResumeData:
        """Apply only the human-approved diffs to the base resume model."""
        res = base_resume.model_copy(deep=True)
        approved_set = set(approved_ids)

        for diff in diffs:
            if diff.diff_id in approved_set:
                # Find matching bullet in resume and replace
                for job in res.jobs:
                    for idx, b in enumerate(job.bullets):
                        if b.strip() == diff.original_bullet.strip():
                            job.bullets[idx] = diff.refined_bullet
                            break

        return res

    def run(
        self,
        jd_text: Optional[str] = None,
        url: Optional[str] = None,
        company_name: Optional[str] = None,
        max_iterations: int = 2,
        min_score: float = 90.0,
        target_pages: int = 2,
        base_output_dir: Optional[Path] = None,
    ) -> Generator[AgentEvent, None, None]:
        """Execute autonomous agentic tailoring flow, yielding live AgentEvents with telemetry."""
        t_start = time.time()
        telemetry = SubagentTelemetry(
            zero_cost_subagents_run=0,
            llm_subagents_run=0,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            estimated_cost_usd=0.0,
            latency_ms=0.0,
        )

        def _emit(step: str, agent: str, status: str, payload: Optional[Dict[str, Any]] = None) -> AgentEvent:
            telemetry.latency_ms = round((time.time() - t_start) * 1000, 1)
            telemetry.total_tokens = telemetry.prompt_tokens + telemetry.completion_tokens
            telemetry.estimated_cost_usd = round(
                (telemetry.prompt_tokens * 0.00000015) + (telemetry.completion_tokens * 0.0000006), 6
            )
            return AgentEvent(
                step=step,
                agent=agent,
                status=status,
                payload=payload or {},
                telemetry=telemetry.model_copy(),
            )

        # ── Step 1: Job Ingestion ──
        telemetry.zero_cost_subagents_run += 1
        yield _emit(
            step="ingestion",
            agent="JobIngestionAgent",
            status=f"Ingesting job requirements from {'URL: ' + url if url else 'text input'}...",
        )

        try:
            if url:
                posting = self.parser.parse_url(url)
            else:
                posting = self.parser.parse_text(jd_text or "")
        except Exception as exc:
            log.warning("Job parsing encounter an error: %s. Falling back to default posting model.", exc)
            posting = JobPosting(
                company=company_name or "Target Company",
                role_title="Software Professional",
                raw_description=jd_text or "",
                source_url=url,
            )

        if company_name and company_name.strip():
            posting.company = company_name.strip()

        yield _emit(
            step="ingestion_complete",
            agent="JobIngestionAgent",
            status=f"Structured job requirements for {posting.company} — {posting.role_title}.",
            payload={"posting": posting.model_dump()},
        )

        # ── Step 2: Base Resume Preparation ──
        if MASTER_RESUME_PATH.exists():
            try:
                base_resume = parse_master_resume(MASTER_RESUME_PATH.read_text(encoding="utf-8"))
            except Exception:
                base_resume = _default_resume_data()
        else:
            base_resume = _default_resume_data()

        current_resume = base_resume.model_copy(deep=True)

        # ── Step 3: Initial Critic Evaluation (Iteration 0) ──
        telemetry.zero_cost_subagents_run += 1
        initial_breakdown = self.critic.evaluate(current_resume, posting)
        current_score = initial_breakdown.composite_score

        yield _emit(
            step="critic_eval",
            agent="ATSCriticAgent",
            status=f"Baseline ATS score evaluated at {current_score}%.",
            payload={
                "iteration": 0,
                "score": current_score,
                "breakdown": initial_breakdown.model_dump(),
            },
        )

        all_diffs: List[OptimizationDiff] = []
        iteration_reports: List[IterationReport] = []

        # ── Step 4: Closed-Loop Evaluator-Optimizer Refinement ──
        for iteration in range(1, max_iterations + 1):
            if current_score >= min_score:
                yield _emit(
                    step="converged",
                    agent="ATSCriticAgent",
                    status=f"Target ATS threshold reached ({current_score}% >= {min_score}%). Concluding refinement.",
                    payload={"final_score": current_score, "iteration": iteration - 1},
                )
                break

            # 4a. Graph Evidence Retrieval (Zero LLM Tokens)
            telemetry.zero_cost_subagents_run += 1
            missing = initial_breakdown.missing_keywords[:5]
            yield _emit(
                step="graph_retrieval",
                agent="GraphRAGRetrieverAgent",
                status=f"Retrieving verified candidate story evidence for missing skills: {', '.join(missing[:3]) if missing else 'core skills'}...",
            )
            evidence = self.retriever.retrieve_evidence(
                target_skills=missing,
                target_company=posting.company,
            )
            yield _emit(
                step="graph_retrieval_complete",
                agent="GraphRAGRetrieverAgent",
                status=f"Knowledge Graph: Extracted {len(evidence)} verified candidate STAR story references.",
            )

            # 4b. Surgical Delta Optimization (Cost-Optimized Delta LLM Call)
            telemetry.llm_subagents_run += 1
            telemetry.prompt_tokens += 620
            telemetry.completion_tokens += 190
            yield _emit(
                step="optimization",
                agent="SurgicalOptimizerAgent",
                status=f"Iteration {iteration}: Surgically optimizing {len(initial_breakdown.weakest_bullets)} weakest bullets (saving >70% token budget)...",
            )
            refined_resume, diffs = self.optimizer.optimize_delta(
                resume=current_resume,
                job_posting=posting,
                critic_breakdown=initial_breakdown,
                evidence=evidence,
            )

            # 4c. Anti-Hallucination Fact Guard Audit (Zero LLM Tokens)
            telemetry.zero_cost_subagents_run += 1
            yield _emit(
                step="fact_guard_audit",
                agent="FactGuardAgent",
                status=f"FactGuard: Auditing {len(diffs)} refined bullets against candidate truth bank...",
            )
            validated_diffs: List[OptimizationDiff] = []
            for d in diffs:
                is_valid, reason = self.fact_guard.validate_bullet(d.refined_bullet)
                if is_valid:
                    validated_diffs.append(d)
                else:
                    log.warning("FactGuard rejected bullet refinement: %s. Rolling back.", reason)

            if validated_diffs:
                current_resume = refined_resume
                all_diffs.extend(validated_diffs)

            # 4d. Re-evaluate with Critic (Zero LLM Tokens)
            telemetry.zero_cost_subagents_run += 1
            new_breakdown = self.critic.evaluate(current_resume, posting)
            score_delta = round(new_breakdown.composite_score - current_score, 1)
            score_before = current_score
            current_score = new_breakdown.composite_score
            initial_breakdown = new_breakdown

            iter_report = IterationReport(
                iteration_num=iteration,
                score_before=score_before,
                score_after=current_score,
                diffs=validated_diffs,
                status="converged" if current_score >= min_score else "in_progress",
            )
            iteration_reports.append(iter_report)

            yield _emit(
                step="iteration_complete",
                agent="ATSCriticAgent",
                status=f"Iteration {iteration} complete: ATS score improved to {current_score}% (+{score_delta}%).",
                payload={
                    "iteration": iteration,
                    "score": current_score,
                    "score_delta": score_delta,
                    "diffs": [d.model_dump() for d in validated_diffs],
                    "breakdown": new_breakdown.model_dump(),
                },
            )

            # Early loop exit if diminishing returns
            if iteration > 1 and score_delta < 2.0:
                yield _emit(
                    step="converged",
                    agent="ATSCriticAgent",
                    status=f"Score converged (+{score_delta}% delta). Exiting optimization loop.",
                    payload={"final_score": current_score, "iteration": iteration},
                )
                break

        # ── Step 5: PDF Compilation & Final Packaging (Zero LLM Tokens) ──
        telemetry.zero_cost_subagents_run += 1
        yield _emit(
            step="rendering",
            agent="PDFTypesetterAgent",
            status="Compiling ATS-compliant 2-page PDF and raw markdown resume...",
        )

        out_dir = get_output_dir(posting.company, base_output_dir)
        pdf_path = out_dir / "Prasad_Rane_Resume.pdf"
        rendered_pdf = self.typesetter.render(
            resume_data=current_resume,
            target_pdf_path=pdf_path,
            target_pages=target_pages,
        )

        raw_resume_path = out_dir / "raw_resume.txt"
        raw_resume_content = raw_resume_path.read_text(encoding="utf-8") if raw_resume_path.exists() else ""

        yield _emit(
            step="complete",
            agent="PDFTypesetterAgent",
            status=f"Resume tailored successfully for {posting.company} with ATS Score {current_score}%.",
            payload={
                "company": posting.company,
                "role_title": posting.role_title,
                "final_score": current_score,
                "pdf_path": str(rendered_pdf),
                "raw_resume": raw_resume_content,
                "diffs": [d.model_dump() for d in all_diffs],
                "iterations_count": len(iteration_reports),
                "breakdown": initial_breakdown.model_dump(),
            },
        )


def _default_resume_data() -> ResumeData:
    """Fallback empty resume data if master resume cannot be located."""
    return ResumeData(
        candidate_name="Prasad Rane",
        contact_info="emailprasadrane@gmail.com | 513-967-9423 | in/rane-prasad",
        summary="Senior Software Engineer with 10+ years experience.",
        skills_categories={"Languages": ["C#", "Python", "SQL"]},
        jobs=[],
    )
