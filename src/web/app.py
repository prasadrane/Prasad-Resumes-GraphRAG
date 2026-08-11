"""
app.py — FastAPI Web Backend for Prasad Resumes GraphRAG UI.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.config import ROOT_DIR, OUTPUT_DIR_PATH, MASTER_RESUME_PATH, WEB_STATIC_DIR as STATIC_DIR
from src.shared.api_models import ResumeGenerationRequest, SaveEditRequest

from src.generators.resume_generator import generate_raw_resume, parse_resume_markdown, format_tailored_markdown, generate_raw_resume_stepwise
from src.generators.pdf_renderer import render_pdf_resume
from src.shared.api_routes import shared_router

logger = logging.getLogger(__name__)

app = FastAPI(title="Prasad Resumes GraphRAG UI", version="1.0.0")
app.include_router(shared_router)


# Serve static files if directory exists
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


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


@app.get("/api/default-resume")
@app.get("/api/default_resume")
def get_default_resume_endpoint():
    """Fetch default master resume raw text and PDF preview."""
    master_path = MASTER_RESUME_PATH
    if not master_path.exists():
        raise HTTPException(status_code=404, detail="MASTER_RESUME.txt file not found.")

    try:
        master_content = master_path.read_text(encoding="utf-8")
        parsed = parse_resume_markdown(master_content)
        clean_raw_resume = format_tailored_markdown(parsed, [])

        out_dir = OUTPUT_DIR_PATH / "Default"
        out_dir.mkdir(parents=True, exist_ok=True)
        txt_target = out_dir / "raw_resume.txt"
        txt_target.write_text(clean_raw_resume, encoding="utf-8")
        pdf_target = out_dir / "Prasad_Rane_Default_Resume.pdf"
        render_pdf_resume(txt_target, pdf_target)

        pdf_rel = pdf_target.resolve().relative_to(OUTPUT_DIR_PATH.resolve()).as_posix()
        txt_rel = txt_target.resolve().relative_to(OUTPUT_DIR_PATH.resolve()).as_posix()

        return {
            "status": "success",
            "pdf_url": f"/api/files/{pdf_rel}?t={int(datetime.now().timestamp())}",
            "txt_url": f"/api/files/{txt_rel}",
            "raw_resume": clean_raw_resume
        }
    except Exception:
        logger.exception("Failed to load default resume")
        raise HTTPException(status_code=500, detail="Failed to load default resume.")


@app.get("/api/history", response_model=List[ResumeHistoryItem])
def get_resume_history():
    """Fetch history of tailored resumes from the output directory (recursively scanning all company folders)."""
    history = []
    if not OUTPUT_DIR_PATH.exists():
        return history

    # Scan output directory recursively for PDF files
    for pdf_path in OUTPUT_DIR_PATH.rglob("*.pdf"):
        if pdf_path.is_file():
            rel_path = pdf_path.relative_to(OUTPUT_DIR_PATH).as_posix()
            company_name = pdf_path.parent.name
            mod_time = datetime.fromtimestamp(pdf_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            
            # Check matching TXT file in same folder
            txt_path = pdf_path.parent / pdf_path.name.replace(".pdf", ".txt")
            txt_rel_path = txt_path.relative_to(OUTPUT_DIR_PATH).as_posix() if txt_path.exists() else None

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
    # Reject traversal attempts before globbing user input
    if ".." in company or ".." in filename:
        raise HTTPException(status_code=403, detail="Access denied.")
    # Find matching PDF file under company
    # Company folders are nested under output/<date>/<company>/, so rglob is
    # required to locate the requested PDF at any nesting depth.
    matches = list(OUTPUT_DIR_PATH.rglob(f"**/{company}/{filename}"))
    if not matches:
        raise HTTPException(status_code=404, detail="Requested PDF resume not found.")
    target_file = matches[0].resolve()
    # Security check: ensure path is within OUTPUT_DIR_PATH (same guard as serve_output_file)
    if not target_file.is_relative_to(OUTPUT_DIR_PATH.resolve()):
        raise HTTPException(status_code=403, detail="Access denied.")
    return FileResponse(str(target_file), media_type="application/pdf", filename=filename)


@app.get("/api/files/{filepath:path}")
def serve_output_file(filepath: str):
    """Serve requested PDF/TXT file dynamically by relative path under output directory."""
    target_file = (OUTPUT_DIR_PATH / filepath).resolve()

    # Security check: ensure path is within OUTPUT_DIR_PATH
    if not target_file.is_relative_to(OUTPUT_DIR_PATH.resolve()):
        raise HTTPException(status_code=403, detail="Access denied.")
    if not target_file.exists() or not target_file.is_file():
        raise HTTPException(status_code=404, detail="Requested file not found.")

    media_type = "application/pdf" if target_file.suffix.lower() == ".pdf" else "text/plain"
    return FileResponse(str(target_file), media_type=media_type, content_disposition_type="inline")


@app.post("/api/generate")
def generate_resume_endpoint(req: ResumeGenerationRequest):
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

        pdf_rel = Path(pdf_path).resolve().relative_to(OUTPUT_DIR_PATH.resolve()).as_posix()
        txt_rel = Path(raw_text_path).resolve().relative_to(OUTPUT_DIR_PATH.resolve()).as_posix()

        return {
            "status": "success",
            "message": f"Resume tailored successfully for {company_clean}.",
            "company": company_clean,
            "pdf_url": f"/api/files/{pdf_rel}",
            "txt_url": f"/api/files/{txt_rel}",
            "raw_resume": raw_text_path.read_text(encoding="utf-8"),
        }
    except Exception:
        logger.exception("Resume generation failed")
        raise HTTPException(status_code=500, detail="Generation failed. Please try again later.")


@app.post("/api/generate-stream")
def generate_resume_stream_endpoint(req: ResumeGenerationRequest):
    """Generate a tailored raw resume text and rule-based PDF with step-by-step progress SSE stream."""
    import json
    company_clean = req.company.strip()
    if not company_clean:
        raise HTTPException(status_code=400, detail="Company name cannot be empty.")

    def event_generator():
        try:
            for step_id, label, pct, detail in generate_raw_resume_stepwise(
                company_name=company_clean, 
                jd_text=req.jd_text or ""
            ):
                if step_id == "complete" and isinstance(detail, dict):
                    pdf_path = Path(detail["pdf_path"])
                    raw_resume_path = Path(detail["raw_resume_path"])
                    pdf_rel = pdf_path.resolve().relative_to(OUTPUT_DIR_PATH.resolve()).as_posix()
                    txt_rel = raw_resume_path.resolve().relative_to(OUTPUT_DIR_PATH.resolve()).as_posix()
                    
                    complete_payload = {
                        "status": "success",
                        "message": f"Resume tailored successfully for {company_clean}.",
                        "company": company_clean,
                        "pdf_url": f"/api/files/{pdf_rel}",
                        "txt_url": f"/api/files/{txt_rel}",
                        "raw_resume": detail["raw_resume"]
                    }
                    yield f"data: {json.dumps({'step': step_id, 'label': label, 'progress': pct, 'detail': complete_payload})}\n\n"
                else:
                    yield f"data: {json.dumps({'step': step_id, 'label': label, 'progress': pct, 'detail': detail})}\n\n"
        except Exception:
            logger.exception("Resume generation stream failed")
            yield f"event: error\ndata: {json.dumps({'detail': 'Generation failed. Please try again later.'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/api/save-edit")
@app.post("/api/render_pdf")
def save_edit_endpoint(req: SaveEditRequest):
    """Save updated raw resume text content and re-render the PDF."""
    raw_content = req.raw_text or req.content or ""
    if not raw_content and not req.txt_url:
        raise HTTPException(status_code=400, detail="Raw resume text content cannot be empty.")
        
    try:
        if req.txt_url and req.txt_url.startswith("/api/files/"):
            txt_path_str = req.txt_url.replace("/api/files/", "")
            target_txt = (OUTPUT_DIR_PATH / txt_path_str).resolve()
            if not target_txt.is_relative_to(OUTPUT_DIR_PATH.resolve()):
                raise HTTPException(status_code=403, detail="Access denied.")
            if raw_content:
                target_txt.write_text(raw_content, encoding="utf-8")
            else:
                raw_content = target_txt.read_text(encoding="utf-8")
            pdf_target = target_txt.parent / "Prasad_Rane_Resume.pdf"
            render_pdf_resume(target_txt, pdf_target)
            pdf_rel = pdf_target.resolve().relative_to(OUTPUT_DIR_PATH.resolve()).as_posix()
            return {
                "status": "success",
                "message": "Resume updated and re-rendered successfully.",
                "pdf_url": f"/api/files/{pdf_rel}?t={int(datetime.now().timestamp())}",
                "txt_url": req.txt_url,
                "raw_resume": raw_content
            }
        else:
            import tempfile, base64
            temp_out_dir = OUTPUT_DIR_PATH
            temp_out_dir.mkdir(parents=True, exist_ok=True)
            raw_path = temp_out_dir / "edited_raw_resume.txt"
            raw_path.write_text(raw_content, encoding="utf-8")
            pdf_target = temp_out_dir / "Prasad_Rane_Resume.pdf"
            render_pdf_resume(raw_path, pdf_target)
            b64_pdf = base64.b64encode(pdf_target.read_bytes()).decode("utf-8")
            return {
                "status": "success",
                "message": "Resume updated and re-rendered successfully.",
                "pdf_url": f"data:application/pdf;base64,{b64_pdf}",
                "txt_url": None,
                "raw_resume": raw_content
            }
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to update resume")
        raise HTTPException(status_code=500, detail="Failed to update resume.")


