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
from src.generators.resume_generator import generate_raw_resume, parse_resume_markdown, format_tailored_markdown, generate_raw_resume_stepwise
from src.generators.pdf_renderer import render_pdf_resume
from src.config import MASTER_RESUME_PATH, WEB_STATIC_DIR
from fastapi.responses import FileResponse, StreamingResponse

app = FastAPI(title="Prasad Resumes GraphRAG Vercel API", version="1.0.0")

class ResumeGenerationRequest(BaseModel):
    company: str
    jd_text: str

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
@app.post("/api/save-edit")
def render_pdf_endpoint(req: RenderPdfRequest):
    try:
        text_content = req.raw_text or ""
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
    try:
        temp_out_dir = Path(tempfile.gettempdir()) / "output"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to resolve temp dir: {str(e)}")

    def event_generator():
        try:
            for step_id, label, pct, detail in generate_raw_resume_stepwise(
                company_name=req.company, 
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
                        "company": req.company,
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


from src.query.search_engine import execute_graphrag_query
from src.query.static_graph_reader import read_precomputed_entities

class QueryRequest(BaseModel):
    query: str
    mode: Optional[str] = "local"


@app.post("/api/chat-stream")
def chat_stream_endpoint(req: QueryRequest):
    import json
    query_clean = req.query.strip()
    if not query_clean:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    
    mode_clean = req.mode.lower().strip() if req.mode else "local"
    if mode_clean not in ["local", "global"]:
        mode_clean = "local"
        
    def event_generator():
        try:
            # 1. Search sources
            keywords = [w.strip("?,.()\"'") for w in query_clean.lower().split() if len(w) > 3]
            entities = read_precomputed_entities()
            sources = []
            if entities and keywords:
                for entity in entities:
                    title = entity.get("title", "")
                    content = entity.get("content", "")
                    text = (title + " " + content).lower()
                    if any(kw in text for kw in keywords):
                        sources.append(title)
            sources = list(set(sources))[:5]
            
            # Emit sources
            yield f"event: sources\ndata: {json.dumps({'sources': sources})}\n\n"
            
            # 2. Get LLM response
            response_text = execute_graphrag_query(query=query_clean, mode=mode_clean, root_dir=ROOT_DIR)
            
            # Emit token
            yield f"event: token\ndata: {json.dumps({'token': response_text})}\n\n"
            
            # Emit done
            yield f"event: done\ndata: {json.dumps({'response': response_text, 'sources': sources})}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'detail': str(e)})}\n\n"
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")


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


