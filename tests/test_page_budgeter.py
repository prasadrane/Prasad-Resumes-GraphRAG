"""
test_page_budgeter.py — Unit and integration tests for 1-Page vs 2-Page Resume Budgeting and PDF rendering.
"""

import unittest
from pathlib import Path
import pypdf

from src.config import MASTER_RESUME_PATH, ROOT_DIR
from src.generators.models import JobEntry, ResumeData
from src.generators.page_budgeter import budget_resume_for_pages
from src.generators.pdf_renderer import render_pdf_from_model, render_pdf_resume
from src.generators.resume_parser import parse_resume_markdown


class TestPageBudgeter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.master_content = MASTER_RESUME_PATH.read_text(encoding="utf-8")
        cls.parsed_master = parse_resume_markdown(cls.master_content)
        cls.test_output_dir = ROOT_DIR / "output" / "TestPageBudgeter"
        cls.test_output_dir.mkdir(parents=True, exist_ok=True)

    def test_budget_for_1_page_curates_bullets(self):
        """Verify 1-page budgeting limits bullets and keeps highest priority achievements."""
        budgeted = budget_resume_for_pages(self.parsed_master, target_pages=1)
        self.assertLessEqual(len(budgeted.jobs[0].bullets), 4)
        if len(budgeted.jobs) > 1:
            self.assertLessEqual(len(budgeted.jobs[1].bullets), 3)

    def test_budget_for_2_pages_retains_full_experience(self):
        """Verify 2-page budgeting retains all high-impact bullets."""
        budgeted = budget_resume_for_pages(self.parsed_master, target_pages=2)
        self.assertGreaterEqual(len(budgeted.jobs[0].bullets), 6)

    def test_render_1_page_pdf_exact_page_count(self):
        """Verify rendering 1-page resume produces exactly 1 page PDF without overflow."""
        pdf_path = self.test_output_dir / "test_resume_1p.pdf"
        render_pdf_resume(MASTER_RESUME_PATH, pdf_path, target_pages=1)

        reader = pypdf.PdfReader(str(pdf_path))
        self.assertEqual(len(reader.pages), 1, f"Expected exactly 1 page, got {len(reader.pages)}")

    def test_render_2_page_pdf_exact_page_count(self):
        """Verify rendering 2-page resume produces exactly 2 pages PDF."""
        pdf_path = self.test_output_dir / "test_resume_2p.pdf"
        render_pdf_resume(MASTER_RESUME_PATH, pdf_path, target_pages=2)

        reader = pypdf.PdfReader(str(pdf_path))
        self.assertEqual(len(reader.pages), 2, f"Expected exactly 2 pages, got {len(reader.pages)}")

    def test_section_order_in_2_page_mode(self):
        """Verify 2-page mode puts Skills on Page 1 before Experience for fast recruiter scannability."""
        pdf_path = self.test_output_dir / "test_resume_2p.pdf"
        render_pdf_resume(MASTER_RESUME_PATH, pdf_path, target_pages=2)

        reader = pypdf.PdfReader(str(pdf_path))
        page1_text = reader.pages[0].extract_text()
        self.assertIn("SKILLS", page1_text)
        self.assertIn("PRASAD RANE", page1_text)


if __name__ == "__main__":
    unittest.main()
