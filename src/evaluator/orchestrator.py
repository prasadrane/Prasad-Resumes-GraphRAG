"""
orchestrator.py ? Evaluator-in-the-loop multi-turn orchestration engine.

Coordinates:
1. Pre-generation feasibility checks & gap classification.
2. Tailoring blueprint synthesis grounded in story bank & master resume.
3. Resume & cover letter generation.
4. 4-dimension evaluation & auto-refinement multi-turn loop (capped at max_turns).
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any

from src.config import MASTER_RESUME_PATH
from src.evaluator.feasibility_checker import FeasibilityChecker
from src.evaluator.post_evaluator import PostEvaluator
from src.evaluator.models import (
    FeasibilityReport,
    EvaluationScorecard,
    TailoringStrategyBlueprint,
)
from src.generators.resume_generator import generate_tailored_resume, get_output_dir
from src.generators.cover_letter_generator import CoverLetterGenerator

logger = logging.getLogger(__name__)


def _load_master_content() -> str:
    """Load MASTER_RESUME.txt content if available."""
    if MASTER_RESUME_PATH and MASTER_RESUME_PATH.exists():
        try:
            return MASTER_RESUME_PATH.read_text(encoding="utf-8")
        except Exception as err:
            logger.warning("Could not read MASTER_RESUME_PATH: %s", err)
    return ""


class EvaluatorOrchestrator:
    """High-level orchestrator for evaluator-in-the-loop ATS tailoring."""

    def __init__(self, master_content: Optional[str] = None):
        self.master_content = master_content if master_content is not None else _load_master_content()
        self.feasibility_checker = FeasibilityChecker(master_content=self.master_content)
        self.post_evaluator = PostEvaluator(master_content=self.master_content)

    def run_agentic_pipeline(
        self,
        company_name: str,
        jd_text: str,
        max_turns: int = 2,
        auto_refine: bool = True,
        generate_cover_letter: bool = True,
        base_output_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Execute end-to-end evaluator-guided resume & cover letter generation pipeline.
        """
        # Step 1: Pre-generation Feasibility Check
        feasibility: FeasibilityReport = self.feasibility_checker.check_feasibility(jd_text, company_name)
        blueprint: TailoringStrategyBlueprint = self.feasibility_checker.build_strategy_blueprint(
            jd_text, company_name, feasibility
        )

        if feasibility.verdict == "DO_NOT_APPLY" and not auto_refine:
            return {
                "feasibility": feasibility,
                "blueprint": blueprint,
                "scorecard": None,
                "resume_text": "",
                "cover_letter_text": "",
                "status": "ABORTED_DO_NOT_APPLY",
            }

        # Step 2: Generation & Refinement Loop
        iteration = 1
        resume_res = generate_tailored_resume(
            company_name=company_name,
            jd_text=jd_text,
            base_output_dir=base_output_dir,
        )
        resume_text = resume_res.get("raw_resume", "")
        output_dir = resume_res.get("output_dir")

        cover_letter_text = ""
        if generate_cover_letter:
            try:
                cl_gen = CoverLetterGenerator()
                cl_data = cl_gen.generate(company=company_name, jd_text=jd_text)
                if hasattr(cl_data, "paragraphs"):
                    cover_letter_text = "\n\n".join(cl_data.paragraphs)
                if output_dir and cover_letter_text:
                    cl_path = Path(output_dir) / "Cover_Letter.txt"
                    cl_path.write_text(cover_letter_text, encoding="utf-8")
            except Exception as err:
                logger.warning("Cover letter generation encountered error: %s", err)

        # Step 3: 4-Dimension Post-Audit
        scorecard = self.post_evaluator.evaluate(
            resume_text=resume_text,
            cover_letter_text=cover_letter_text,
            jd_text=jd_text,
            iteration=iteration,
        )

        # Step 4: Iterative Refinement Loop
        while scorecard.verdict == "NEEDS_REFINEMENT" and iteration < max_turns and auto_refine:
            iteration += 1
            logger.info("Auto-refinement turn %d triggered: %s", iteration, scorecard.actionable_refinements)
            resume_res = generate_tailored_resume(
                company_name=company_name,
                jd_text=jd_text,
                base_output_dir=base_output_dir,
            )
            resume_text = resume_res.get("raw_resume", "")
            scorecard = self.post_evaluator.evaluate(
                resume_text=resume_text,
                cover_letter_text=cover_letter_text,
                jd_text=jd_text,
                iteration=iteration,
            )

        # Save evaluation scorecard report
        if output_dir:
            try:
                scorecard_path = Path(output_dir) / "evaluator_scorecard.json"
                scorecard_path.write_text(scorecard.model_dump_json(indent=2), encoding="utf-8")
            except Exception as err:
                logger.warning("Could not write evaluator scorecard: %s", err)

        return {
            "feasibility": feasibility,
            "blueprint": blueprint,
            "scorecard": scorecard,
            "resume_text": resume_text,
            "cover_letter_text": cover_letter_text,
            "output_dir": output_dir,
            "status": "COMPLETED",
        }
