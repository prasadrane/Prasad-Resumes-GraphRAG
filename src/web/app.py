"""
app.py — FastAPI Web Backend for Prasad Resumes GraphRAG UI.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = ROOT_DIR / "output"
STATIC_DIR = Path(__file__).resolve().parent / "static"

from src.generators.resume_generator import generate_raw_resume
from src.generators.pdf_renderer import render_pdf_resume
from src.query.search_engine import execute_graphrag_query

app = FastAPI(title="Prasad Resumes GraphRAG UI", version="1.0.0")


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Question for GraphRAG knowledge graph")
    mode: str = Field(default="local", description="Query mode: 'local' or 'global'")


@app.post("/api/query")
def query_endpoint(req: QueryRequest):
    """Execute GraphRAG query against Prasad's resumes knowledge graph."""
    query_clean = req.query.strip()
    if not query_clean:
        raise HTTPException(status_code=400, detail="Query string cannot be empty.")
    
    mode_clean = req.mode.lower().strip()
    if mode_clean not in ["local", "global"]:
        mode_clean = "local"
        
    try:
        response_text = execute_graphrag_query(query=query_clean, mode=mode_clean, root_dir=ROOT_DIR)
        return {
            "status": "success",
            "query": query_clean,
            "mode": mode_clean,
            "response": response_text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


# Serve static files if directory exists
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class GenerateRequest(BaseModel):
    company: str = Field(..., min_length=1, description="Target company name")
    jd_text: Optional[str] = Field(default="", description="Job description text")


class ResumeHistoryItem(BaseModel):
    company: str
    date: str
    pdf_filename: str
    pdf_url: str
    txt_filename: Optional[str] = None
    txt_url: Optional[str] = None


@app.get("/")
def read_root():
    """Serve main single-page interface."""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return JSONResponse({"message": "Prasad Resumes GraphRAG API Server Active. UI static assets missing."})


@app.get("/api/history", response_model=List[ResumeHistoryItem])
def get_resume_history():
    """Fetch history of tailored resumes from the output directory (recursively scanning all company folders)."""
    history = []
    if not OUTPUT_DIR.exists():
        return history

    # Scan output directory recursively for PDF files
    for pdf_path in OUTPUT_DIR.rglob("*.pdf"):
        if pdf_path.is_file():
            rel_path = pdf_path.relative_to(OUTPUT_DIR).as_posix()
            company_name = pdf_path.parent.name
            mod_time = datetime.fromtimestamp(pdf_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            
            # Check matching TXT file in same folder
            txt_path = pdf_path.parent / pdf_path.name.replace(".pdf", ".txt")
            txt_rel_path = txt_path.relative_to(OUTPUT_DIR).as_posix() if txt_path.exists() else None

            history.append(
                ResumeHistoryItem(
                    company=company_name,
                    date=mod_time,
                    pdf_filename=pdf_path.name,
                    pdf_url=f"/api/files/{rel_path}",
                    txt_filename=txt_path.name if txt_path.exists() else None,
                    txt_url=f"/api/files/{txt_rel_path}" if txt_rel_path else None,
                )
            )

    # Sort reverse chronologically by date
    history.sort(key=lambda x: x.date, reverse=True)
    return history


@app.get("/api/pdf/{company}/{filename}")
def serve_pdf_legacy(company: str, filename: str):
    """Legacy route: Serve requested PDF file."""
    # Find matching PDF file under company
    matches = list(OUTPUT_DIR.rglob(f"**/{company}/{filename}"))
    if not matches:
        raise HTTPException(status_code=404, detail="Requested PDF resume not found.")
    return FileResponse(str(matches[0]), media_type="application/pdf", filename=filename)


@app.get("/api/files/{filepath:path}")
def serve_output_file(filepath: str):
    """Serve requested PDF/TXT file dynamically by relative path under output directory."""
    target_file = (OUTPUT_DIR / filepath).resolve()

    # Security check: ensure path is within OUTPUT_DIR
    if not str(target_file).startswith(str(OUTPUT_DIR.resolve())):
        raise HTTPException(status_code=403, detail="Access denied.")
    if not target_file.exists() or not target_file.is_file():
        raise HTTPException(status_code=404, detail="Requested file not found.")

    media_type = "application/pdf" if target_file.suffix.lower() == ".pdf" else "text/plain"
    return FileResponse(str(target_file), media_type=media_type, content_disposition_type="inline")


@app.post("/api/generate")
def generate_resume_endpoint(req: GenerateRequest):
    """Generate a tailored raw resume text and rule-based PDF."""
    company_clean = req.company.strip()
    if not company_clean:
        raise HTTPException(status_code=400, detail="Company name cannot be empty.")

    try:
        # Step 1: Generate tailored raw resume text
        raw_text_path = generate_raw_resume(company_name=company_clean, jd_text=req.jd_text or "")

        # Step 2: Render ATS-compliant PDF
        pdf_output_target = raw_text_path.parent / "Prasad_Rane_Resume.pdf"
        pdf_path = render_pdf_resume(raw_text_path, pdf_output_target)

        pdf_rel = Path(pdf_path).resolve().relative_to(OUTPUT_DIR.resolve()).as_posix()
        txt_rel = Path(raw_text_path).resolve().relative_to(OUTPUT_DIR.resolve()).as_posix()

        return {
            "status": "success",
            "message": f"Resume tailored successfully for {company_clean}.",
            "company": company_clean,
            "pdf_url": f"/api/files/{pdf_rel}",
            "txt_url": f"/api/files/{txt_rel}",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


class SaveEditRequest(BaseModel):
    txt_url: str = Field(..., min_length=1, description="Relative URL or path to text file")
    content: str = Field(..., description="Updated raw resume text content")


@app.post("/api/save-edit")
def save_edit_endpoint(req: SaveEditRequest):
    """Save updated raw resume text content and re-render the PDF."""
    txt_path_str = req.txt_url.replace("/api/files/", "")
    target_txt = (OUTPUT_DIR / txt_path_str).resolve()

    # Security check: ensure path is within OUTPUT_DIR and is a .txt file
    if not str(target_txt).startswith(str(OUTPUT_DIR.resolve())):
        raise HTTPException(status_code=403, detail="Access denied.")
    if target_txt.suffix.lower() != ".txt":
        raise HTTPException(status_code=400, detail="Only .txt resume files can be edited.")
    
    try:
        # Write updated text content to TXT file
        target_txt.parent.mkdir(parents=True, exist_ok=True)
        target_txt.write_text(req.content, encoding="utf-8")

        # Re-render PDF
        pdf_output_target = target_txt.parent / "Prasad_Rane_Resume.pdf"
        pdf_path = render_pdf_resume(target_txt, pdf_output_target)

        pdf_rel = Path(pdf_path).resolve().relative_to(OUTPUT_DIR.resolve()).as_posix()
        txt_rel = target_txt.resolve().relative_to(OUTPUT_DIR.resolve()).as_posix()

        return {
            "status": "success",
            "message": "Resume updated and re-rendered successfully.",
            "pdf_url": f"/api/files/{pdf_rel}?t={int(datetime.now().timestamp())}",
            "txt_url": f"/api/files/{txt_rel}",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update resume: {str(e)}")


