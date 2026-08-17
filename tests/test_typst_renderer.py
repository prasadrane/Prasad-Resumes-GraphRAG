"""
Unit tests for Typst and LaTeX Resume Renderers.
"""

import unittest
from src.generators.models import ResumeData, JobEntry
from src.generators.typst_renderer import render_typst_markup
from src.generators.latex_renderer import render_latex_markup


class TestAdvancedRenderers(unittest.TestCase):
    """Test suite for Typst and LaTeX markup generation."""

    def setUp(self):
        self.resume_data = ResumeData(
            name="Prasad Rane",
            title="Senior Software Engineer",
            contact_email="prasad.rane@example.com",
            contact_phone="(123) 456-7890",
            contact_location="Chicago, IL",
            contact_linkedin="https://linkedin.com/in/prasad-rane",
            summary="Experienced cloud backend architect.",
            skills=["Languages: Python, C#, SQL", "Cloud: AWS, ECS Fargate"],
            jobs=[
                JobEntry(
                    title="Senior Software Engineer",
                    company="Rocket Mortgage",
                    location="Detroit, MI",
                    dates="2023 - Present",
                    bullets=[
                        "Architected AWS ECS Fargate microservices.",
                        "Reduced query latency by 70%.",
                    ],
                )
            ],
            education=["MS Computer Science", "BS Engineering"],
        )

    def test_render_typst_markup(self):
        markup = render_typst_markup(self.resume_data)
        self.assertIn("#set page(paper: \"us-letter\", margin:", markup)
        self.assertIn("Prasad Rane", markup)
        self.assertIn("Rocket Mortgage", markup)
        self.assertIn("Architected AWS ECS Fargate", markup)
        self.assertIn("70%", markup)

    def test_render_latex_markup(self):
        markup = render_latex_markup(self.resume_data)
        self.assertIn("\\documentclass", markup)
    def test_render_latex_escapes_special_characters(self):
        special_data = ResumeData(
            name="C# & C++ Developer",
            title="Senior Engineer {Architecture}",
            summary="Optimized 100% of $1M database queries with C#_Core & ~50% latency^2 reduction.",
            skills=["Languages: C# & Python", "Formula: x^2 + y_1"],
        )
        markup = render_latex_markup(special_data)
        self.assertIn("C\\# \\& C++ Developer", markup)
        self.assertIn("\\{Architecture\\}", markup)
        self.assertIn("100\\%", markup)
        self.assertIn("\\$1M", markup)
        self.assertIn("C\\#\\_Core", markup)
        self.assertIn("\\textasciitilde{}50\\%", markup)
        self.assertIn("x\\textasciicircum{}2", markup)


if __name__ == "__main__":
    unittest.main()
