"""
input_converter.py — Batch document conversion orchestrator.
"""

from pathlib import Path
from typing import Dict, Union

from .pdf_parser import PDF_SUPPORT, extract_pdf_text
from .resume_structurer import clean_text

def make_out_name(stem: str) -> str:
    """Normalize output filename."""
    clean = stem.replace(" ", "_").replace("(", "").replace(")", "")
    return clean + ".txt"

def convert_documents(source_dir: Path, target_dir: Path, force: bool = False) -> Dict[str, int]:
    """Batch converts PDFs and Markdown files from source_dir into plain .txt in target_dir.
    Returns status counts dictionary."""
    target_dir.mkdir(parents=True, exist_ok=True)
    
    stats = {"ok": 0, "skip": 0, "error": 0}
    
    if not source_dir.exists():
        print(f"[ERROR] Source directory does not exist: {source_dir}")
        return stats

    files = list(source_dir.iterdir())
    pdfs = [f for f in files if f.suffix.lower() == ".pdf"]
    mds  = [f for f in files if f.suffix.lower() == ".md"]

    if PDF_SUPPORT:
        for pdf in sorted(pdfs):
            out_path = target_dir / make_out_name(pdf.stem)
            if out_path.exists() and not force:
                stats["skip"] += 1
                continue
            success, content = extract_pdf_text(pdf)
            if success:
                out_path.write_text(content, encoding="utf-8")
                stats["ok"] += 1
            else:
                print(f"[WARN] Failed to convert PDF {pdf.name}: {content}")
                stats["error"] += 1
    elif pdfs:
        print("[WARN] PyMuPDF (fitz) is not installed. Skipping PDF conversion.")

    for md in sorted(mds):
        out_path = target_dir / make_out_name(md.stem)
        if out_path.exists() and not force:
            stats["skip"] += 1
            continue
        try:
            text = md.read_text(encoding="utf-8")
            out_path.write_text(clean_text(text), encoding="utf-8")
            stats["ok"] += 1
        except Exception as e:
            print(f"[WARN] Failed to process Markdown file {md.name}: {e}")
            stats["error"] += 1

    return stats
