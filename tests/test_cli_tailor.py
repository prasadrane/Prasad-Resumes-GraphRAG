# tests/test_cli_tailor.py
import pytest
from unittest.mock import patch, MagicMock
from src.cli import main

def test_cli_tailor_command_help(capsys):
    with pytest.raises(SystemExit) as exc:
        with patch("sys.argv", ["cli.py", "tailor", "--help"]):
            main()
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "--company" in captured.out
    assert "--jd" in captured.out
    assert "--check-only" in captured.out

def test_cli_tailor_execution(capsys, tmp_path):
    jd_file = tmp_path / "test_jd.txt"
    jd_file.write_text("Senior Software Engineer with Python, AWS, Docker experience.", encoding="utf-8")

    with patch("src.cli.EvaluatorOrchestrator") as MockOrch:
        instance = MockOrch.return_value
        instance.feasibility_checker.check_feasibility.return_value = MagicMock(
            baseline_match_pct=85.0,
            verdict="STRONG_MATCH",
            rationale="Great fit",
            matched_skills=["Python", "AWS"],
            fillable_gaps=[],
            unfillable_gaps=[],
        )
        instance.run_agentic_pipeline.return_value = {
            "feasibility": instance.feasibility_checker.check_feasibility.return_value,
            "blueprint": MagicMock(target_company="Acme"),
            "scorecard": MagicMock(
                iteration=1,
                ats_score=88.5,
                story_grounding_score=100.0,
                format_compliance=True,
                cover_letter_score=90.0,
                verdict="APPROVED",
                critique_summary="Clean match",
                actionable_refinements=[],
            ),
            "resume_text": "## Summary\nSenior Engineer",
            "cover_letter_text": "Dear Acme Team...",
            "output_dir": str(tmp_path),
            "status": "COMPLETED",
        }

        with patch("sys.argv", ["cli.py", "tailor", "--company", "Acme", "--jd", str(jd_file)]):
            main()

    captured = capsys.readouterr()
    assert "EVALUATOR AGENT" in captured.out or "FEASIBILITY" in captured.out or "Acme" in captured.out
