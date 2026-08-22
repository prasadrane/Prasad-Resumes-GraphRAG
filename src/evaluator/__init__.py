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

__all__ = [
    "FillableGap",
    "FeasibilityReport",
    "TailoringStrategyBlueprint",
    "EvaluationScorecard",
]
