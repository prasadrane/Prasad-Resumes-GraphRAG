"""
api_routes.py — Shared FastAPI router for endpoints identical across both apps.

Hosts /api/query and /api/chat-stream, previously duplicated verbatim in
src/web/app.py and api/index.py. Both apps include this router.
"""

import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from src.config import ROOT_DIR
from src.query.search_engine import execute_graphrag_query
from src.query.static_graph_reader import read_precomputed_entities
from src.shared.api_models import QueryRequest

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
