"""
Characterization test: the batch path (generate_raw_resume / llm_tailor_resume)
and the stepwise path (generate_raw_resume_stepwise) must produce byte-identical
raw resume text for identical inputs and identical mocked LLM responses.
This is the regression net for the tailoring dedupe.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.generators.resume_generator import generate_raw_resume, generate_raw_resume_stepwise

MOCK_LLM_RESPONSE = "Mocked tailoring content shared across both generation paths for dedupe verification."
JD_TEXT = "Senior engineer with Python, AWS, Kubernetes and Kafka experience."


class TestTailoringDedupe(unittest.TestCase):

    def _run_both_paths(self):
        with tempfile.TemporaryDirectory() as tmp_batch, tempfile.TemporaryDirectory() as tmp_step:
            with patch(
                "src.generators.resume_generator._call_llm_safe",
                return_value=MOCK_LLM_RESPONSE,
            ):
                batch_path = generate_raw_resume("DedupeCo", JD_TEXT, base_output_dir=Path(tmp_batch))
                batch_text = batch_path.read_text(encoding="utf-8")
                steps = list(generate_raw_resume_stepwise("DedupeCo", JD_TEXT, base_output_dir=Path(tmp_step)))
        return batch_text, steps

    def test_batch_and_stepwise_raw_resume_are_identical(self):
        batch_text, steps = self._run_both_paths()
        self.assertEqual(steps[-1][0], "complete")
        self.assertEqual(steps[-1][3]["raw_resume"], batch_text)

    def test_llm_called_with_two_positional_args(self):
        calls = []

        def spy(prompt, system_prompt):
            calls.append((prompt, system_prompt))
            return MOCK_LLM_RESPONSE

        with tempfile.TemporaryDirectory() as tmp:
            with patch("src.generators.resume_generator._call_llm_safe", side_effect=spy):
                generate_raw_resume("DedupeCo", JD_TEXT, base_output_dir=Path(tmp))

        self.assertGreaterEqual(len(calls), 1)
        self.assertIn("## Target Role", calls[0][0])
        self.assertIn("elite technical resume strategist", calls[0][1])


if __name__ == "__main__":
    unittest.main()
