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
from src.generators.pdf_renderer import render_pdf_resume
from src.query.graphrag_engine import get_engine, reset_engine
from src.query.conversation_store import get_conversation_store, reset_conversation_store
from src.shared.api_models import QueryRequest, SaveEditRequest

logger = logging.getLogger(__name__)

shared_router = APIRouter()


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
    return StreamingResponse(
        _stream_query_response(req),
        media_type="text/event-stream",
    )


async def _handle_query_core(req: QueryRequest) -> dict:
    """Core handling shared by both streaming and non-streaming endpoints."""
    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    mode = (req.mode or "local").lower()
    if mode not in ("local", "global", "drift"):
        mode = "local"

    try:
        engine = await get_engine(ROOT_DIR)
        store = get_conversation_store()
        sid = req.session_id or str(uuid.uuid4())

        # Conversation history if session exists
        history = []
        if req.session_id and store.has_session(sid):
            history = store.get_history(sid, limit=10)

        # Stream the response (collect fully here for non-streaming API)
        resp_parts = []
        sources = []
        async for frame in engine.chat_stream(query, mode, history):
            # Parse SSE line
            if frame.startswith("data: "):
                content = json.loads(frame[6:])
                if "token" in content:
                    resp_parts.append(content["token"])
                if content.get("done"):
                    sources = content.get("sources", [])
                    break

        response_text = "".join(resp_parts)

        # Persist to conversation memory
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
        store = get_conversation_store()
        sid = req.session_id or str(uuid.uuid4())

        history = []
        if req.session_id and store.has_session(sid):
            history = store.get_history(sid, limit=10)

        async for frame in engine.chat_stream(query, mode, history):
            yield frame

        # Persist after completion
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
        raise HTTPException(status_code=500, detail="Failed to update resume.")
