"""
models.py ? Pydantic models for Evaluator Agent in-the-loop workflows.
"""

from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, Field


class FillableGap(BaseModel):
    """Represents a missing JD requirement that can be fulfilled via candidate story bank or transferable experience."""
    skill: str
    suggested_story_id: Optional[str] = None
    company_context: str
    evidence_snippet: str


class FeasibilityReport(BaseModel):
    """Pre-generation feasibility assessment of candidate fit against a target Job Description."""
    baseline_match_pct: float
    hard_skills_match_pct: float
    soft_skills_match_pct: float
    matched_skills: List[str] = Field(default_factory=list)
    fillable_gaps: List[FillableGap] = Field(default_factory=list)
    unfillable_gaps: List[str] = Field(default_factory=list)
    verdict: Literal["STRONG_MATCH", "TAILORABLE", "HIGH_GAP", "DO_NOT_APPLY"]
    rationale: str


class TailoringStrategyBlueprint(BaseModel):
    """Structured blueprint guiding the generator with specific story mappings and keywords."""
    target_role_title: str
    target_company: str
    recommended_summary_focus: str
    role_story_mappings: Dict[str, List[str]] = Field(default_factory=dict)
    must_include_keywords: List[str] = Field(default_factory=list)
    cover_letter_hook_theme: str


class EvaluationScorecard(BaseModel):
    """Post-generation 4-dimension audit scorecard and refinement critique."""
    iteration: int
    ats_score: float
    hard_skill_match_pct: float
    soft_skill_match_pct: float
    story_grounding_score: float  # 0.0 - 100.0%
    format_compliance: bool
    cover_letter_score: float     # 0.0 - 100.0%
    verdict: Literal["APPROVED", "NEEDS_REFINEMENT", "CRITICAL_GAP"]
    critique_summary: str
    actionable_refinements: List[str] = Field(default_factory=list)
