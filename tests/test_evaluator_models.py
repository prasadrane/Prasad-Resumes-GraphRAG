# tests/test_evaluator_models.py
import pytest
from src.evaluator.models import (
    FillableGap,
    FeasibilityReport,
    TailoringStrategyBlueprint,
    EvaluationScorecard,
)

def test_fillable_gap_creation():
    gap = FillableGap(
        skill="AWS Fargate",
        suggested_story_id="STORY_FARGATE_01",
        company_context="TechCorp",
        evidence_snippet="Migrated legacy containers to AWS Fargate",
    )
    assert gap.skill == "AWS Fargate"
    assert gap.suggested_story_id == "STORY_FARGATE_01"
    assert gap.company_context == "TechCorp"
    assert "Fargate" in gap.evidence_snippet

def test_feasibility_report_instantiation():
    gap = FillableGap(
        skill="AWS Fargate",
        suggested_story_id="STORY_FARGATE_01",
        company_context="TechCorp",
        evidence_snippet="Migrated legacy containers to AWS Fargate",
    )
    report = FeasibilityReport(
        baseline_match_pct=82.5,
        hard_skills_match_pct=80.0,
        soft_skills_match_pct=90.0,
        matched_skills=["Python", "AWS", "Docker"],
        fillable_gaps=[gap],
        unfillable_gaps=["Embedded C++"],
        verdict="TAILORABLE",
        rationale="Strong backend alignment with minor fillable gaps.",
    )
    assert report.verdict == "TAILORABLE"
    assert report.baseline_match_pct == 82.5
    assert len(report.fillable_gaps) == 1
    assert report.fillable_gaps[0].skill == "AWS Fargate"
    assert report.unfillable_gaps == ["Embedded C++"]

def test_tailoring_strategy_blueprint():
    blueprint = TailoringStrategyBlueprint(
        target_role_title="Senior Backend Engineer",
        target_company="Stripe",
        recommended_summary_focus="Emphasize high-throughput distributed systems",
        role_story_mappings={"TechCorp": ["STORY_01", "STORY_02"]},
        must_include_keywords=["Python", "Kafka", "AWS"],
        cover_letter_hook_theme="Architecting scalable payment pipelines",
    )
    assert blueprint.target_company == "Stripe"
    assert "Python" in blueprint.must_include_keywords
    assert blueprint.role_story_mappings["TechCorp"] == ["STORY_01", "STORY_02"]

def test_evaluation_scorecard_instantiation():
    scorecard = EvaluationScorecard(
        iteration=1,
        ats_score=88.0,
        hard_skill_match_pct=85.0,
        soft_skill_match_pct=95.0,
        story_grounding_score=100.0,
        format_compliance=True,
        cover_letter_score=90.0,
        verdict="APPROVED",
        critique_summary="Resume and cover letter are fully aligned and authentic.",
        actionable_refinements=[],
    )
    assert scorecard.verdict == "APPROVED"
    assert scorecard.story_grounding_score == 100.0
    assert scorecard.ats_score == 88.0
    assert scorecard.format_compliance is True
