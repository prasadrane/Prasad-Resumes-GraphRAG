"""
app.py — FastAPI Web Backend for Prasad Resumes GraphRAG UI.
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.config import ROOT_DIR, OUTPUT_DIR_PATH, MASTER_RESUME_PATH, WEB_STATIC_DIR as STATIC_DIR
from src.shared.api_models import ResumeGenerationRequest, AgenticResumeRequest

from src.generators.ats_matcher import extract_ats_keywords
from src.generators.resume_generator import generate_raw_resume, parse_resume_markdown, format_tailored_markdown, generate_raw_resume_stepwise
from src.generators.page_budgeter import budget_resume_for_pages
from src.generators.pdf_renderer import render_pdf_resume, render_pdf_from_model, _pdf_to_data_uri
from src.agents.orchestrator import AgenticPipelineOrchestrator

# ── Observability imports ─────────────────────────────────────────────────
from src.observability import (
    get_correlation_id,
    logger as obs_logger,
    set_correlation_id,
)
from src.metrics import collect_as_text, get_collector

logger = logging.getLogger(__name__)

# ── Correlation-ID middleware (W4.2) ──────────────────────────────────────

app = FastAPI(title="Prasad Resumes GraphRAG UI", version="1.0.0")



@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    """Extract or generate a correlation ID, store it in ContextVar, pass through headers."""
    header = request.headers.get("X-Correlation-ID")
    if header:
        set_correlation_id(header)
    else:
        import uuid
        set_correlation_id(str(uuid.uuid4()))
    cid = get_correlation_id()
    start = time.time()

    response = await call_next(request)

    elapsed_ms = (time.time() - start) * 1000
    response.headers["X-Correlation-ID"] = cid
    response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.1f}"
    return response


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


@app.get("/api/health")
async def health_check():
    """Detailed health-check with dependency status for Kubernetes/Docker probes.

    Returns 200 when all dependencies are healthy, 503 when any critical dep fails.
    Status values: ok / degraded / down
    """
    checks = {}
    overall = "ok"

    # -- API itself (always up if we're executing) --
    checks["api"] = {"status": "ok"}

    # -- LLM Gateway -- quick probe: try resolving a model (cheap no-API-key-needed op)
    try:
        from src.config.providers import get_model_for as _gmf
        start_t = time.time()
        try:
            resolved = _gmf("chat")[1]  # resolves to model ID without hitting network
        except Exception:
            resolved = "unknown"
        latency_ms = (time.time() - start_t) * 1000

        # Attempt a minimal provider probe (check key availability is enough for non-prod)
        provider_name = _gmf("chat")[0]
        checks["llm_gateway"] = {
            "status": "ok",
            "provider": provider_name,
            "model": resolved,
            "latency_ms": round(latency_ms, 1),
        }
    except Exception as err:
        checks["llm_gateway"] = {"status": "down", "error": str(err)}
        overall = "degraded"

    # -- GraphRAG / Knowledge Base --
    try:
        from src.config import OUTPUT_DIR_PATH
        if (OUTPUT_DIR_PATH / "entities.parquet").exists() or (ROOT_DIR / "output" / "entities.parquet").exists():
            checks["graphrag"] = {"status": "ok", "mode": "parquet_index"}
        elif MASTER_RESUME_PATH.exists():
            checks["graphrag"] = {
                "status": "ok",
                "mode": "static_fallback",
                "source": MASTER_RESUME_PATH.name,
            }
        else:
            checks["graphrag"] = {
                "status": "degraded",
                "missing": ["entities.parquet", "MASTER_RESUME.txt"],
            }
            overall = "degraded"
    except Exception as err:
        checks["graphrag"] = {"status": "down", "error": str(err)}
        overall = "degraded"

    # -- Database (conversation store) -- verify SQLite accessible
    try:
        from src.query.conversation_store import get_conversation_store
        store = get_conversation_store()
        checks["database"] = {
            "status": "ok",
            "path": str(store.db_path),
        }
    except Exception as err:
        checks["database"] = {"status": "down", "error": str(err)}
        overall = "down"

    # Final verdict: 503 only when core services (API / database) are down
    status = overall
    code = 503 if overall == "down" else 200

    result = {
        "status": status,
        "checks": checks,
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    return JSONResponse(content=result, status_code=code)


@app.get("/")
def read_root():
    """Serve main single-page interface."""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return JSONResponse({"message": "Prasad Resumes GraphRAG API Server Active. UI static assets missing."})


@app.post("/api/keywords")
def get_keywords(req: ResumeGenerationRequest):
    """Extract ATS keywords from job description text."""
    kws = extract_ats_keywords(req.jd_text)
    return {"company": req.company, "keywords": kws}


@app.get("/api/default-resume")
@app.get("/api/default_resume")
def get_default_resume_endpoint(pages: int = Query(2, ge=1, le=2)):
    """Fetch default master resume raw text and PDF preview (1-page or 2-page)."""
    master_path = MASTER_RESUME_PATH
    if not master_path.exists():
        raise HTTPException(status_code=404, detail="MASTER_RESUME.txt file not found.")

    try:
        master_content = master_path.read_text(encoding="utf-8")
        parsed = parse_resume_markdown(master_content)
        budgeted = budget_resume_for_pages(parsed, target_pages=pages)
        clean_raw_resume = format_tailored_markdown(budgeted, [])

        try:
            out_dir = OUTPUT_DIR_PATH / "Default"
            out_dir.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError):
            import tempfile
            out_dir = Path(tempfile.gettempdir()) / "output" / "Default"
            out_dir.mkdir(parents=True, exist_ok=True)

        try:
            txt_target = out_dir / "raw_resume.txt"
            txt_target.write_text(clean_raw_resume, encoding="utf-8")
        except (OSError, PermissionError):
            pass

        pdf_target = out_dir / "Prasad_Rane_Resume.pdf"
        actual_pdf_path = render_pdf_from_model(parsed, pdf_target, target_pages=pages)
        pdf_data_uri = _pdf_to_data_uri(actual_pdf_path)

        return {
            "status": "success",
            "pdf_url": pdf_data_uri,
            "pdf_data_uri": pdf_data_uri,
            "txt_url": None,
            "raw_resume": clean_raw_resume,
            "pages": pages,
        }
    except Exception:
        logger.exception("Failed to load default resume")
        raise HTTPException(status_code=500, detail="Failed to load default resume.")


@app.get("/api/default-resume-pdf")
@app.get("/api/default_resume_pdf")
def get_default_resume_pdf_endpoint(pages: int = Query(2, ge=1, le=2)):
    """Directly stream default master resume PDF for native browser and iframe rendering."""
    master_path = MASTER_RESUME_PATH
    if not master_path.exists():
        raise HTTPException(status_code=404, detail="MASTER_RESUME.txt file not found.")

    try:
        master_content = master_path.read_text(encoding="utf-8")
        parsed = parse_resume_markdown(master_content)

        try:
            out_dir = OUTPUT_DIR_PATH / "Default"
            out_dir.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError):
            import tempfile
            out_dir = Path(tempfile.gettempdir()) / "output" / "Default"
            out_dir.mkdir(parents=True, exist_ok=True)

        pdf_target = out_dir / "Prasad_Rane_Resume.pdf"
        actual_pdf_path = render_pdf_from_model(parsed, pdf_target, target_pages=pages)

        pdf_bytes = actual_pdf_path.read_bytes()
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": 'inline; filename="Prasad_Rane_Resume.pdf"'},
        )
    except Exception:
        logger.exception("Failed to stream default resume PDF")
        raise HTTPException(status_code=500, detail="Failed to render default resume PDF.")


@app.get("/api/history", response_model=List[ResumeHistoryItem])
def get_resume_history():
    """Fetch history of tailored resumes from the output directory (recursively scanning all company folders)."""
    history = []
    if not OUTPUT_DIR_PATH.exists():
        return history

    # Scan output directory recursively for PDF files
    for pdf_path in OUTPUT_DIR_PATH.rglob("*.pdf"):
        if pdf_path.is_file():
            company_name = pdf_path.parent.name
            mod_time = datetime.fromtimestamp(pdf_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")

            # Encode PDF as base64 data URI
            try:
                pdf_data_uri = _pdf_to_data_uri(pdf_path)
            except Exception:
                logger.warning("Failed to read PDF for history: %s", pdf_path)
                continue

            history.append(
                ResumeHistoryItem(
                    company=company_name,
                    date=mod_time,
                    pdf_filename=pdf_path.name,
                    pdf_url=pdf_data_uri,
                    txt_filename=None,
                    txt_url=None,
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



@app.post("/api/generate")
def generate_resume_endpoint(req: ResumeGenerationRequest):
    """Generate a tailored raw resume text and rule-based PDF."""
    company_clean = req.company.strip()
    if not company_clean:
        raise HTTPException(status_code=400, detail="Company name cannot be empty.")

    try:
        pages = req.target_pages or 2
        # Step 1: Generate tailored raw resume text
        raw_text_path = generate_raw_resume(company_name=company_clean, jd_text=req.jd_text or "", target_pages=pages)

        # Step 2: Render ATS-compliant PDF
        pdf_output_target = raw_text_path.parent / "Prasad_Rane_Resume.pdf"
        pdf_path = render_pdf_resume(raw_text_path, pdf_output_target, target_pages=pages)

        pdf_data_uri = _pdf_to_data_uri(Path(pdf_path))

        return {
            "status": "success",
            "message": f"Resume tailored successfully for {company_clean}.",
            "company": company_clean,
            "pdf_url": pdf_data_uri,
            "txt_url": None,
            "raw_resume": raw_text_path.read_text(encoding="utf-8"),
            "pages": pages,
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

    pages = req.target_pages or 2

    def event_generator():
        try:
            for step_id, label, pct, detail in generate_raw_resume_stepwise(
                company_name=company_clean,
                jd_text=req.jd_text or "",
                target_pages=pages,
            ):
                if step_id == "complete" and isinstance(detail, dict):
                    pdf_path = Path(detail["pdf_path"])
                    pdf_data_uri = _pdf_to_data_uri(pdf_path)

                    complete_payload = {
                        "status": "success",
                        "message": f"Resume tailored successfully for {company_clean}.",
                        "company": company_clean,
                        "pdf_url": pdf_data_uri,
                        "txt_url": "",
                        "raw_resume": detail["raw_resume"],
                        "pages": pages,
                    }
                    yield f"data: {json.dumps({'step': step_id, 'label': label, 'progress': pct, 'detail': complete_payload})}\n\n"
                else:
                    yield f"data: {json.dumps({'step': step_id, 'label': label, 'progress': pct, 'detail': detail})}\n\n"
        except Exception:
            logger.exception("Resume generation stream failed")
            yield f"event: error\ndata: {json.dumps({'detail': 'Generation failed. Please try again later.'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/api/stream-agent-tailor")
def stream_agent_tailor_endpoint(req: AgenticResumeRequest):
    """Execute autonomous Multi-Subagent Evaluator-Optimizer loop with real-time SSE stream."""
    import json
    
    url_clean = (req.url or "").strip()
    jd_clean = (req.jd_text or "").strip()
    company_clean = (req.company or "").strip()
    
    if not url_clean and not jd_clean and not company_clean:
        raise HTTPException(status_code=400, detail="Must provide either a job URL, job description text, or target company.")
        
    pages = req.target_pages or 2
    min_score = req.min_score or 90.0
    max_iter = req.max_iterations or 2

    def event_stream():
        try:
            orchestrator = AgenticPipelineOrchestrator()
            for event in orchestrator.run(
                jd_text=jd_clean,
                url=url_clean or None,
                company_name=company_clean or None,
                max_iterations=max_iter,
                min_score=min_score,
                target_pages=pages,
            ):
                event_dict = event.model_dump()
                if event.step == "complete" and "pdf_path" in event.payload:
                    pdf_p = Path(event.payload["pdf_path"])
                    if pdf_p.exists():
                        event_dict["payload"]["pdf_url"] = _pdf_to_data_uri(pdf_p)
                yield f"data: {json.dumps(event_dict)}\n\n"
        except Exception:
            logger.exception("Agentic stream failed")
            yield f"event: error\ndata: {json.dumps({'detail': 'Agentic optimization failed. Please try again.'})}\n\n"

    headers = {
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
        "Content-Type": "text/event-stream; charset=utf-8",
    }
    return StreamingResponse(event_stream(), media_type="text/event-stream", headers=headers)


@app.get("/api/metrics")
def metrics_endpoint():
    """Prometheus-compatible metrics endpoint.

    Returns all collected counters and histograms in Prometheus exposition
    text format (``# HELP``, ``# TYPE``, metric lines).
    """
    collector = get_collector()
    body = collect_as_text(collector)
    return Response(content=body, media_type="text/plain; charset=utf-8")


# ── Shared API router inclusion ───────────────────────────────────────────
from src.shared.api_routes import shared_router

app.include_router(shared_router)





