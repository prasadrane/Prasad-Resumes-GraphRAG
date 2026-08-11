"""
Unit tests for src/converters/pdf_parser.py.

Builds real PDFs with ReportLab and extracts them with PyMuPDF, so the
full parse -> clean -> structure pipeline is exercised. Pytest-style
(uses tmp_path and conftest fixtures); not collected by unittest.
"""

from pathlib import Path

from reportlab.pdfgen import canvas as rl_canvas

from src.converters.pdf_parser import extract_pdf_text


def _make_pdf(pdf_path: Path, lines: list) -> None:
    """Render the given text lines into a single-page PDF."""
    page = rl_canvas.Canvas(str(pdf_path))
    y = 750
    for line in lines:
        if line.strip():
            page.drawString(72, y, line)
            y -= 20
    page.showPage()
    page.save()


def test_extract_valid_pdf_success(tmp_path, sample_master_resume_text):
    pdf_path = tmp_path / "resume.pdf"
    _make_pdf(pdf_path, sample_master_resume_text.split("\n"))

    success, result = extract_pdf_text(pdf_path)

    assert success is True
    assert "Prasad Rane" in result


def test_extract_too_little_text(tmp_path):
    pdf_path = tmp_path / "tiny.pdf"
    _make_pdf(pdf_path, ["Hello World"])

    success, result = extract_pdf_text(pdf_path)

    assert success is False
    assert result == "Too little text extracted (possibly image-only PDF)"


def test_extract_missing_file_returns_failure(tmp_path):
    success, result = extract_pdf_text(tmp_path / "does_not_exist.pdf")

    assert success is False
    assert isinstance(result, str)
    assert len(result) > 0
