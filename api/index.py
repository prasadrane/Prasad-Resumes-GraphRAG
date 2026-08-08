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

class RenderPdfRequest(BaseModel):
    raw_text: str
    company: Optional[str] = "Tailored"

@app.post("/api/generate")
def generate_resume_endpoint(req: ResumeGenerationRequest):
    try:
        temp_out_dir = Path(tempfile.gettempdir()) / "output"
        raw_path = generate_raw_resume(req.company, req.jd_text, base_output_dir=temp_out_dir)
        pdf_target = raw_path.parent / "Prasad_Rane_Resume.pdf"
        render_pdf_resume(raw_path, pdf_target)

        pdf_bytes = pdf_target.read_bytes()
        b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
        pdf_data_uri = f"data:application/pdf;base64,{b64_pdf}"

        return {
            "status": "success",
            "pdf_url": pdf_data_uri,
            "raw_resume": raw_path.read_text(encoding="utf-8")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

@app.post("/api/render_pdf")
def render_pdf_endpoint(req: RenderPdfRequest):
    try:
        temp_out_dir = Path(tempfile.gettempdir()) / "output"
        temp_out_dir.mkdir(parents=True, exist_ok=True)
        raw_path = temp_out_dir / "edited_raw_resume.txt"
        raw_path.write_text(req.raw_text, encoding="utf-8")

        pdf_target = temp_out_dir / "Prasad_Rane_Resume.pdf"
        render_pdf_resume(raw_path, pdf_target)

        pdf_bytes = pdf_target.read_bytes()
        b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
        pdf_data_uri = f"data:application/pdf;base64,{b64_pdf}"

        return {
            "status": "success",
            "pdf_url": pdf_data_uri,
            "raw_resume": req.raw_text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF rendering failed: {str(e)}")

from src.query.search_engine import execute_graphrag_query

class QueryRequest(BaseModel):
    query: str
    mode: Optional[str] = "local"

@app.post("/api/query")
def query_endpoint(req: QueryRequest):
    query_clean = req.query.strip()
    if not query_clean:
        raise HTTPException(status_code=400, detail="Query string cannot be empty.")
    
    mode_clean = req.mode.lower().strip() if req.mode else "local"
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


