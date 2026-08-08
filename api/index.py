"""
api/index.py — Vercel Serverless FastAPI Entrypoint.
Provides stateless serverless endpoints for ATS keyword extraction, tailored resume generation, and PDF downloads.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.generators.ats_matcher import extract_ats_keywords
from src.generators.resume_generator import generate_raw_resume
from src.generators.pdf_renderer import render_pdf_resume

app = FastAPI(title="Prasad Resumes GraphRAG Vercel API", version="1.0.0")

class ResumeGenerationRequest(BaseModel):
    company: str
    jd_text: str

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

STATIC_DIR = ROOT_DIR / "src" / "web" / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
def read_root():
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"status": "ok", "service": "Prasad-Resumes-GraphRAG Vercel Serverless API"}

@app.post("/api/keywords")
def get_keywords(req: ResumeGenerationRequest):
    kws = extract_ats_keywords(req.jd_text)
    return {"company": req.company, "keywords": kws}

import base64
import tempfile

@app.get("/api/history")
def get_history():
    return []

@app.post("/api/generate")
def generate_resume(req: ResumeGenerationRequest):
    try:
        temp_out_dir = Path(tempfile.gettempdir()) / "output"
        raw_resume_path = generate_raw_resume(req.company, req.jd_text, base_output_dir=temp_out_dir)
        raw_content = raw_resume_path.read_text(encoding="utf-8")
        
        pdf_target = raw_resume_path.parent / "Prasad_Rane_Resume.pdf"
        render_pdf_resume(raw_resume_path, pdf_target)
        
        pdf_bytes = pdf_target.read_bytes()
        b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
        pdf_data_uri = f"data:application/pdf;base64,{b64_pdf}"

        return {
            "status": "success",
            "company": req.company,
            "raw_resume": raw_content,
            "pdf_url": pdf_data_uri,
            "pdf_filename": "Prasad_Rane_Resume.pdf"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

