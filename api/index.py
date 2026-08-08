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
from src.generators.resume_generator import generate_tailored_resume
from src.generators.pdf_renderer import render_resume_pdf

app = FastAPI(title="Prasad Resumes GraphRAG Vercel API", version="1.0.0")

class ResumeGenerationRequest(BaseModel):
    company: str
    jd_text: str

@app.get("/")
def read_root():
    return {"status": "ok", "service": "Prasad-Resumes-GraphRAG Vercel Serverless API"}

@app.post("/api/keywords")
def get_keywords(req: ResumeGenerationRequest):
    kws = extract_ats_keywords(req.jd_text)
    return {"company": req.company, "keywords": kws}

@app.post("/api/generate")
def generate_resume(req: ResumeGenerationRequest):
    try:
        raw_resume = generate_tailored_resume(req.company, req.jd_text)
        return {
            "status": "success",
            "company": req.company,
            "raw_resume": raw_resume
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
