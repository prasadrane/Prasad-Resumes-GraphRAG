"""
src/evaluator ? Evaluator Agent in-the-loop package for feasibility checking,
anti-hallucination story grounding, ATS auditing, and multi-turn refinement.
"""

from .models import (
    FillableGap,
    FeasibilityReport,
    TailoringStrategyBlueprint,
    EvaluationScorecard,
)
from .feasibility_checker import FeasibilityChecker
from .grounding_auditor import GroundingAuditor
from .post_evaluator import PostEvaluator
from .orchestrator import EvaluatorOrchestrator

__all__ = [
    "FillableGap",
    "FeasibilityReport",
    "TailoringStrategyBlueprint",
    "EvaluationScorecard",
    "FeasibilityChecker",
    "GroundingAuditor",
    "PostEvaluator",
    "EvaluatorOrchestrator",
]
