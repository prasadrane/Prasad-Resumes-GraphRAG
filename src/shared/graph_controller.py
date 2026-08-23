"""graph_controller.py — Read GraphRAG parquets and emit Cytoscape-ready JSON.

Caches the payload in memory, invalidated when any source parquet's mtime changes.
Used by GET /api/graph/explore to drive the Knowledge Graph Explorer UI tab.
"""
import ast
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from src.config import OUTPUT_DIR_PATH, ROOT_DIR

logger = logging.getLogger(__name__)


# Resolve parquet locations. vercel.json sets OUTPUT_DIR=/tmp/output which
# `vercel dev` applies locally, but the actual parquets live at ROOT_DIR/output.
# Try the configured OUTPUT_DIR first, then fall back to ROOT_DIR/output.
def _resolve_parquet_paths() -> tuple:
    candidates = [OUTPUT_DIR_PATH]
    default_output = ROOT_DIR / "output"
    if default_output.resolve() != OUTPUT_DIR_PATH.resolve():
        candidates.append(default_output)
    for base in candidates:
        if (base / "entities.parquet").exists():
            return (
                base / "entities.parquet",
                base / "relationships.parquet",
                base / "communities.parquet",
                base / "community_reports.parquet",
            )
    # Default to configured OUTPUT_DIR_PATH (will surface GraphNotBuiltError)
    return (
        OUTPUT_DIR_PATH / "entities.parquet",
        OUTPUT_DIR_PATH / "relationships.parquet",
        OUTPUT_DIR_PATH / "communities.parquet",
        OUTPUT_DIR_PATH / "community_reports.parquet",
    )


ENTITIES_PATH, RELS_PATH, COMMUNITIES_PATH, REPORTS_PATH = _resolve_parquet_paths()

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

        # communities.parquet titles are placeholders ("Community N"); the
        # community reports carry the real names.
        summary = ""
        report_title = ""
        if not reports.empty:
            match = reports[reports["community"] == row["community"]]
            if not match.empty:
                report_title = str(match.iloc[0].get("title") or "").strip()
                full = str(match.iloc[0].get("full_content", "") or "")
                summary = full[:300].strip()
                if not report_title and full:
                    report_title = full.splitlines()[0].strip().lstrip("#").strip()

        community_rows.append({
            "id": cid,
            "kind": "community",
            "label": report_title or str(row.get("title") or f"Community {row['community']}"),
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
        # x/y may be NaN (no pre-computed layout) — coerce to 0 for JSON safety
        x_val = row.get("x", 0)
        y_val = row.get("y", 0)
        x = 0.0 if (x_val is None or pd.isna(x_val)) else float(x_val)
        y = 0.0 if (y_val is None or pd.isna(y_val)) else float(y_val)
        entity_nodes.append({
            "id": f"e:{raw_id}",
            "kind": "entity",
            "entity_type": ent_type,
            "label": str(row.get("title") or raw_id),
            "description": str(row.get("description") or ""),
            "degree": int(row.get("degree", 0) or 0),
            "frequency": int(row.get("frequency", 0) or 0),
            "parent": parent,
            "x": x,
            "y": y,
        })

    # 2b. Communities without a report keep placeholder titles; derive a
    # readable name from their highest-degree members instead.
    members_by_parent: Dict[str, List[Dict[str, Any]]] = {}
    for n in entity_nodes:
        members_by_parent.setdefault(n["parent"], []).append(n)
    for row in community_rows:
        if not re.match(r"^Community \d+$", row["label"]):
            continue
        tops = sorted(members_by_parent.get(row["id"], []),
                      key=lambda m: m["degree"], reverse=True)[:2]
        if tops:
            row["label"] = " · ".join(t["label"].title() for t in tops)

    # 3. Build edges from relationships (relationships use entity TITLES as source/target)
    title_to_id = {str(row.get("title")): f"e:{row.get('id')}" for _, row in entities.iterrows()
                   if row.get("title") is not None and row.get("id") is not None}
    edges: List[Dict[str, Any]] = []
    skipped_edges = 0
    for _, row in rels.iterrows():
        src_title = row.get("source")
        tgt_title = row.get("target")
        if src_title is None or tgt_title is None:
            continue
        src = title_to_id.get(str(src_title))
        tgt = title_to_id.get(str(tgt_title))
        if src is None or tgt is None:
            skipped_edges += 1
            continue
        edges.append({
            "id": f"r:{row.get('id', len(edges))}",
            "source": src,
            "target": tgt,
            "label": str(row.get("description") or "")[:80],
            "weight": float(row.get("weight", 0.5) or 0.5),
        })
    if skipped_edges:
        logger.warning("graph_controller: %d edges skipped (source/target not found in entities)", skipped_edges)

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


def get_fallback_explorer_payload() -> Dict[str, Any]:
    """Generate a rich, interactive fallback graph payload when GraphRAG parquets are not yet indexed."""
    communities = [
        {"id": "c:1", "kind": "community", "label": "Enterprise Modernization & FinTech", "level": 0, "rank": 4.0, "member_count": 4, "summary": "Cloud modernization, FinTech underwriting platforms, and microservices architecture."},
        {"id": "c:2", "kind": "community", "label": "Cloud Infrastructure & GenAI", "level": 0, "rank": 5.0, "member_count": 5, "summary": "AWS ECS Fargate, Amazon Bedrock (Claude Sonnet), Apache Kafka/MSK, and Terraform IaC."},
        {"id": "c:3", "kind": "community", "label": "SaaS & High-Scale Data", "level": 0, "rank": 4.0, "member_count": 4, "summary": "SQL Server query plan optimization, .NET Core 8/9, and single-table DynamoDB designs."},
        {"id": "c:4", "kind": "community", "label": "Systems Diagnostics & DevEx", "level": 0, "rank": 3.0, "member_count": 3, "summary": "WinDbg/dotnet-dump memory profiling, Docker Compose local DevEx, and low-level thread optimization."},
        {"id": "c:5", "kind": "community", "label": "Education & Credentials", "level": 0, "rank": 2.0, "member_count": 2, "summary": "University of Cincinnati MS IT and AWS Certified Cloud Practitioner."},
    ]

    entities = [
        {"id": "e:1", "kind": "entity", "entity_type": "ORGANIZATION", "label": "Rocket Mortgage", "description": "Enterprise mortgage lending platform (Jan 2023 – Jul 2025)", "degree": 5, "frequency": 12, "parent": "c:1", "x": 0.0, "y": 0.0},
        {"id": "e:2", "kind": "entity", "entity_type": "TECHNOLOGY", "label": "AWS ECS Fargate", "description": "Serverless container orchestration cutting costs by 40% with 99.95% uptime", "degree": 4, "frequency": 9, "parent": "c:2", "x": 0.0, "y": 0.0},
        {"id": "e:3", "kind": "entity", "entity_type": "TECHNOLOGY", "label": "Amazon Bedrock (GenAI)", "description": "Claude Sonnet AI loan lookup chatbot delivering 70% time reduction", "degree": 3, "frequency": 8, "parent": "c:2", "x": 0.0, "y": 0.0},
        {"id": "e:4", "kind": "entity", "entity_type": "TECHNOLOGY", "label": "Apache Kafka / MSK", "description": "Enterprise event streaming and governance standard adopted across 5 teams", "degree": 3, "frequency": 7, "parent": "c:2", "x": 0.0, "y": 0.0},
        {"id": "e:5", "kind": "entity", "entity_type": "TECHNOLOGY", "label": "Amazon DynamoDB", "description": "Single-table NoSQL design for sub-15 min self-service product configuration", "degree": 3, "frequency": 6, "parent": "c:2", "x": 0.0, "y": 0.0},
        {"id": "e:6", "kind": "entity", "entity_type": "TECHNOLOGY", "label": "Terraform IaC", "description": "Infrastructure as Code for automated multi-environment cloud provisioning", "degree": 2, "frequency": 5, "parent": "c:2", "x": 0.0, "y": 0.0},
        {"id": "e:7", "kind": "entity", "entity_type": "ORGANIZATION", "label": "London Computer Systems", "description": "Property management SaaS platform engineering (Dec 2019 – Jan 2023)", "degree": 4, "frequency": 10, "parent": "c:3", "x": 0.0, "y": 0.0},
        {"id": "e:8", "kind": "entity", "entity_type": "TECHNOLOGY", "label": "SQL Server Optimization", "description": "Refactored stored procedures & composite indexes (45s to <3s latency)", "degree": 3, "frequency": 6, "parent": "c:3", "x": 0.0, "y": 0.0},
        {"id": "e:9", "kind": "entity", "entity_type": "TECHNOLOGY", "label": ".NET Core / C#", "description": "Enterprise backend architecture, CQRS, and high-concurrency SemaphoreSlim profiling", "degree": 5, "frequency": 15, "parent": "c:3", "x": 0.0, "y": 0.0},
        {"id": "e:10", "kind": "entity", "entity_type": "TECHNOLOGY", "label": "Angular (12–18)", "description": "Modular SPA frontend engineering, RxJS reactive state, and TypeScript", "degree": 3, "frequency": 7, "parent": "c:3", "x": 0.0, "y": 0.0},
        {"id": "e:11", "kind": "entity", "entity_type": "ORGANIZATION", "label": "EXFO Electro-Optical", "description": "Telecom test instruments & offline REST sync layers (Mar 2015 – Jun 2018)", "degree": 3, "frequency": 6, "parent": "c:4", "x": 0.0, "y": 0.0},
        {"id": "e:12", "kind": "entity", "entity_type": "TECHNOLOGY", "label": "WinDbg & Diagnostics", "description": "CLR memory dump analysis and unmanaged handle leak resolution", "degree": 2, "frequency": 4, "parent": "c:4", "x": 0.0, "y": 0.0},
        {"id": "e:13", "kind": "entity", "entity_type": "ORGANIZATION", "label": "Tanish Infotech Solutions", "description": "Full-stack .NET and SQL custom business solutions (Mar 2014 – Feb 2015)", "degree": 2, "frequency": 4, "parent": "c:1", "x": 0.0, "y": 0.0},
        {"id": "e:14", "kind": "entity", "entity_type": "ORGANIZATION", "label": "University of Cincinnati", "description": "Master of Science in Information Technology (GPA 3.84/4.0)", "degree": 2, "frequency": 3, "parent": "c:5", "x": 0.0, "y": 0.0},
        {"id": "e:15", "kind": "entity", "entity_type": "CREDENTIAL", "label": "AWS Certified Cloud Practitioner", "description": "Official AWS Cloud Architecture Certification", "degree": 1, "frequency": 2, "parent": "c:5", "x": 0.0, "y": 0.0},
    ]

    edges = [
        {"id": "r:1", "source": "e:1", "target": "e:2", "label": "Migrated legacy monolith to ECS Fargate (40% cost reduction)", "weight": 0.95},
        {"id": "r:2", "source": "e:1", "target": "e:3", "label": "Built Claude Sonnet GenAI chatbot (70% lookup time savings)", "weight": 0.92},
        {"id": "r:3", "source": "e:1", "target": "e:4", "label": "Cross-team Kafka/MSK schema governance across 5 squads", "weight": 0.88},
        {"id": "r:4", "source": "e:1", "target": "e:5", "label": "Single-table DynamoDB architecture with shadow validation", "weight": 0.85},
        {"id": "r:5", "source": "e:1", "target": "e:6", "label": "Terraform IaC multi-environment deployment pipelines", "weight": 0.80},
        {"id": "r:6", "source": "e:7", "target": "e:8", "label": "SQL Server query plan tuning (slashed latency from 45s to <3s)", "weight": 0.90},
        {"id": "r:7", "source": "e:7", "target": "e:9", "label": "Engineered core .NET Core billing API and payment integrations", "weight": 0.88},
        {"id": "r:8", "source": "e:7", "target": "e:10", "label": "Architected Angular self-service customer portal", "weight": 0.82},
        {"id": "r:9", "source": "e:11", "target": "e:12", "label": "Diagnosed OS power event memory leaks via WinDbg & CLR dumps", "weight": 0.85},
        {"id": "r:10", "source": "e:11", "target": "e:9", "label": "Built offline-first REST API sync layer in C#", "weight": 0.80},
        {"id": "r:11", "source": "e:13", "target": "e:9", "label": "Delivered full-stack .NET and SQL custom business software", "weight": 0.75},
        {"id": "r:12", "source": "e:14", "target": "e:9", "label": "Master of Science in Information Technology (Enterprise Computing)", "weight": 0.70},
        {"id": "r:13", "source": "e:15", "target": "e:2", "label": "AWS Cloud Practitioner Certified Validation", "weight": 0.65},
    ]

    return {
        "freshness": {
            "built_at": datetime.now(timezone.utc).isoformat(),
            "entity_count": len(entities),
            "relationship_count": len(edges),
            "community_count": len(communities),
            "is_precomputed_fallback": True,
        },
        "elements": {
            "nodes": [{"data": n} for n in communities + entities],
            "edges": [{"data": e} for e in edges],
        },
    }
