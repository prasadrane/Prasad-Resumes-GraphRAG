"""
src/agents/models.py — Data models for specialized subagents, evaluation reports, and streaming events.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CriticScoreBreakdown(BaseModel):
    """Detailed deterministic scoring breakdown calculated by ATSCriticAgent."""
    composite_score: float = Field(..., description="Overall ATS score (0-100)")
    keyword_coverage: float = Field(..., description="Keyword alignment percentage (0-100)")
    impact_metric_score: float = Field(..., description="Action verbs and quantified metrics score (0-100)")
    bolding_compliance_score: float = Field(..., description="Bolding density (<20% cap) compliance (0-100)")
    page_budget_score: float = Field(..., description="2-page length budget compliance (0-100)")
    matched_keywords: List[str] = Field(default_factory=list)
    missing_keywords: List[str] = Field(default_factory=list)
    weakest_bullets: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Ranked list of weak bullets targeted for optimization: [{'job_index': 0, 'bullet_index': 1, 'role': 'Lead Architect', 'bullet': '...', 'score': 45.0}]"
    )


class OptimizationDiff(BaseModel):
    """Before/after diff for a surgically optimized bullet."""
    role_title: str
    original_bullet: str
    refined_bullet: str
    rationale: str = ""
    target_keywords: List[str] = Field(default_factory=list)


class IterationReport(BaseModel):
    """Record of an optimization iteration."""
    iteration_num: int
    score_before: float
    score_after: float
    diffs: List[OptimizationDiff] = Field(default_factory=list)
    status: str = "in_progress"  # in_progress, converged, max_iterations_reached


class AgentEvent(BaseModel):
    """Streaming event emitted by the orchestrator for CLI and SSE UI streams."""
    step: str = Field(..., description="e.g. ingestion, critic_eval, graph_retrieval, optimization, fact_guard, complete, error")
    agent: str = Field(..., description="Name of the executing specialized subagent")
    status: str = Field(..., description="Human-readable description of current action")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Detailed step data (scores, diffs, models)")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
