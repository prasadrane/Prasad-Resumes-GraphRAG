"""
pdf_parser.py — PDF text extraction using PyMuPDF (fitz) with layout sorting.
"""

from pathlib import Path
from typing import Tuple

try:
    import fitz  # PyMuPDF
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

from .resume_structurer import clean_text, structure_resume

def extract_pdf_text(pdf_path: Path) -> Tuple[bool, str]:
    """Extract text from a PDF file with layout ordering.
    Returns (success_flag, extracted_or_structured_text)."""
    if not PDF_SUPPORT:
        return False, "PyMuPDF not installed"
        
    try:
        doc = fitz.open(str(pdf_path))
        pages = []
        for page in doc:
            text_blocks = page.get_text("blocks")
            text_blocks.sort(key=lambda b: (round(b[1] / 10), b[0]))
            pages.append("\n".join(b[4] for b in text_blocks if isinstance(b[4], str)))
        doc.close()
        
        raw_text = clean_text("\n".join(pages))
        if len(raw_text.strip()) < 50:
            return False, "Too little text extracted (possibly image-only PDF)"
            
        structured_markdown = structure_resume(raw_text)
        return True, structured_markdown
    except Exception as e:
        return False, str(e)
