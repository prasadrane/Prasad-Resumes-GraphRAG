"""
api/index.py — Vercel Serverless FastAPI Entrypoint.
Provides stateless serverless endpoints for ATS keyword extraction, tailored resume generation, and PDF downloads.
"""

from fastapi import FastAPI, HTTPException
import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.generators.ats_matcher import extract_ats_keywords
from src.generators.resume_generator import generate_raw_resume, parse_resume_markdown, format_tailored_markdown, generate_raw_resume_stepwise
from src.generators.pdf_renderer import render_pdf_resume
from src.config import MASTER_RESUME_PATH, WEB_STATIC_DIR
from src.shared.api_models import ResumeGenerationRequest, SaveEditRequest
from src.shared.api_routes import shared_router
from fastapi.responses import FileResponse, StreamingResponse

app = FastAPI(title="Prasad Resumes GraphRAG Vercel API", version="1.0.0")
app.include_router(shared_router)

from fastapi.staticfiles import StaticFiles

STATIC_DIR = WEB_STATIC_DIR
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

@app.get("/api/default-resume")
@app.get("/api/default_resume")
def get_default_resume_endpoint():
    """Fetch default master resume raw text and base64 PDF preview for Vercel serverless."""
    master_path = MASTER_RESUME_PATH
    if not master_path.exists():
        raise HTTPException(status_code=404, detail="MASTER_RESUME.txt file not found.")

    try:
        master_content = master_path.read_text(encoding="utf-8")
        parsed = parse_resume_markdown(master_content)
        clean_raw_resume = format_tailored_markdown(parsed, [])

        temp_out_dir = Path(tempfile.gettempdir()) / "output" / "Default"
        temp_out_dir.mkdir(parents=True, exist_ok=True)
        raw_path = temp_out_dir / "master_raw_resume.txt"
        raw_path.write_text(clean_raw_resume, encoding="utf-8")

        pdf_target = temp_out_dir / "Prasad_Rane_Default_Resume.pdf"
        render_pdf_resume(raw_path, pdf_target)

        pdf_bytes = pdf_target.read_bytes()
        b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
        pdf_data_uri = f"data:application/pdf;base64,{b64_pdf}"

        return {
            "status": "success",
            "pdf_url": pdf_data_uri,
            "txt_url": None,
            "raw_resume": clean_raw_resume
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load default resume: {str(e)}")

@app.post("/api/generate")
def generate_resume_endpoint(req: ResumeGenerationRequest):
    company_clean = req.company.strip()
    if not company_clean:
        raise HTTPException(status_code=400, detail="Company name cannot be empty.")
    try:
        temp_out_dir = Path(tempfile.gettempdir()) / "output"
        raw_path = generate_raw_resume(company_clean, req.jd_text, base_output_dir=temp_out_dir)
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
@app.post("/api/save-edit")
def render_pdf_endpoint(req: SaveEditRequest):
    try:
        text_content = req.raw_text or req.content or ""
        if not text_content:
            raise HTTPException(status_code=400, detail="Resume text content cannot be empty.")
            
        temp_out_dir = Path(tempfile.gettempdir()) / "output"
        temp_out_dir.mkdir(parents=True, exist_ok=True)
        raw_path = temp_out_dir / "edited_raw_resume.txt"
        raw_path.write_text(text_content, encoding="utf-8")

        pdf_target = temp_out_dir / "Prasad_Rane_Resume.pdf"
        render_pdf_resume(raw_path, pdf_target)

        pdf_bytes = pdf_target.read_bytes()
        b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
        pdf_data_uri = f"data:application/pdf;base64,{b64_pdf}"

        return {
            "status": "success",
            "pdf_url": pdf_data_uri,
            "raw_resume": text_content
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF rendering failed: {str(e)}")


@app.post("/api/generate-stream")
def generate_resume_stream_endpoint(req: ResumeGenerationRequest):
    import json
    import tempfile
    import base64
    company_clean = req.company.strip()
    if not company_clean:
        raise HTTPException(status_code=400, detail="Company name cannot be empty.")
    try:
        temp_out_dir = Path(tempfile.gettempdir()) / "output"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to resolve temp dir: {str(e)}")

    def event_generator():
        try:
            for step_id, label, pct, detail in generate_raw_resume_stepwise(
                company_name=company_clean,
                jd_text=req.jd_text,
                base_output_dir=temp_out_dir
            ):
                if step_id == "complete" and isinstance(detail, dict):
                    pdf_path = Path(detail["pdf_path"])
                    pdf_bytes = pdf_path.read_bytes()
                    b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
                    pdf_data_uri = f"data:application/pdf;base64,{b64_pdf}"

                    complete_payload = {
                        "status": "success",
                        "company": company_clean,
                        "pdf_url": pdf_data_uri,
                        "txt_url": "",
                        "raw_resume": detail["raw_resume"]
                    }
                    yield f"data: {json.dumps({'step': step_id, 'label': label, 'progress': pct, 'detail': complete_payload})}\n\n"
                else:
                    yield f"data: {json.dumps({'step': step_id, 'label': label, 'progress': pct, 'detail': detail})}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'detail': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
