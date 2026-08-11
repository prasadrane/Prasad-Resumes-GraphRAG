"""
api_routes.py — Shared FastAPI router for endpoints identical across both apps.

Hosts /api/query, /api/chat-stream, /api/render_pdf, and /api/save-edit —
previously duplicated verbatim in src/web/app.py and api/index.py. Both apps
include this router so there is one canonical handler per endpoint.
"""

import base64
import json
import logging
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from src.config import ROOT_DIR, OUTPUT_DIR_PATH
from src.generators.pdf_renderer import render_pdf_resume
from src.query.search_engine import execute_graphrag_query
from src.query.static_graph_reader import read_precomputed_entities
from src.shared.api_models import QueryRequest, SaveEditRequest

logger = logging.getLogger(__name__)

shared_router = APIRouter()


@shared_router.post("/api/query")
def query_endpoint(req: QueryRequest):
    """Execute GraphRAG query against Prasad's resumes knowledge graph."""
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
    except Exception:
        logger.exception("GraphRAG query failed")
        raise HTTPException(status_code=500, detail="Query failed. Please try again later.")


@shared_router.post("/api/chat-stream")
def chat_stream_endpoint(req: QueryRequest):
    """Chat stream endpoint yielding sources and responses via SSE."""
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

            # Emit token/response
            yield f"event: token\ndata: {json.dumps({'token': response_text})}\n\n"

            # Emit done
            yield f"event: done\ndata: {json.dumps({'response': response_text, 'sources': sources})}\n\n"
        except Exception:
            logger.exception("Chat stream failed")
            yield f"event: error\ndata: {json.dumps({'detail': 'Chat query failed. Please try again later.'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


def _pdf_to_data_uri(pdf_path: Path) -> str:
    """Read a rendered PDF and return a base64 data URI."""
    pdf_bytes = pdf_path.read_bytes()
    b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
    return f"data:application/pdf;base64,{b64_pdf}"


@shared_router.post("/api/save-edit")
@shared_router.post("/api/render_pdf")
def save_edit_endpoint(req: SaveEditRequest):
    """Save updated raw resume text content and re-render the PDF.

    Always returns a base64 data URI for ``pdf_url`` so both local and
    serverless deployments share one response contract.  When ``txt_url``
    carries an ``/api/files/`` prefix the handler resolves the path on
    disk (with traversal protection) so the source text file is updated
    in place; otherwise the text is written to a scratch file under the
    output directory.
    """
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
