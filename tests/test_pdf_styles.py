"""
Unit tests for src/generators/pdf_styles.py (ReportLab styling and HTML helpers).
"""

import io
import unittest
from contextlib import redirect_stdout

from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import HRFlowable, Paragraph

from src.generators.models import JobEntry, ResumeData
from src.generators.pdf_styles import (
    PageCountCanvas,
    create_section_header_flowables,
    format_contact_paragraph,
    format_job_heading,
    get_resume_styles,
    markdown_to_reportlab_html,
)


class TestMarkdownToReportlabHtml(unittest.TestCase):

    def test_bold_conversion(self):
        self.assertEqual(
            markdown_to_reportlab_html("Built **Python** services"),
            "Built <b>Python</b> services",
        )

    def test_italic_conversion(self):
        self.assertEqual(
            markdown_to_reportlab_html("Worked *remotely* abroad"),
            "Worked <i>remotely</i> abroad",
        )

    def test_link_conversion(self):
        result = markdown_to_reportlab_html("See [site](https://example.com)")
        self.assertIn('<a href="https://example.com">', result)
        self.assertIn('<font color="#0f3460">site</font></a>', result)

    def test_date_range_dash_preserved(self):
        result = markdown_to_reportlab_html("Jan 2020 — Feb 2022")
        self.assertEqual(result, "Jan 2020 - Feb 2022")

    def test_standalone_em_dash_becomes_period(self):
        # replace("—", ". ") keeps the surrounding spaces: "x — y" -> "x .  y"
        result = markdown_to_reportlab_html("Led team — improved uptime")
        self.assertNotIn("—", result)
        self.assertIn("Led team .", result)

    def test_empty_text(self):
        self.assertEqual(markdown_to_reportlab_html(""), "")


class TestFormatJobHeading(unittest.TestCase):

    def test_full_heading(self):
        job = JobEntry(title="Engineer", company="Co", location="Remote", dates="2020 - Present")
        result = format_job_heading(job)
        self.assertIn("<b>Engineer</b> | <b>Co</b>", result)
        self.assertIn("<i>Remote</i>", result)
        self.assertIn("<i>2020 - Present</i>", result)

    def test_title_only(self):
        job = JobEntry(title="Engineer")
        result = format_job_heading(job)
        self.assertIn("<b>Engineer</b>", result)
        self.assertNotIn("|", result)

    def test_fallback_to_raw_heading(self):
        job = JobEntry(heading="Raw heading text")
        self.assertEqual(format_job_heading(job), "Raw heading text")


class TestFormatContactParagraph(unittest.TestCase):

    def test_full_contact_line(self):
        data = ResumeData(
            contact_location="Remote",
            contact_phone="555-0100",
            contact_email="mailto:alex@example.com",
            contact_linkedin="linkedin.com/in/alex",
        )
        result = format_contact_paragraph(data)
        self.assertIn("Remote", result)
        self.assertIn("555-0100", result)
        # mailto: prefix stripped then re-added exactly once
        self.assertIn('<a href="mailto:alex@example.com">', result)
        self.assertNotIn("mailto:mailto:", result)
        # scheme-less LinkedIn gets https:// prefix in href only
        self.assertIn('<a href="https://linkedin.com/in/alex">', result)
        self.assertIn(">linkedin.com/in/alex</font>", result)

    def test_empty_contact(self):
        self.assertEqual(format_contact_paragraph(ResumeData()), "")


class TestStyleFactories(unittest.TestCase):

    def test_get_resume_styles_keys(self):
        styles = get_resume_styles()
        expected = {
            "name", "contact", "sec_header", "job_heading", "bullet",
            "summary", "skill", "cert", "edu",
        }
        self.assertEqual(set(styles.keys()), expected)
        for style in styles.values():
            self.assertIsInstance(style, ParagraphStyle)

    def test_create_section_header_flowables(self):
        styles = get_resume_styles()
        flowables = create_section_header_flowables("EXPERIENCE", styles["sec_header"])
        self.assertEqual(len(flowables), 2)
        self.assertIsInstance(flowables[0], HRFlowable)
        self.assertIsInstance(flowables[1], Paragraph)


class TestPageCountCanvas(unittest.TestCase):

    def test_warns_when_over_two_pages(self):
        buffer = io.BytesIO()
        page_canvas = PageCountCanvas(buffer)
        for _ in range(3):
            page_canvas.showPage()
        captured = io.StringIO()
        with redirect_stdout(captured):
            page_canvas.save()
        self.assertIn("exceeded 2-page constraint", captured.getvalue())

    def test_no_warning_at_two_pages(self):
        buffer = io.BytesIO()
        page_canvas = PageCountCanvas(buffer)
        for _ in range(2):
            page_canvas.showPage()
        captured = io.StringIO()
        with redirect_stdout(captured):
            page_canvas.save()
        self.assertEqual(captured.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
