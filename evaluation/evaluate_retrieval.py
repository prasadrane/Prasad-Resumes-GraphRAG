"""
Evaluation Script — Measure GraphRAG retrieval quality on a query dataset.

Loads queries from *evaluation/query_dataset.json*, runs each query through
both local and global modes, then calculates entity and keyword precision/recall.

Usage:
    python -m evaluation.evaluate_retrieval [--mode local|global|both] [--dataset <path>]
"""

from __future__ import annotations

import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Set

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
log = logging.getLogger(__name__)

EVAL_DIR = Path(__file__).resolve().parent  # evaluation/
DEFAULT_DATASET = EVAL_DIR / "query_dataset.json"


def _normalize(text: str) -> set[str]:
    """Lowercase, strip non-alpha, return token set."""
    tokens = re.findall(r"[a-z0-9#]+", text.lower())
    return set(tokens)


def _precision_recall(got: Set[str], expected: Set[str]) -> Dict[str, float]:
    """Compute precision and recall for entity/keyword matching."""
    if not got and not expected:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0}
    if not expected:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
    tp = len(got & expected)
    prec = tp / len(got) if got else 0.0
    rec = tp / len(expected) if expected else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
    return {"precision": round(prec, 4), "recall": round(rec, 4), "f1": round(f1, 4)}


def _run_query(query: str, mode: str) -> str:
    """Run a single query through GraphRAG. Returns raw response text."""
    try:
        from src.query.search_engine import execute_graphrag_query
        response = execute_graphrag_query(query, mode=mode)
        return response or ""
    except Exception as exc:
        log.warning("Query failed [%s] '%s': %s", mode, query, exc)
        return ""


def evaluate_query(
    item: Dict[str, Any],
    mode: str,
) -> Dict[str, object]:
    """Evaluate one query against its expected entities/keywords."""
    response = _run_query(item["query"], mode)
    response_tokens = _normalize(response)
    expected_entities = {re.sub(r"[^a-z0-9]", "", e).lower() for e in item.get("expected_entities", []) if e}
    expected_keywords = {re.sub(r"[^a-z0-9]", "", k).lower() for k in item.get("expected_keywords", []) if k}

    return {
        "id": item["id"],
        "query": item["query"],
        "category": item.get("category", ""),
        "mode": mode,
        "response_length": len(response),
        "entity_metrics": _precision_recall(response_tokens, expected_entities),
        "keyword_metrics": _precision_recall(response_tokens, expected_keywords),
        "matched_entities": sorted(response_tokens & expected_entities),
        "missing_entities": sorted(expected_entities - response_tokens),
        "found_at_least_one": bool(expected_entities & response_tokens),
    }


def run_evaluation(
    dataset_path: Path = DEFAULT_DATASET,
    mode: str = "both",
) -> Dict[str, Any]:
    """Run full evaluation over all queries, print summary."""
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    modes = [mode] if mode != "both" else ["local", "global"]

    all_results: List[Dict[str, object]] = []
    for item in dataset:
        for m in modes:
            result = evaluate_query(item, m)
            all_results.append(result)

    # Compute aggregate metrics per mode
    summaries: Dict[str, Dict[str, Any]] = {}
    for m in modes:
        mode_results = [r for r in all_results if r["mode"] == m]
        if not mode_results:
            continue

        n = len(mode_results)
        avg_prec_entity = sum(r["entity_metrics"]["precision"] for r in mode_results) / n
        avg_rec_entity = sum(r["entity_metrics"]["recall"] for r in mode_results) / n
        avg_f1_entity = sum(r["entity_metrics"]["f1"] for r in mode_results) / n
        avg_prec_keyword = sum(r["keyword_metrics"]["precision"] for r in mode_results) / n
        avg_rec_keyword = sum(r["keyword_metrics"]["recall"] for r in mode_results) / n
        avg_f1_keyword = sum(r["keyword_metrics"]["f1"] for r in mode_results) / n
        found_count = sum(1 for r in mode_results if r["found_at_least_one"])

        summaries[m] = {
            "total_queries": n,
            "entities": {
                "avg_precision": round(avg_prec_entity, 4),
                "avg_recall": round(avg_rec_entity, 4),
                "avg_f1": round(avg_f1_entity, 4),
                "queries_with_matches": found_count,
            },
            "keywords": {
                "avg_precision": round(avg_prec_keyword, 4),
                "avg_recall": round(avg_rec_keyword, 4),
                "avg_f1": round(avg_f1_keyword, 4),
            },
            "per_query": mode_results,
        }

    output = {
        "dataset": str(dataset_path.name),
        "total_queries": len(dataset),
        "modes_evaluated": modes,
        "summaries": summaries,
    }

    # Print summary
    for m, s in summaries.items():
        print(f"\n=== Mode: {m} ===")
        print(f"  Queries evaluated : {s['total_queries']}")
        print(f"  Entities F1       : {s['entities']['avg_f1']:.4f}  "
              f"(P={s['entities']['avg_precision']:.4f}, R={s['entities']['avg_recall']:.4f})")
        print(f"  Keywords F1       : {s['keywords']['avg_f1']:.4f}  "
              f"(P={s['keywords']['avg_precision']:.4f}, R={s['keywords']['avg_recall']:.4f})")
        print(f"  Found >=1 entity  : {s['entities']['queries_with_matches']}/{s['total_queries']}")

    return output


def main() -> None:
    """CLI entry point."""
    import argparse
    ap = argparse.ArgumentParser(description="Evaluate GraphRAG retrieval quality")
    ap.add_argument("--mode", choices=["local", "global", "both"], default="both")
    ap.add_argument("--dataset", type=str, default=str(DEFAULT_DATASET))
    args = ap.parse_args()

    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        log.error("Dataset not found: %s", dataset_path)
        sys.exit(1)

    run_evaluation(dataset_path, args.mode)


if __name__ == "__main__":
    main()
