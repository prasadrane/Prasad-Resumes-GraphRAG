"""graph_controller.py — Read GraphRAG parquets and emit Cytoscape-ready JSON.

Caches the payload in memory, invalidated when any source parquet's mtime changes.
Used by GET /api/graph/explore to drive the Knowledge Graph Explorer UI tab.
"""
import ast
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from src.config import OUTPUT_DIR_PATH

logger = logging.getLogger(__name__)


ENTITIES_PATH = OUTPUT_DIR_PATH / "entities.parquet"
RELS_PATH = OUTPUT_DIR_PATH / "relationships.parquet"
COMMUNITIES_PATH = OUTPUT_DIR_PATH / "communities.parquet"
REPORTS_PATH = OUTPUT_DIR_PATH / "community_reports.parquet"

_PARQUET_PATHS = (ENTITIES_PATH, RELS_PATH, COMMUNITIES_PATH)


class GraphNotBuiltError(RuntimeError):
    """Raised when required parquet files are missing."""


_cache: Optional[Dict[str, Any]] = None
_cache_key: Optional[float] = None


def clear_graph_cache() -> None:
    """Clear in-memory cached payload. Used by tests and after re-index."""
    global _cache, _cache_key
    _cache = None
    _cache_key = None


def _check_parquets() -> None:
    missing = [str(p) for p in _PARQUET_PATHS if not p.exists()]
    if missing:
        raise GraphNotBuiltError(
            f"GraphRAG parquets missing: {missing}. Run `graphrag index --root .` to build."
        )


def _current_mtime_key() -> float:
    return max(p.stat().st_mtime for p in _PARQUET_PATHS)


def get_explorer_payload() -> Dict[str, Any]:
    """Return Cytoscape-ready JSON, rebuilding cache when parquets change."""
    global _cache, _cache_key
    _check_parquets()
    mtime = _current_mtime_key()
    if _cache is not None and _cache_key == mtime:
        return _cache

    entities = pd.read_parquet(ENTITIES_PATH)
    rels = pd.read_parquet(RELS_PATH)
    communities = pd.read_parquet(COMMUNITIES_PATH)
    reports = pd.read_parquet(REPORTS_PATH) if REPORTS_PATH.exists() else pd.DataFrame()

    payload = _build_payload(entities, rels, communities, reports)
    _cache, _cache_key = payload, mtime
    return payload


def _coerce_entity_ids(value: Any) -> List[str]:
    """Coerce communities.entity_ids to a list of strings.

    Handles Python list, numpy array, pandas Series, or string repr of a list.
    """
    if value is None:
        return []
    # pandas may store the column as object-dtype numpy arrays
    if hasattr(value, "__iter__") and not isinstance(value, (str, bytes)):
        return [str(v) for v in value]
    if isinstance(value, str):
        try:
            parsed = ast.literal_eval(value)
            if isinstance(parsed, list):
                return [str(v) for v in parsed]
        except Exception:
            pass
    return []


def _build_payload(
    entities: pd.DataFrame,
    rels: pd.DataFrame,
    communities: pd.DataFrame,
    reports: pd.DataFrame,
) -> Dict[str, Any]:
    """Transform raw parquet DataFrames into Cytoscape elements."""
    # 1. Build entity_id -> community_id mapping from communities.entity_ids
    entity_to_community: Dict[str, str] = {}
    community_rows: List[Dict[str, Any]] = []
    for _, row in communities.iterrows():
        cid = f"c:{row['community']}"
        entity_ids = _coerce_entity_ids(row.get("entity_ids"))
        for eid in entity_ids:
            entity_to_community[eid] = cid

        summary = ""
        if not reports.empty:
            match = reports[reports["community"] == row["community"]]
            if not match.empty:
                full = str(match.iloc[0].get("full_content", "") or "")
                summary = full[:300].strip()

        community_rows.append({
            "id": cid,
            "kind": "community",
            "label": str(row.get("title") or f"Community {row['community']}"),
            "level": int(row.get("level", 0) or 0),
            "rank": float(row.get("size", 0) or 0),
            "member_count": len(entity_ids),
            "summary": summary,
        })

    # 2. Build entity nodes, parented to community
    entity_nodes: List[Dict[str, Any]] = []
    for _, row in entities.iterrows():
        raw_id = str(row.get("id") or row.get("human_readable_id"))
        parent = entity_to_community.get(raw_id)
        ent_type = str(row.get("type") or "").strip() or "ENTITY"
        entity_nodes.append({
            "id": f"e:{raw_id}",
            "kind": "entity",
            "entity_type": ent_type,
            "label": str(row.get("title") or raw_id),
            "description": str(row.get("description") or ""),
            "degree": int(row.get("degree", 0) or 0),
            "frequency": int(row.get("frequency", 0) or 0),
            "parent": parent,
            "x": float(row.get("x", 0) or 0),
            "y": float(row.get("y", 0) or 0),
        })

    # 3. Build edges from relationships
    edges: List[Dict[str, Any]] = []
    for _, row in rels.iterrows():
        src = row.get("source")
        tgt = row.get("target")
        if src is None or tgt is None:
            continue
        edges.append({
            "id": f"r:{row.get('id', len(edges))}",
            "source": f"e:{src}",
            "target": f"e:{tgt}",
            "label": str(row.get("description") or "")[:80],
            "weight": float(row.get("weight", 0.5) or 0.5),
        })

    # 4. Parent orphaned entities (no community) to a synthetic 'Unassigned' bucket
    orphan_parentless = [n for n in entity_nodes if n["parent"] is None]
    if orphan_parentless:
        logger.warning(
            "graph_controller: %d entities without community membership will be parented to a synthetic 'Unassigned' community",
            len(orphan_parentless),
        )
        synthetic_id = "c:__unassigned__"
        if synthetic_id not in {c["id"] for c in community_rows}:
            community_rows.append({
                "id": synthetic_id,
                "kind": "community",
                "label": "Unassigned",
                "level": 0,
                "rank": 0,
                "member_count": len(orphan_parentless),
                "summary": "Entities without community membership.",
            })
        for n in orphan_parentless:
            n["parent"] = synthetic_id

    return {
        "freshness": {
            "built_at": datetime.now(timezone.utc).isoformat(),
            "entity_count": len(entity_nodes),
            "relationship_count": len(edges),
            "community_count": len(community_rows),
        },
        "elements": {
            "nodes": [{"data": n} for n in community_rows + entity_nodes],
            "edges": [{"data": e} for e in edges],
        },
    }
