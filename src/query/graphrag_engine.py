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
from typing import Optional, List, Dict, Any, AsyncGenerator, Tuple
import asyncio
import json

import pandas as pd

try:
    import lancedb
    _HAS_LANCEDB = True
except ImportError:
    lancedb = None  # type: ignore
    _HAS_LANCEDB = False

from src.config import ROOT_DIR
from src.query.bm25_search import BM25Index, reciprocal_rank_fusion

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
        self._tu_bm25: Optional[BM25Index] = None
        self._ent_bm25: Optional[BM25Index] = None
        self._comm_bm25: Optional[BM25Index] = None

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
        from src.gateway import get_embedding as _get_emb
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

    async def retrieve_healed(
        self, query: str, mode: str = "local", top_k: int = 10
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Retrieve context with autonomous self-healing guardrail verification.
        
        Evaluates context density and entity coverage; if insufficient, retries across
        fallback modes (local -> drift -> global) to maximize answer quality.
        """
        from .retrieval_guardrail import RetrievalGuardrail
        from .intent_classifier import IntentClassifier

        guardrail = RetrievalGuardrail()
        classifier = IntentClassifier()
        details = classifier.classify_with_details(query)
        extracted_entities = details.get("extracted_entities", [])

        # 1. Attempt initial retrieval mode
        initial_ctx = await self.retrieve(query, mode=mode, top_k=top_k)
        initial_formatted = self.format_context(initial_ctx)
        report = guardrail.evaluate_context(query, initial_formatted, extracted_entities)

        if report.is_sufficient:
            return initial_ctx, []

        # 2. Execute self-healing escalation across fallback modes
        best_ctx = initial_ctx
        best_token_count = len(initial_formatted.split())
        trace: List[Dict[str, Any]] = [
            {
                "attempt": 1,
                "mode": mode,
                "is_sufficient": report.is_sufficient,
                "token_count": report.token_count,
                "issues": report.detected_issues,
            }
        ]

        fallback_modes = [m for m in ["local", "drift", "global"] if m != mode]
        for attempt_idx, next_mode in enumerate(fallback_modes, start=2):
            next_ctx = await self.retrieve(query, mode=next_mode, top_k=top_k)
            next_formatted = self.format_context(next_ctx)
            next_report = guardrail.evaluate_context(query, next_formatted, extracted_entities)

            trace.append({
                "attempt": attempt_idx,
                "mode": next_mode,
                "is_sufficient": next_report.is_sufficient,
                "token_count": next_report.token_count,
                "issues": next_report.detected_issues,
            })

            curr_tokens = len(next_formatted.split())
            if next_report.is_sufficient:
                return next_ctx, trace
            elif curr_tokens > best_token_count:
                best_ctx = next_ctx
                best_token_count = curr_tokens

        return best_ctx, trace

    # ── local mode: hybrid vector + BM25 search text-units, resolve entities & rels ────

    async def _local_retrieval(self, query: str, top_k: int = 26) -> Dict[str, Any]:
        """Hybrid retrieval across LanceDB dense vectors and BM25 sparse index."""
        dense_results: pd.DataFrame = pd.DataFrame()
        emb: Optional[List[float]] = None
        if self._db is not None:
            try:
                emb = await self.get_embedding(query)
                table = self._db.open_table("default-text_unit-text")
                dense_results = table.search(emb).limit(top_k).to_pandas()
            except Exception:
                dense_results = pd.DataFrame()

        # Sparse BM25 search on text units
        if self._tu_bm25 is None and self._text_units is not None and not self._text_units.empty:
            self._tu_bm25 = BM25Index.from_dataframe(self._text_units, text_col="text", id_col="id")

        sparse_results = self._tu_bm25.search_df(query, top_k=top_k) if self._tu_bm25 is not None else pd.DataFrame()

        # Fuse dense and sparse rankings via Reciprocal Rank Fusion (RRF)
        dense_ids = dense_results["id"].tolist() if not dense_results.empty and "id" in dense_results.columns else []
        sparse_ids = sparse_results["id"].tolist() if not sparse_results.empty and "id" in sparse_results.columns else []

        if dense_ids and sparse_ids:
            fused = reciprocal_rank_fusion([dense_ids, sparse_ids], k=60)
            fused_ids = [item_id for item_id, _ in fused][:top_k]
            tu_map = {row["id"]: row for _, row in self._text_units.iterrows()} if self._text_units is not None else {}
            results = pd.DataFrame([tu_map[tid] for tid in fused_ids if tid in tu_map])
        elif not dense_results.empty:
            results = dense_results
        elif not sparse_results.empty:
            results = sparse_results
        elif self._text_units is not None:
            results = self._keyword_search(self._text_units, "text", query, top_k)
        else:
            results = pd.DataFrame()

        if results.empty or self._entities is None or self._relationships is None:
            return {
                "text_units": results,
                "entities": pd.DataFrame(),
                "relationships": pd.DataFrame(),
            }

        text_unit_ids: List[Any] = results["id"].tolist() if "id" in results.columns else []

        # Direct Entity Vector Search across LanceDB tables (if embedded)
        direct_ent_ids: Set[str] = set()
        if self._db is not None and "emb" in locals() and emb is not None:
            for ent_table_name in ["default-entity-description", "default-entity-title"]:
                try:
                    e_table = self._db.open_table(ent_table_name)
                    e_vec_res = e_table.search(emb).limit(top_k // 2).to_pandas()
                    if "id" in e_vec_res.columns:
                        direct_ent_ids.update(e_vec_res["id"].tolist())
                except Exception:
                    pass

        # Entities that authored these units OR directly matched via entity vectors
        mask = self._entities["text_unit_ids"].apply(
            lambda arr: any(_tid_match(tid, arr) for tid in text_unit_ids)
        )
        if direct_ent_ids and "id" in self._entities.columns:
            mask = mask | self._entities["id"].isin(direct_ent_ids)

        relevant_ents = self._entities[mask]
        ent_ids = relevant_ents["id"].tolist()

        # Relationships involving those entities
        rel_mask = (
            self._relationships["source"].isin(ent_ids)
            | self._relationships["target"].isin(ent_ids)
        )
        relevant_rels = self._relationships[rel_mask]

        return {
            "text_units": results,
            "entities": relevant_ents,
            "relationships": relevant_rels,
        }

    # ── global mode: community reports ranked by hybrid semantic + BM25 similarity ─────

    async def _global_retrieval(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        dense_results: pd.DataFrame = pd.DataFrame()
        if self._db is not None:
            try:
                table = self._db.open_table("default-community-full_content")
                emb = await self.get_embedding(query)
                dense_results = table.search(emb).limit(top_k).to_pandas()
            except Exception:
                dense_results = pd.DataFrame()

        if self._comm_bm25 is None and self._communities is not None and not self._communities.empty:
            self._comm_bm25 = BM25Index.from_dataframe(self._communities, text_col="full_content", id_col="id")

        sparse_results = self._comm_bm25.search_df(query, top_k=top_k) if self._comm_bm25 is not None else pd.DataFrame()

        dense_ids = dense_results["id"].tolist() if not dense_results.empty and "id" in dense_results.columns else []
        sparse_ids = sparse_results["id"].tolist() if not sparse_results.empty and "id" in sparse_results.columns else []

        if dense_ids and sparse_ids:
            fused = reciprocal_rank_fusion([dense_ids, sparse_ids], k=60)
            fused_ids = [item_id for item_id, _ in fused][:top_k]
            comm_map = {row["id"]: row for _, row in self._communities.iterrows()} if self._communities is not None else {}
            results = pd.DataFrame([comm_map[cid] for cid in fused_ids if cid in comm_map])
        elif not dense_results.empty:
            results = dense_results
        elif not sparse_results.empty:
            results = sparse_results
        elif self._communities is not None:
            results = self._keyword_search(self._communities, "full_content", query, top_k)
        else:
            results = pd.DataFrame()

        return {"communities": results}

    # ── drift mode: multi-hop entity expansion over relationships ─────────

    async def _drift_retrieval(self, query: str, top_k: int = 10, min_edge_weight: float = 0.5) -> Dict[str, Any]:
        base = await self._local_retrieval(query, top_k=top_k)

        if base["entities"].empty or self._relationships is None or self._relationships.empty:
            return base

        seed_ents = base["entities"].head(5)
        seen_ids: set = set(seed_ents["id"])

        expanded: List[Dict[str, Any]] = []
        for _, row in seed_ents.iterrows():
            eid = row["id"]
            connected = self._relationships[
                (self._relationships["source"] == eid)
                | (self._relationships["target"] == eid)
            ]
            if "weight" in connected.columns:
                connected = connected[connected["weight"] >= min_edge_weight].sort_values("weight", ascending=False)
            connected = connected.head(3)

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
            # Show all retrieved text units without truncation (dataset is small: ~26 total, ~12k chars total)
            for _, tu in tUs.iterrows():
                txt = str(tu.get("text", "")).strip()
                if txt:
                    parts.append(f"- {txt}")

        ents = context.get("entities")
        if ents is not None and not ents.empty:
            parts.append("\n## Key Entities")
            for _, e in ents.head(10).iterrows():
                name = e.get("title", "") or e.get("name", "") or e.get("id", "")
                desc = str(e.get("description", ""))[:150]
                if name or desc:
                    parts.append(f"- **{name}** ({e.get('type', '')}): {desc}")

        rels = context.get("relationships")
        if rels is not None and not rels.empty:
            parts.append("\n## Knowledge Graph Triples")
            # Group by source entity for clear relational hierarchy
            grouped_rels: Dict[str, List[str]] = {}
            for _, r in rels.head(12).iterrows():
                src = str(r.get("source", "")).strip()[:50]
                tgt = str(r.get("target", "")).strip()[:50]
                desc = str(r.get("description", "")).strip()[:150]
                if not src or not tgt:
                    continue
                triple_str = f"  * --[{desc}]--> **{tgt}**" if desc else f"  * --> **{tgt}**"
                if src not in grouped_rels:
                    grouped_rels[src] = []
                grouped_rels[src].append(triple_str)

            for src_entity, target_triples in grouped_rels.items():
                parts.append(f"- **{src_entity}**:")
                for t in target_triples:
                    parts.append(t)

        comms = context.get("communities")
        if comms is not None and not comms.empty:
            parts.append("\n## Community Reports")
            for _, c in comms.head(5).iterrows():
                title = c.get("title", "") or c.get("id", "")
                content = str(c.get("full_content", ""))[:600]
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
            from src.gateway import (
                call_serverless_llm_stream,
            )

            async for token in call_serverless_llm_stream(
                system_prompt=sys_prompt,
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

        except Exception as e:
            import logging
            logging.getLogger(__name__).exception("LLM streaming failed")
            sources = self.extract_sources(context)
            ctx_str = self.format_context(context)
            answer = (
                f"Retrieved GraphRAG context.\n\nContext:\n{ctx_str}\n\n"
                f"*Answer:* (LLM streaming unavailable — {type(e).__name__})"
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
                "Use ALL the provided context comprehensively. When asked about companies, skills, or experiences, "
                "list ALL relevant items from the context, not just a few examples. Be specific with dates, metrics, and technologies. "
                "Only use information explicitly stated in the context—do not infer or add information not present."
            ),
            "global": (
                "You are a career analyst providing executive-level summaries of Prasad Rane's professional trajectory. "
                "Use ALL the provided community reports comprehensively to give high-level insights. "
                "Cover the full scope of experience mentioned in the context."
            ),
            "drift": (
                "You are a career researcher performing multi-hop analysis of Prasad Rane's professional experience. "
                "Connect information across ALL provided entities and relationships to provide comprehensive answers. "
                "Ensure your answer covers all relevant connections found in the context."
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
            new_engine = GraphRAGEngine(str(rd))
            await new_engine.connect()  # Raises if artifacts missing
            _engine = new_engine  # Only cache on success
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
