"""
Unit tests for stepwise resume generator (TDD).
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.generators.resume_generator import generate_raw_resume_stepwise


class TestStepwiseGenerator(unittest.TestCase):

    def test_stepwise_yields_all_steps(self):
        """Verify correct 8-step sequence is yielded in order."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_out_dir = Path(tmp_dir)
            
            # Mock LLM safe calls
            with patch("src.generators.resume_generator._call_llm_safe", return_value="Mocked LLM content"):
                steps = list(generate_raw_resume_stepwise(
                    company_name="TestCompany",
                    jd_text="Need Python Cloud IAM AWS",
                    base_output_dir=temp_out_dir
                ))
            
            step_ids = [step[0] for step in steps]
            expected_steps = [
                "extracting_keywords",
                "loading_master",
                "selecting_summary",
                "tailoring_summary",
                "tailoring_bullets",
                "formatting",
                "rendering_pdf",
                "complete"
            ]
            self.assertEqual(step_ids, expected_steps)

    def test_stepwise_progress_monotonic(self):
        """Verify percentages strictly increase."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_out_dir = Path(tmp_dir)
            
            with patch("src.generators.resume_generator._call_llm_safe", return_value="Mocked LLM content"):
                steps = list(generate_raw_resume_stepwise(
                    company_name="TestCompany",
                    jd_text="Need Python Cloud IAM AWS",
                    base_output_dir=temp_out_dir
                ))
                
            progress_pcts = [step[2] for step in steps]
            # Verify they are strictly increasing
            for i in range(1, len(progress_pcts)):
                self.assertGreater(progress_pcts[i], progress_pcts[i-1])
                
            self.assertEqual(progress_pcts[-1], 100)

    def test_stepwise_final_result_has_file(self):
        """Verify complete step includes correct file paths and content."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_out_dir = Path(tmp_dir)
            
            with patch("src.generators.resume_generator._call_llm_safe", return_value="Mocked LLM content"):
                steps = list(generate_raw_resume_stepwise(
                    company_name="TestCompany",
                    jd_text="Need Python Cloud IAM AWS",
                    base_output_dir=temp_out_dir
                ))
                
            last_step = steps[-1]
            self.assertEqual(last_step[0], "complete")
            self.assertEqual(last_step[2], 100)
            
            detail = last_step[3]
            self.assertIsInstance(detail, dict)
            self.assertIn("raw_resume_path", detail)
            self.assertIn("raw_resume", detail)
            self.assertIn("pdf_path", detail)
            
            raw_path = Path(detail["raw_resume_path"])
            pdf_path = Path(detail["pdf_path"])
            self.assertTrue(raw_path.exists())
            self.assertTrue(pdf_path.exists())
            self.assertIn("Mocked LLM content", detail["raw_resume"])

    def test_stepwise_graceful_llm_failure(self):
        """Verify pipeline continues when LLM is unavailable."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_out_dir = Path(tmp_dir)
            
            # Force LLM safe calls to return empty string/fail
            with patch("src.generators.resume_generator._call_llm_safe", return_value=""):
                steps = list(generate_raw_resume_stepwise(
                    company_name="TestCompany",
                    jd_text="Need Python Cloud IAM AWS",
                    base_output_dir=temp_out_dir
                ))
                
            last_step = steps[-1]
            self.assertEqual(last_step[0], "complete")
            detail = last_step[3]
            self.assertTrue(Path(detail["raw_resume_path"]).exists())
            self.assertTrue(Path(detail["pdf_path"]).exists())


if __name__ == "__main__":
    unittest.main()
