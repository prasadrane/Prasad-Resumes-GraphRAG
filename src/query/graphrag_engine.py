"""
graphrag_engine.py — Real GraphRAG query engine backed by LanceDB vector search
and parquet artifacts from Microsoft GraphRAG indexing.

Supports three query modes:
- local:  Entity-focused retrieval via text-unit vector search + entity/relationship extraction
- global: Community-report summary retrieval for high-level answers
- drift:  Multi-hop reasoning expanding from seed entities through the relationship graph

Gracefully falls back to static_text reader when parquet/LanceDB artifacts are missing.
"""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any, AsyncGenerator
import asyncio
import json

import pandas as pd
import lancedb

from src.config import ROOT_DIR

# Lazy-loaded artifact columns (avoid loading unused data)
_ENTITY_COLS = ["id", "title", "type", "description", "text_unit_ids", "frequency", "degree"]
_REL_COLS = ["id", "source", "target", "description", "weight", "combined_degree"]
_COMMUNITY_COLS = [
    "id", "title", "summary", "full_content", "rank", "level", "size",
]
_TEXT_UNIT_COLS = ["id", "text", "n_tokens", "document_ids", "entity_ids"]


class GraphRAGEngine:
    """Loads GraphRAG parquet artifacts into memory and exposes retrieval/search methods."""

    def __init__(self, root_dir=None):
        self.root_dir = Path(root_dir) if root_dir else ROOT_DIR
        self._db: Optional["lancedb.DBConnection"] = None
        self._entities: Optional[pd.DataFrame] = None
        self._relationships: Optional[pd.DataFrame] = None
        self._communities: Optional[pd.DataFrame] = None
        self._text_units: Optional[pd.DataFrame] = None

    # ── public initialisation helpers ──────────────────────────────────────

    @property
    def connected(self) -> bool:
        return self._db is not None and self._entities is not None

    async def connect(self) -> "GraphRAGEngine":
        """Connect to LanceDB and load parquet artefacts (raises FileNotFoundError)."""
        await asyncio.get_running_loop().run_in_executor(
            None, self._sync_connect
        )
        return self

    # Synchronous work runs off the event loop so it never blocks async callers.

    def _sync_connect(self) -> None:
        lancedb_path = self.root_dir / "output" / "lancedb"
        parquet_dir = self.root_dir / "output"

        if not lancedb_path.exists():
            raise FileNotFoundError(f"LanceDB directory not found: {lancedb_path}")

        self._db = lancedb.connect(str(lancedb_path))

        # ── load parquet artefacts (read-once per process) ────────────────
        self._entities = self._load_parquet(
            parquet_dir / "entities.parquet", _ENTITY_COLS
        )
        self._relationships = self._load_parquet(
            parquet_dir / "relationships.parquet", _REL_COLS
        )
        self._communities = self._load_parquet(
            parquet_dir / "community_reports.parquet", _COMMUNITY_COLS
        )
        self._text_units = self._load_parquet(
            parquet_dir / "text_units.parquet", _TEXT_UNIT_COLS
        )

    @staticmethod
    def _load_parquet(path: Path, columns: List[str]) -> pd.DataFrame:
        if not path.exists():
            raise FileNotFoundError(f"Missing GraphRAG artefact: {path}")
        return pd.read_parquet(path, columns=columns)

    async def disconnect(self) -> None:
        self._db = None

    # ── embedding helper ──────────────────────────────────────────────────

    async def get_embedding(self, text: str) -> List[float]:
        """Delegate embedding generation to serverless_gateway (OpenRouter → Gemini)."""
        from src.query.serverless_gateway import get_embedding as _get_emb
        return await _get_emb(text)

    # ── fallback keyword-based retrieval (when embeddings unavailable) ────

    def _keyword_search(self, df: pd.DataFrame, text_col: str, query: str, top_k: int = 10) -> pd.DataFrame:
        """Simple keyword search fallback when vector embeddings fail."""
        if df.empty:
            return df

        # Tokenize query (simple split, lowercase)
        query_terms = set(query.lower().split())

        def score_row(row):
            text = str(row.get(text_col, "")).lower()
            if not text.strip():
                return 0
            # Count matching terms
            return sum(1 for term in query_terms if term in text)

        # Score each row
        df_copy = df.copy()
        df_copy["_score"] = df_copy.apply(score_row, axis=1)

        # Filter rows with score > 0, sort by score desc, take top_k
        matches = df_copy[df_copy["_score"] > 0].sort_values("_score", ascending=False).head(top_k)
        return matches.drop(columns=["_score"])

    # ── retrieval modes ───────────────────────────────────────────────────

    async def retrieve(
        self, query: str, mode: str = "local", top_k: int = 10
    ) -> Dict[str, Any]:
        """Single-entry retrieval dispatcher."""
        if mode == "local":
            return await self._local_retrieval(query, top_k=top_k)
        elif mode == "global":
            return await self._global_retrieval(query, top_k=min(top_k // 2, 5))
        elif mode == "drift":
            return await self._drift_retrieval(query, top_k=top_k)
        else:
            raise ValueError(f"Unknown GraphRAG mode: {mode!r}. Choose local/global/drift.")

    # ── local mode: vector-search text-units, resolve entities & rels ────

    async def _local_retrieval(self, query: str, top_k: int = 10) -> Dict[str, Any]:
        # Try vector search first, fall back to keyword search if embeddings fail
        try:
            table = self._db.open_table("default-text_unit-text")
            emb = await self.get_embedding(query)
            results = table.search(emb).limit(top_k).to_pandas()
        except Exception as e:
            # Fallback to keyword search on text_units parquet
            results = self._keyword_search(self._text_units, "text", query, top_k)

        text_unit_ids: List[Any] = results["id"].tolist()

        # Entities that authored these units
        mask = self._entities["text_unit_ids"].apply(
            lambda arr: any(_tid_match(tid, arr) for tid in text_unit_ids)
        )
        relevant_ents = self._entities[mask].head(20)
        ent_ids = relevant_ents["id"].tolist()

        # Relationships involving those entities
        rel_mask = (
            self._relationships["source"].isin(ent_ids)
            | self._relationships["target"].isin(ent_ids)
        )
        relevant_rels = self._relationships[rel_mask].head(30)

        return {
            "text_units": results.head(10),
            "entities": relevant_ents.head(20),
            "relationships": relevant_rels.head(30),
        }

    # ── global mode: community reports ranked by semantic similarity ─────

    async def _global_retrieval(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        # Try vector search first, fall back to keyword search if embeddings fail
        try:
            table = self._db.open_table("default-community-full_content")
            emb = await self.get_embedding(query)
            results = table.search(emb).limit(top_k).to_pandas()
        except Exception:
            # Fallback to keyword search on community reports
            results = self._keyword_search(self._communities, "full_content", query, top_k)
        return {"communities": results}

    # ── drift mode: multi-hop entity expansion over relationships ─────────

    async def _drift_retrieval(self, query: str, top_k: int = 10) -> Dict[str, Any]:
        base = await self._local_retrieval(query, top_k=top_k)

        seed_ents = base["entities"].head(5)
        seen_ids: set = set(seed_ents["id"])

        expanded: List[Dict[str, Any]] = []
        for _, row in seed_ents.iterrows():
            eid = row["id"]
            connected = self._relationships[
                (self._relationships["source"] == eid)
                | (self._relationships["target"] == eid)
            ].head(3)
            for _, rel in connected.iterrows():
                other_id = (
                    rel["target"] if rel["source"] == eid else rel["source"]
                )
                if other_id not in seen_ids:
                    match = self._entities[self._entities["id"] == other_id]
                    if not match.empty:
                        rec = match.iloc[0].to_dict()
                        expanded.append(rec)
                        seen_ids.add(other_id)

        # Deduplicate (in case multiple seeds point to the same neighbour)
        unique_expanded: List[Dict[str, Any]] = []
        got: set = set()
        for e in expanded:
            key = e.get("id")
            if key is not None and key not in got:
                unique_expanded.append(e)
                got.add(key)

        result_entities = pd.concat(
            [seed_ents.head(5), pd.DataFrame(unique_expanded[:10])]
        ).drop_duplicates(subset=["id"]).reset_index(drop=True)

        return {
            "text_units": base["text_units"],
            "entities": result_entities,
            "relationships": base["relationships"],
        }

    # ── prompt assembly helpers (consumed by API route) ───────────────────

    @staticmethod
    def format_context(context: Dict[str, Any]) -> str:
        """Render a retrieved *context* dict into a human-readable string for LLM ingestion."""
        parts: List[str] = []

        if not context:
            return ""

        tUs = context.get("text_units")
        if tUs is not None and not tUs.empty:
            parts.append("## Relevant Text Segments")
            for _, tu in tUs.head(5).iterrows():
                txt = str(tu.get("text", ""))[:500]
                if txt.strip():
                    parts.append(f"- [{tu.get('id', '')}] {txt}")

        ents = context.get("entities")
        if ents is not None and not ents.empty:
            parts.append("\n## Key Entities")
            for _, e in ents.head(10).iterrows():
                name = e.get("title", "") or e.get("name", "") or e.get("id", "")
                desc = str(e.get("description", ""))[:200]
                if name or desc:
                    parts.append(f"- **{name}** ({e.get('type', '')}): {desc}")

        rels = context.get("relationships")
        if rels is not None and not rels.empty:
            parts.append("\n## Relationships")
            for _, r in rels.head(10).iterrows():
                src = str(r.get("source", ""))[:40]
                tgt = str(r.get("target", ""))[:40]
                desc = str(r.get("description", ""))[:150]
                parts.append(f"- {src} → {tgt}: {desc}")

        comms = context.get("communities")
        if comms is not None and not comms.empty:
            parts.append("\n## Community Reports")
            for _, c in comms.head(3).iterrows():
                title = c.get("title", "") or c.get("id", "")
                content = str(c.get("full_content", ""))[:500]
                parts.append(f"- **{title}** (rank {c.get('rank', '')}): {content}")

        return "\n".join(parts)

    @staticmethod
    def extract_sources(context: Dict[str, Any]) -> List[Dict[str, str]]:
        sources: List[Dict[str, str]] = []
        ents = context.get("entities")
        if ents is not None and not ents.empty:
            for _, e in ents.head(5).iterrows():
                sources.append({
                    "type": "entity",
                    "name": e.get("title", "") or e.get("name", ""),
                    "description": str(e.get("description", ""))[:100],
                })
        comms = context.get("communities")
        if comms is not None and not comms.empty:
            for _, c in comms.head(3).iterrows():
                sources.append({
                    "type": "community",
                    "title": c.get("title", "") or c.get("id", ""),
                    "summary": str(c.get("full_content", ""))[:150],
                })
        return sources

    # ── convenience entry-point used by /api/chat-stream (SSE streaming) ─

    async def chat_stream(
        self,
        query: str,
        mode: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream a GraphRAG answer token-by-token via SSE frames.

        This method combines retrieval → prompt assembly → LLM streaming
        into a single pipeline.  The caller wraps each yielded value in
        ``data: ...\\n\\n`` framing inside the FastAPI StreamingResponse handler.
        """
        # Retrieve context
        context = await self.retrieve(query, mode=mode)

        # Build system prompt
        sys_prompt = self._build_system_prompt(mode, context, conversation_history)

        full_resp_parts: List[str] = []

        # Delegate actual token streaming to serverless_gateway
        try:
            from src.query.serverless_gateway import (
                call_serverless_llm_stream,
            )

            async for token in call_serverless_llm_stream(
                sys_prompt=sys_prompt,
                user_message=query,
                temperature=0.3,
            ):
                full_resp_parts.append(token)
                yield f"data: {json.dumps({'token': token, 'done': False})}\n\n"

            response_text = "".join(full_resp_parts)
            final_frame = json.dumps({
                'done': True,
                'sources': self.extract_sources(context),
                'response': response_text,
            })
            yield f"data: {final_frame}\n\n"

        except Exception:
            # If no streaming impl exists yet (serverless_gateway may not have
            # the streaming helpers until Task 2.5 completes), fall back to
            # a single-shot block so the engine still produces an answer.
            sources = self.extract_sources(context)
            ctx_str = self.format_context(context)
            answer = (
                f"Retrieved GraphRAG context.\n\nContext:\n{ctx_str}\n\n"
                f"*Answer:* (LLM streaming not available — enable streaming support in Task 2.5)"
            )
            yield f"data: {json.dumps({'token': '', 'done': False})}\n\n"
            final_frame = json.dumps({
                'done': True,
                'sources': sources,
                'response': answer,
            })
            yield f"data: {final_frame}\n\n"

    # ── internal helpers ──────────────────────────────────────────────────

    def _build_system_prompt(
        self,
        mode: str,
        context: Dict[str, Any],
        history: Optional[List[Dict[str, str]]],
    ) -> str:
        personas = {
            "local": (
                "You are a knowledgeable assistant answering questions about Prasad Rane's professional experience. "
                "Use the provided entity and relationship data to give specific, detailed answers."
            ),
            "global": (
                "You are a career analyst providing executive-level summaries of Prasad Rane's professional trajectory. "
                "Use the provided community reports to give high-level insights."
            ),
            "drift": (
                "You are a career researcher performing multi-hop analysis of Prasad Rane's professional experience. "
                "Connect information across entities and relationships to provide comprehensive answers."
            ),
        }
        sys_msg = personas.get(mode, personas["local"])

        hist = ""
        if history:
            pairs = history[-6:]  # last 3 exchanges (user+assistant)
            hist_lines = [f"{m['role']}: {m['content']}" for m in pairs]
            hist = "\n\nPrevious conversation:\n" + "\n".join(hist_lines)

        return f"{sys_msg}\n\nContext:\n{self.format_context(context)}{hist}"


# ── module-level singleton (lazy init, safe for concurrent use) ────────────────

_lock = asyncio.Lock()
_engine: Optional[GraphRAGEngine] = None


async def get_engine(root_dir=None):
    """Return a shared GraphRAGEngine instance (singleton per root_dir)."""
    global _engine
    rd = Path(root_dir) if root_dir else ROOT_DIR
    async with _lock:
        if _engine is None or _engine.root_dir != rd:
            _engine = GraphRAGEngine(str(rd))
            await _engine.connect()
        return _engine


def reset_engine() -> None:
    """Reset singleton — useful for tests."""
    global _engine
    _engine = None


# ── small private utility ─────────────────────────────────────────────────────

def _tid_match(tid: Any, arr: Any) -> bool:
    """Check whether *tid* appears inside *arr*, handling ndarray / list / set types."""
    if arr is None:
        return False
    if isinstance(arr, str):
        return tid == arr or str(tid) in arr
    if hasattr(arr, "__iter__"):
        try:
            return any(str(x) == str(tid) for x in arr)
        except TypeError:
            return False
    return False
