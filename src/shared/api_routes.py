"""
api_routes.py — Shared FastAPI router for endpoints identical across both apps.

Hosts /api/query, /api/chat-stream, /api/render_pdf, and /api/save-edit —
previously duplicated verbatim in src/web/app.py and api/index.py. Both apps
include this router so there is one canonical handler per endpoint.
"""

import base64
import json
import logging
import uuid
from pathlib import Path
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from src.config import ROOT_DIR, OUTPUT_DIR_PATH
import difflib
from src.generators.pdf_renderer import render_pdf_resume
from src.query.graphrag_engine import get_engine, reset_engine
from src.query.conversation_store import get_conversation_store, reset_conversation_store
from src.query.star_generator import STARGenerator
from src.query.interview_prep import InterviewPrepGenerator
from src.query.fts_search import FTS5SearchEngine
from src.converters.profile_manager import ProfileManager
from src.generators.ats_simulator import ATSSimulator
from src.generators.cover_letter_generator import CoverLetterGenerator
from src.generators.resume_parser import parse_resume_markdown
from src.generators.typst_renderer import render_typst_markup
from src.generators.latex_renderer import render_latex_markup
from src.observability.telemetry import get_tracer
from src.generators.linkedin_optimizer import LinkedInOptimizer
from src.security.sanitizer import InputSanitizer
from src.shared.api_models import (
    QueryRequest,
    SaveEditRequest,
    BehavioralQuestionRequest,
    DiffResumeRequest,
    ATSSimulationRequest,
    CoverLetterRequest,
    InterviewPrepRequest,
    LinkedInProfileRequest,
)

logger = logging.getLogger(__name__)

shared_router = APIRouter()
_sanitizer = InputSanitizer()
_star_generator = STARGenerator()
_profile_manager = ProfileManager()
_ats_simulator = ATSSimulator()
_cover_letter_generator = CoverLetterGenerator()
_interview_prep_generator = InterviewPrepGenerator()
_linkedin_optimizer = LinkedInOptimizer()
_fts_engine = FTS5SearchEngine()
_tracer = get_tracer()


# ── GraphRAG query routes (SSE streaming) ──────────────────────────────────

@shared_router.post("/api/query")
async def query_endpoint(req: QueryRequest):
    """Execute GraphRAG query with full retrieval → LLM streaming.

    Returns a single JSON response with answer + sources for non-streaming use.
    For streaming, prefer /api/chat-stream which yields tokens incrementally.
    """
    return await _handle_query_core(req)


@shared_router.post("/api/chat-stream")
def chat_stream_endpoint(req: QueryRequest):
    """Chat stream endpoint yielding tokens incrementally via SSE.

    Supports conversation memory via session_id param.
    Response format:
      event: token   → data: {"token": "...", "done": false}
      event: done    → data: {"done": true, "response": "...", "sources": [...]}
    """
    # Validate up-front so an empty query returns 400 before we commit to the
    # streaming response (otherwise the HTTPException inside the generator
    # fires after headers are sent, and the client sees 200 + error frame).
    if not req.query or not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    return StreamingResponse(
        _stream_query_response(req),
        media_type="text/event-stream",
    )


async def _handle_query_core(req: QueryRequest) -> dict:
    """Core handling shared by both streaming and non-streaming endpoints."""
    sanitized = _sanitizer.sanitize(req.query or "")
    query = sanitized.sanitized_text
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    mode = (req.mode or "local").lower()
    if mode not in ("local", "global", "drift"):
        mode = "local"

    try:
        engine = await get_engine(ROOT_DIR)
    except (FileNotFoundError, ImportError):
        # GraphRAG artifacts not available — fall back to static search engine
        logger.info("GraphRAG artifacts not found, falling back to static search engine")
        from src.query.search_engine import execute_graphrag_query
        response_text = execute_graphrag_query(query, mode=mode)
        return {
            "status": "success",
            "query": query,
            "mode": mode,
            "session_id": req.session_id or str(uuid.uuid4()),
            "response": response_text,
            "sources": [],
        }

    try:
        try:
            store = get_conversation_store()
        except (OSError, PermissionError):
            # Read-only filesystem (Vercel serverless) — no conversation memory
            store = None
            logger.info("Conversation store unavailable (read-only filesystem), skipping memory")

        sid = req.session_id or str(uuid.uuid4())

        # Conversation history if session exists
        history = []
        if store and req.session_id and store.has_session(sid):
            history = store.get_history(sid, limit=10)

        # Stream the response (collect fully here for non-streaming API)
        resp_parts = []
        sources = []
        fallback_response = None
        async for frame in engine.chat_stream(query, mode, history):
            # Parse SSE line
            if frame.startswith("data: "):
                content = json.loads(frame[6:])
                if "token" in content:
                    resp_parts.append(content["token"])
                if content.get("done"):
                    sources = content.get("sources", [])
                    # Check for fallback response in final frame
                    if "response" in content and content["response"]:
                        fallback_response = content["response"]
                    break

        # Use fallback response if no tokens were collected
        response_text = "".join(resp_parts) or fallback_response or ""

        # Persist to conversation memory (skip if store unavailable)
        if store:
            store.add_message(sid, "user", query)
            store.add_message(sid, "assistant", response_text)

        return {
            "status": "success",
            "query": query,
            "mode": mode,
            "session_id": sid,
            "response": response_text,
            "sources": sources,
        }
    except Exception:
        logger.exception("GraphRAG query failed")
        raise HTTPException(status_code=500, detail="Query failed. Please try again later.")


async def _stream_query_response(req: QueryRequest) -> AsyncGenerator[str, None]:
    """Yield SSE frames for /api/chat-stream."""
    query = req.query.strip()
    if not query:
        yield "event: error\ndata: " + json.dumps({"detail": "Query cannot be empty."})
        return

    mode = (req.mode or "local").lower()
    if mode not in ("local", "global", "drift"):
        mode = "local"

    try:
        engine = await get_engine(ROOT_DIR)
    except (FileNotFoundError, ImportError):
        # GraphRAG artifacts not available — fall back to static search engine
        logger.info("GraphRAG artifacts not found, falling back to static search engine")
        from src.query.search_engine import execute_graphrag_query
        response_text = execute_graphrag_query(query, mode=mode)
        yield f"data: {json.dumps({'token': response_text, 'done': False})}\n\n"
        yield f"data: {json.dumps({'token': '', 'done': True, 'response': response_text, 'sources': []})}\n\n"
        return

    try:
        try:
            store = get_conversation_store()
        except (OSError, PermissionError):
            # Read-only filesystem (Vercel serverless) — no conversation memory
            store = None
            logger.info("Conversation store unavailable (read-only filesystem), skipping memory")

        sid = req.session_id or str(uuid.uuid4())

        history = []
        if store and req.session_id and store.has_session(sid):
            history = store.get_history(sid, limit=10)

        async for frame in engine.chat_stream(query, mode, history):
            yield frame

        # Persist after completion (skip if store unavailable)
        if store:
            store.add_message(sid, "user", query)
            store.add_message(sid, "assistant", "conversation complete")
    except Exception:
        logger.exception("Chat stream failed")
        yield "event: error\ndata: " + json.dumps({"detail": "Chat query failed."})


# ── PDF rendering & edit save routes ────────────────────────────────────────

def _pdf_to_data_uri(pdf_path: Path) -> str:
    pdf_bytes = pdf_path.read_bytes()
    b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
    return f"data:application/pdf;base64,{b64_pdf}"


@shared_router.post("/api/save-edit")
@shared_router.post("/api/render_pdf")
def save_edit_endpoint(req: SaveEditRequest):
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
        else:
            if not raw_content:
                raise HTTPException(status_code=400, detail="Resume text content cannot be empty.")
            temp_out_dir = OUTPUT_DIR_PATH
            temp_out_dir.mkdir(parents=True, exist_ok=True)
            raw_path = temp_out_dir / "edited_raw_resume.txt"
            raw_path.write_text(raw_content, encoding="utf-8")
            pdf_target = temp_out_dir / "Prasad_Rane_Resume.pdf"
            render_pdf_resume(raw_path, pdf_target)

        pdf_data_uri = _pdf_to_data_uri(pdf_target)
        return {
            "status": "success",
            "message": "Resume updated and re-rendered successfully.",
            "pdf_url": pdf_data_uri,
            "txt_url": req.txt_url,
            "raw_resume": raw_content,
        }
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to update resume")
        raise HTTPException(status_code=500, detail="Failed to save edit and re-render PDF.")


# ── Behavioral Interview & Profile routes ──────────────────────────────────

@shared_router.post("/api/behavioral-answer")
def behavioral_answer_endpoint(req: BehavioralQuestionRequest):
    """Generate structured Situation, Task, Action, Result interview response."""
    sanitized = _sanitizer.sanitize(req.question)
    if not sanitized.sanitized_text:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    response = _star_generator.generate_star_response(sanitized.sanitized_text, context=req.context)
    return {
        "status": "success",
        "question": req.question,
        "dimension": response.dimension,
        "situation": response.situation,
        "task": response.task,
        "action": response.action,
        "result": response.result,
        "metrics": response.metrics,
        "technologies": response.technologies,
        "markdown": response.to_markdown(),
    }


@shared_router.get("/api/profiles")
def list_profiles_endpoint():
    """List available candidate profiles and specializations."""
    profiles = _profile_manager.list_profiles()
    return {"status": "success", "profiles": profiles}


@shared_router.post("/api/diff-resume")
def diff_resume_endpoint(req: DiffResumeRequest):
    """Compute line-by-line diff between master resume and tailored resume."""
    profile = _profile_manager.get_profile(req.candidate_id or "default")
    master_lines = profile.master_resume_text.splitlines(keepends=True)
    tailored_lines = req.tailored_text.splitlines(keepends=True)
    
    diff = list(difflib.unified_diff(
        master_lines,
        tailored_lines,
        fromfile="Master Resume",
        tofile="Tailored Resume",
        n=2,
    ))
    return {
        "status": "success",
        "candidate_id": profile.candidate_id,
        "diff_text": "".join(diff),
        "total_diff_lines": len(diff),
    }


@shared_router.post("/api/ats-score")
def ats_score_endpoint(req: ATSSimulationRequest):
    """Calculate quantitative ATS match score and missing keywords."""
    report = _ats_simulator.simulate(req.resume_text, req.jd_text)
    return {
        "status": "success",
        "overall_score": report.overall_score,
        "keyword_coverage": report.keyword_coverage,
        "covered_keywords": report.covered_keywords,
        "missing_keywords": report.missing_keywords,
        "formatting_issues": report.formatting_issues,
        "is_compliant": report.is_compliant,
    }


@shared_router.post("/api/cover-letter")
def cover_letter_endpoint(req: CoverLetterRequest):
    """Generate tailored cover letter."""
    data = _cover_letter_generator.generate(
        company=req.company,
        jd_text=req.jd_text,
        candidate_name=req.candidate_name or "Prasad Rane",
        role_title=req.role_title or "Senior Software Engineer",
    )
    return {
        "status": "success",
        "company": data.company_name,
        "candidate_name": data.candidate_name,
        "role_title": data.role_title,
        "paragraphs": data.paragraphs,
        "markdown": _cover_letter_generator.render_markdown(data),
    }


@shared_router.post("/api/interview-prep")
def interview_prep_endpoint(req: InterviewPrepRequest):
    """Generate predicted interview questions and tailored talking points."""
    result = _interview_prep_generator.generate(req.jd_text)
    return {
        "status": "success",
        "questions": result.questions,
        "talking_points": result.talking_points,
    }


@shared_router.post("/api/linkedin-profile")
def linkedin_profile_endpoint(req: LinkedInProfileRequest):
    """Generate optimized LinkedIn profile assets."""
    data = _linkedin_optimizer.optimize(
        target_role=req.target_role or "Senior Software Engineer / Tech Lead",
        candidate_name=req.candidate_name or "Prasad Rane",
    )
    return {
        "status": "success",
        "headline": data.headline,
        "about_section": data.about_section,
        "experience_bullets": data.experience_bullets,
        "core_skills": data.core_skills,
    }


@shared_router.get("/api/fts-search")
def fts_search_endpoint(q: str = "", limit: int = 5):
    """Sub-millisecond local SQLite FTS5 full-text search."""
    results = _fts_engine.search(q, limit=limit)
    return {
        "status": "success",
        "query": q,
        "results": [{"title": r.title, "content": r.content, "rank": r.rank} for r in results],
    }


@shared_router.post("/api/export-markup")
def export_markup_endpoint(req: SaveEditRequest, format: str = "typst"):
    """Export resume content into Typst, LaTeX, Markdown, or Plain Text format."""
    raw_content = req.raw_text or req.content or ""
    if not raw_content and req.txt_url and req.txt_url.startswith("/api/files/"):
        txt_path_str = req.txt_url.replace("/api/files/", "")
        target_txt = (OUTPUT_DIR_PATH / txt_path_str).resolve()
        if target_txt.exists():
            raw_content = target_txt.read_text(encoding="utf-8")

    if not raw_content:
        # Fallback to master resume
        master_path = ROOT_DIR / "input" / "MASTER_RESUME.txt"
        if master_path.exists():
            raw_content = master_path.read_text(encoding="utf-8")

    fmt = format.lower().strip()
    if fmt == "typst":
        resume_data = parse_resume_markdown(raw_content)
        content = render_typst_markup(resume_data)
        filename = "Prasad_Rane_Resume.typ"
        media_type = "text/plain"
    elif fmt in ("latex", "tex"):
        resume_data = parse_resume_markdown(raw_content)
        content = render_latex_markup(resume_data)
        filename = "Prasad_Rane_Resume.tex"
        media_type = "application/x-tex"
    elif fmt in ("md", "markdown"):
        content = raw_content
        filename = "Prasad_Rane_Resume.md"
        media_type = "text/markdown"
    else:
        content = raw_content
        filename = "Prasad_Rane_Resume.txt"
        media_type = "text/plain"

    return {
        "status": "success",
        "format": fmt,
        "filename": filename,
        "content": content,
    }


@shared_router.get("/api/telemetry-stats")
def telemetry_stats_endpoint():
    """Retrieve real-time latency percentiles and span summaries."""
    retrieval_stats = _tracer.get_summary("retrieval.local")
    gateway_stats = _tracer.get_summary("gateway.call")
    render_stats = _tracer.get_summary("pdf.render")

    return {
        "status": "success",
        "spans": {
            "retrieval": retrieval_stats,
            "gateway": gateway_stats,
            "pdf_render": render_stats,
        },
        "engine_status": "healthy",
    }
