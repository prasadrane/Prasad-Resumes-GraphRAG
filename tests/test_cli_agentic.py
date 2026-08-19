"""
test_cli_agentic.py — Unit tests for CLI --agentic and --url generation options.
"""

from unittest.mock import MagicMock, patch
import pytest
from src.cli import build_parser, main
from src.agents.models import AgentEvent


def test_cli_build_parser_has_agentic_options():
    parser = build_parser()
    args = parser.parse_args([
        "generate",
        "--url", "https://boards.greenhouse.io/databricks/jobs/123",
        "--agentic",
        "--min-score", "92",
        "--max-iterations", "3",
    ])
    assert args.url == "https://boards.greenhouse.io/databricks/jobs/123"
    assert args.agentic is True
    assert args.min_score == 92.0
    assert args.max_iterations == 3


@patch("src.cli.AgenticPipelineOrchestrator")
def test_cli_generate_agentic_flow(mock_orch_cls, capsys):
    mock_orch = MagicMock()
    mock_orch_cls.return_value = mock_orch
    
    mock_orch.run.return_value = [
        AgentEvent(
            step="ingestion",
            agent="JobIngestionAgent",
            status="Ingested Greenhouse JD for Databricks",
        ),
        AgentEvent(
            step="critic_eval",
            agent="ATSCriticAgent",
            status="Initial score 75%",
            payload={"iteration": 0, "score": 75.0},
        ),
        AgentEvent(
            step="complete",
            agent="PDFTypesetterAgent",
            status="Generated PDF",
            payload={
                "company": "Databricks",
                "final_score": 93.5,
                "pdf_path": "output/08-19-2026/Databricks/Prasad_Rane_Resume.pdf",
                "diffs": [],
                "iterations_count": 1,
            },
        ),
    ]
    
    with patch("sys.argv", ["cli.py", "generate", "--url", "https://boards.greenhouse.io/databricks/jobs/123", "--agentic"]):
        main()
        
    captured = capsys.readouterr().out
    assert "JobIngestionAgent" in captured or "Databricks" in captured
    assert "93.5" in captured
