"""
src/agents/orchestrator.py — Multi-Subagent Pipeline Orchestrator & Live Event Streamer.

Coordinates specialized subagents across ingestion, deterministic evaluation,
GraphRAG evidence retrieval, surgical delta optimization, fact checking, and PDF rendering.
"""

import logging
from pathlib import Path
from typing import Generator, Optional, Union

from src.config import MASTER_RESUME_PATH, OUTPUT_DIR_PATH
from src.generators.models import ResumeData
from src.generators.resume_generator import get_output_dir, _default_resume_data
from src.generators.resume_parser import parse_master_resume
from src.scrapers.job_parser import JobParser
from src.scrapers.models import JobPosting
from .ats_critic import ATSCriticAgent
from .fact_guard import FactGuardAgent
from .graph_retriever import GraphRAGRetrieverAgent
from .models import AgentEvent, CriticScoreBreakdown, IterationReport, OptimizationDiff
from .pdf_typesetter import PDFTypesetterAgent
from .surgical_optimizer import SurgicalOptimizerAgent

log = logging.getLogger(__name__)


class AgenticPipelineOrchestrator:
    """Coordinates specialized subagents in an autonomous closed-loop Evaluator-Optimizer flow."""

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
        """Execute autonomous agentic tailoring flow, yielding live AgentEvents."""
        # ── Step 1: Job Ingestion ──
        yield AgentEvent(
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

        yield AgentEvent(
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
        initial_breakdown = self.critic.evaluate(current_resume, posting)
        current_score = initial_breakdown.composite_score

        yield AgentEvent(
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
                yield AgentEvent(
                    step="converged",
                    agent="ATSCriticAgent",
                    status=f"Target ATS threshold reached ({current_score}% >= {min_score}%). Concluding refinement.",
                    payload={"final_score": current_score, "iteration": iteration - 1},
                )
                break

            # 4a. Graph Evidence Retrieval
            missing = initial_breakdown.missing_keywords[:5]
            yield AgentEvent(
                step="graph_retrieval",
                agent="GraphRAGRetrieverAgent",
                status=f"Retrieving verified candidate story evidence for missing skills: {', '.join(missing[:3]) if missing else 'core skills'}...",
            )
            evidence = self.retriever.retrieve_evidence(
                target_skills=missing,
                target_company=posting.company,
            )
            yield AgentEvent(
                step="graph_retrieval_complete",
                agent="GraphRAGRetrieverAgent",
                status=f"Knowledge Graph: Extracted {len(evidence)} verified candidate STAR story references.",
            )

            # 4b. Surgical Delta Optimization
            yield AgentEvent(
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

            # 4c. Anti-Hallucination Fact Guard Audit
            yield AgentEvent(
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

            # 4d. Re-evaluate with Critic
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

            yield AgentEvent(
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
                yield AgentEvent(
                    step="converged",
                    agent="ATSCriticAgent",
                    status=f"Score converged (+{score_delta}% delta). Exiting optimization loop.",
                    payload={"final_score": current_score, "iteration": iteration},
                )
                break

        # ── Step 5: PDF Compilation & Final Packaging ──
        yield AgentEvent(
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

        yield AgentEvent(
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
