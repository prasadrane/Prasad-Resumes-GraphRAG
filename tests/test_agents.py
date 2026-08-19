"""
test_agents.py — Comprehensive unit tests for specialized subagents and orchestrator.
"""

from unittest.mock import MagicMock, patch
import pytest

from src.generators.models import JobEntry, ResumeData
from src.scrapers.models import JobPosting
from src.agents.models import (
    AgentEvent,
    CriticScoreBreakdown,
    OptimizationDiff,
    IterationReport,
)
from src.agents.ats_critic import ATSCriticAgent
from src.agents.graph_retriever import GraphRAGRetrieverAgent
from src.agents.surgical_optimizer import SurgicalOptimizerAgent
from src.agents.fact_guard import FactGuardAgent
from src.agents.pdf_typesetter import PDFTypesetterAgent
from src.agents.orchestrator import AgenticPipelineOrchestrator


@pytest.fixture
def sample_resume_data() -> ResumeData:
    return ResumeData(
        name="Prasad Rane",
        title="Lead Cloud Architect & AI Systems Engineer",
        summary="Senior Cloud Architect with 14+ years designing scalable AWS microservices.",
        jobs=[
            JobEntry(
                company="Current Corp",
                title="Lead Architect",
                location="Dallas, TX",
                dates="Jan 2022 - Present",
                bullets=[
                    "Architected scalable cloud microservices handling 50k requests/sec using AWS ECS and Python.",
                    "Managed general cloud monitoring and daily operations across multiple teams.",
                    "Designed automated CI/CD pipelines reducing deployment friction.",
                ]
            ),
            JobEntry(
                company="Past Corp",
                title="Senior Software Engineer",
                location="Irving, TX",
                dates="Mar 2018 - Dec 2021",
                bullets=[
                    "Engineered distributed event streaming pipelines processing 10M events daily with Kafka.",
                    "Maintained internal documentation and bug tickets.",
                ]
            )
        ],
        skills=["Cloud: AWS, Kubernetes, Docker, Terraform", "Backend: Python, C#, FastAPI, Kafka"],
        certifications=["AWS Certified Solutions Architect"],
        education=["B.S. in Computer Engineering"]
    )


@pytest.fixture
def sample_job_posting() -> JobPosting:
    return JobPosting(
        company="Databricks",
        role_title="Staff Infrastructure Architect",
        location="Remote",
        required_skills=["AWS", "Kubernetes", "Prometheus", "OpenTelemetry", "Terraform"],
        preferred_skills=["Kafka", "FastAPI"],
        responsibilities=["Build observable cloud infrastructure", "Scale high-throughput streaming systems"],
        raw_description="Looking for a Staff Infrastructure Architect with deep experience in AWS, Kubernetes, Prometheus, OpenTelemetry, Terraform, and Kafka.",
        source_url="https://boards.greenhouse.io/databricks/jobs/999"
    )


# ── 1. ATSCriticAgent Tests ──────────────────────────────────────────────────

def test_ats_critic_deterministic_evaluation(sample_resume_data, sample_job_posting):
    critic = ATSCriticAgent()
    breakdown = critic.evaluate(sample_resume_data, sample_job_posting)
    
    assert isinstance(breakdown, CriticScoreBreakdown)
    assert 0.0 <= breakdown.composite_score <= 100.0
    assert 0.0 <= breakdown.keyword_coverage <= 100.0
    assert 0.0 <= breakdown.impact_metric_score <= 100.0
    assert 0.0 <= breakdown.bolding_compliance_score <= 100.0
    assert 0.0 <= breakdown.page_budget_score <= 100.0
    
    # Missing skills should contain Prometheus and OpenTelemetry
    missing_upper = {s.upper() for s in breakdown.missing_keywords}
    assert "PROMETHEUS" in missing_upper or "OPENTELEMETRY" in missing_upper
    
    # Weakest bullets should be identified
    assert len(breakdown.weakest_bullets) > 0
    weakest_texts = [b["bullet"] for b in breakdown.weakest_bullets]
    assert any("monitoring" in b.lower() or "documentation" in b.lower() for b in weakest_texts)


# ── 2. GraphRAGRetrieverAgent Tests ──────────────────────────────────────────

def test_graph_retriever_finds_evidence():
    retriever = GraphRAGRetrieverAgent()
    evidence = retriever.retrieve_evidence(
        target_skills=["Prometheus", "OpenTelemetry", "Kafka"],
        target_company="Databricks"
    )
    assert isinstance(evidence, list)
    # Returns relevant career stories/triples or fallback candidate knowledge
    assert len(evidence) > 0


# ── 3. SurgicalOptimizerAgent Tests ──────────────────────────────────────────

def test_surgical_optimizer_rewrites_weak_bullets_only(sample_resume_data, sample_job_posting):
    critic = ATSCriticAgent()
    breakdown = critic.evaluate(sample_resume_data, sample_job_posting)
    
    optimizer = SurgicalOptimizerAgent()
    
    mock_llm_response = (
        "Role: Lead Architect\n"
        "Original: Managed general cloud monitoring and daily operations across multiple teams.\n"
        "Refined: **Architected Prometheus and OpenTelemetry** observability infrastructure, improving MTTR by **45%**.\n"
        "Rationale: Injected required Prometheus and OpenTelemetry technologies with quantifiable impact."
    )
    
    with patch("src.agents.surgical_optimizer.call_serverless_llm", return_value=mock_llm_response):
        new_resume, diffs = optimizer.optimize_delta(
            resume=sample_resume_data,
            job_posting=sample_job_posting,
            critic_breakdown=breakdown,
            evidence=["Integrated Prometheus/Grafana and OpenTelemetry tracing for microservices."]
        )
        
        assert len(diffs) >= 1
        assert isinstance(diffs[0], OptimizationDiff)
        assert "Prometheus" in diffs[0].refined_bullet or "Prometheus" in str(diffs[0])
        # Verify un-targeted strong bullet was untouched
        assert "Architected scalable cloud microservices handling 50k requests/sec" in new_resume.jobs[0].bullets[0]


# ── 4. FactGuardAgent Tests ──────────────────────────────────────────────────

def test_fact_guard_accepts_valid_bullet():
    guard = FactGuardAgent()
    valid_bullet = "Architected AWS microservices using Python and Docker, reducing latency by 35%."
    is_valid, reason = guard.validate_bullet(valid_bullet)
    assert is_valid is True


def test_fact_guard_rejects_hallucinated_technologies():
    guard = FactGuardAgent()
    hallucinated_bullet = "Engineered blockchain smart contracts using Solidity, Vyper, and Ethereum."
    is_valid, reason = guard.validate_bullet(hallucinated_bullet)
    assert is_valid is False
    assert "Solidity" in reason or "Vyper" in reason or "Ethereum" in reason or "unverified" in reason.lower()


# ── 5. PDFTypesetterAgent Tests ──────────────────────────────────────────────

def test_pdf_typesetter_formats_markdown_and_renders(sample_resume_data, tmp_path):
    typesetter = PDFTypesetterAgent()
    out_file = tmp_path / "test_resume.pdf"
    
    with patch("src.agents.pdf_typesetter.render_pdf_resume", return_value=out_file) as mock_render:
        res_path = typesetter.render(
            resume_data=sample_resume_data,
            target_pdf_path=out_file,
            target_pages=2
        )
        assert mock_render.called
        assert res_path == out_file


# ── 6. AgenticPipelineOrchestrator E2E Tests ─────────────────────────────────

def test_agentic_orchestrator_convergence_flow(sample_resume_data, sample_job_posting, tmp_path):
    orchestrator = AgenticPipelineOrchestrator()
    
    # Mock LLM and PDF generation
    with patch.object(orchestrator.parser, "parse_text", return_value=sample_job_posting), \
         patch.object(orchestrator.optimizer, "optimize_delta") as mock_opt, \
         patch.object(orchestrator.typesetter, "render", return_value=tmp_path / "Prasad_Rane_Resume.pdf"):
         
        mock_diff = OptimizationDiff(
            role_title="Lead Architect",
            original_bullet="Managed general cloud monitoring...",
            refined_bullet="**Engineered Prometheus** pipelines with **40%** MTTR reduction.",
            rationale="Added Prometheus",
            target_keywords=["Prometheus"]
        )
        
        # Iteration 1 returns higher scoring resume
        improved_resume = sample_resume_data.model_copy(deep=True)
        improved_resume.jobs[0].bullets[1] = "**Engineered Prometheus** observability pipelines with **40%** MTTR reduction."
        
        mock_opt.return_value = (improved_resume, [mock_diff])
        
        events = list(orchestrator.run(
            jd_text=sample_job_posting.raw_description,
            company_name="Databricks",
            max_iterations=2,
            min_score=85.0
        ))
        
        event_types = [e.step for e in events if isinstance(e, AgentEvent)]
        assert "ingestion" in event_types
        assert "critic_eval" in event_types
        assert "complete" in event_types
        
        final_event = [e for e in events if e.step == "complete"][0]
        assert final_event.payload["final_score"] >= 0.0
        assert final_event.telemetry is not None
        assert final_event.telemetry.zero_cost_subagents_run >= 4
        assert final_event.telemetry.latency_ms >= 0.0


def test_apply_approved_diffs(sample_resume_data):
    orchestrator = AgenticPipelineOrchestrator()
    diff1 = OptimizationDiff(
        diff_id="diff-1",
        role_title="Lead Architect",
        original_bullet="Managed general cloud monitoring and daily operations across multiple teams.",
        refined_bullet="Architected Prometheus observability pipelines cutting MTTR by 45%.",
        rationale="Prometheus metrics",
        target_keywords=["Prometheus"]
    )
    diff2 = OptimizationDiff(
        diff_id="diff-2",
        role_title="Senior Software Engineer",
        original_bullet="Maintained internal documentation and bug tickets.",
        refined_bullet="Engineered automated Sphinx docs with 100% CI coverage.",
        rationale="Documentation",
        target_keywords=["Sphinx"]
    )

    # Approve only diff1, reject diff2
    updated = orchestrator.apply_approved_diffs(sample_resume_data, [diff1, diff2], approved_ids=["diff-1"])
    assert updated.jobs[0].bullets[1] == "Architected Prometheus observability pipelines cutting MTTR by 45%."
    # Second bullet should remain unmodified
    assert updated.jobs[1].bullets[1] == "Maintained internal documentation and bug tickets."

