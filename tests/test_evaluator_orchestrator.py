# tests/test_evaluator_orchestrator.py
import pytest
from unittest.mock import patch
from src.evaluator.orchestrator import EvaluatorOrchestrator
from src.generators.cover_letter_generator import CoverLetterData

def test_orchestrator_runs_end_to_end_mocked():
    master_content = """
    ## Core Skills
    Python, AWS, Docker, FastApi
    ## Experience
    Company: TechCorp
    - Built microservices on AWS ECS reducing latency by 40%.
    """
    jd_text = """
    Looking for a Senior Software Engineer with strong Python and AWS background at TechCorp.
    """
    mock_resume_result = {
        "raw_resume": "## Summary\nSenior Engineer with Python and AWS.\n## Experience\n- Built microservices on AWS ECS reducing latency by 40%.\n## Skills\nPython, AWS",
        "output_dir": None,
    }
    mock_cover_letter = CoverLetterData(
        candidate_name="Prasad Rane",
        company_name="TechCorp",
        role_title="Senior Software Engineer",
        paragraphs=[
            "Dear Hiring Team,",
            "I am thrilled to apply for the Senior Software Engineer role at TechCorp.",
            "With deep experience in Python, AWS, and distributed microservices, I look forward to contributing.",
            "Sincerely,\nPrasad Rane"
        ]
    )

    with patch("src.evaluator.orchestrator.generate_tailored_resume", return_value=mock_resume_result):
        with patch("src.generators.cover_letter_generator.CoverLetterGenerator.generate", return_value=mock_cover_letter):
            orchestrator = EvaluatorOrchestrator(master_content=master_content)
            result = orchestrator.run_agentic_pipeline(
                company_name="TechCorp",
                jd_text=jd_text,
                max_turns=2,
                auto_refine=True,
            )

    assert result["feasibility"].verdict in ["STRONG_MATCH", "TAILORABLE"]
    assert result["status"] == "COMPLETED"
    assert "scorecard" in result
    assert result["scorecard"].iteration >= 1

def test_orchestrator_aborts_on_severe_gap_if_requested():
    master_content = "Skills: C#"
    jd_text = "Looking for Lead Embedded Firmware Engineer with FPGA, Verilog, VHDL, RTOS, and Oscilloscope Signal Processing."
    orchestrator = EvaluatorOrchestrator(master_content=master_content)
    result = orchestrator.run_agentic_pipeline(
        company_name="HardwareCorp",
        jd_text=jd_text,
        max_turns=1,
        auto_refine=False,
    )
    assert result["feasibility"].verdict in ["HIGH_GAP", "DO_NOT_APPLY"]
    assert result["status"] == "ABORTED_DO_NOT_APPLY"
    assert result["scorecard"] is None
