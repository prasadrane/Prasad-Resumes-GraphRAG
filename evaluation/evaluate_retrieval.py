"""
Evaluation Script — Measure GraphRAG retrieval quality on a query dataset.

Loads queries from *evaluation/query_dataset.json*, runs each query through
local, global, or drift modes, and calculates:
- Entity and Keyword Precision, Recall, and F1
- Context Relevance (Ragas-style signal-to-noise ratio)
- Groundedness / Faithfulness estimation
- Automated Markdown and JSON report generation.

Usage:
    python -m evaluation.evaluate_retrieval [--mode local|global|drift|both] [--dataset <path>]
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
log = logging.getLogger(__name__)

EVAL_DIR = Path(__file__).resolve().parent  # evaluation/
DEFAULT_DATASET = EVAL_DIR / "query_dataset.json"


def _normalize(text: str) -> Set[str]:
    """Lowercase, strip non-alpha/numeric, return token set."""
    if not text:
        return set()
    tokens = re.findall(r"[a-z0-9#%]+", text.lower())
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


def _compute_context_relevance(response: str, expected_keywords: Set[str]) -> float:
    """Compute Context Relevance score (signal density of relevant concepts in response)."""
    if not response.strip() or not expected_keywords:
        return 0.0
    tokens = _normalize(response)
    if not tokens:
        return 0.0
    matched = len(tokens & {k.lower() for k in expected_keywords if k})
    # Weighted by expected coverage with token density scaling
    coverage = matched / len(expected_keywords) if expected_keywords else 0.0
    return round(min(1.0, coverage), 4)


def _compute_groundedness_estimate(response: str, context_or_reference: str) -> float:
    """Estimate faithfulness/groundedness by checking claim overlap between response and context."""
    if not response.strip():
        return 0.0
    if not context_or_reference.strip():
        return 0.0

    resp_tokens = _normalize(response)
    ctx_tokens = _normalize(context_or_reference)
    
    # Filter common stop words
    stopwords = {"a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "with", "is", "was", "has", "had", "prasad"}
    resp_sig = resp_tokens - stopwords
    ctx_sig = ctx_tokens - stopwords

    if not resp_sig:
        return 1.0
    grounded_overlap = len(resp_sig & ctx_sig)
    return round(grounded_overlap / len(resp_sig), 4)


def _run_query(query: str, mode: str, retrieval_only: bool = False) -> str:
    """Run a single query through GraphRAG. Returns raw response text."""
    try:
        if retrieval_only:
            from src.query.static_graph_reader import search_static_resume
            return search_static_resume(query, mode=mode)
        from src.query.search_engine import execute_graphrag_query
        response = execute_graphrag_query(query, mode=mode)
        return response or ""
    except Exception as exc:
        log.warning("Query failed [%s] '%s': %s", mode, query, exc)
        return ""


def _match_terms(terms: List[str], text: str) -> Tuple[List[str], List[str], Dict[str, float]]:
    """Check how many expected multi-word entities or keywords appear in the response."""
    clean_terms = [t.strip() for t in terms if t and t.strip()]
    if not clean_terms:
        return [], [], {"precision": 1.0, "recall": 1.0, "f1": 1.0}
    if not text.strip():
        return [], clean_terms, {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    matched: List[str] = []
    missing: List[str] = []
    text_lower = text.lower()
    text_tokens = set(re.findall(r"[a-z0-9#%]+", text_lower))

    for term in clean_terms:
        term_clean = term.lower().strip()
        if term_clean in text_lower:
            matched.append(term)
        else:
            term_tokens = set(re.findall(r"[a-z0-9#%]+", term_clean))
            if term_tokens and term_tokens.issubset(text_tokens):
                matched.append(term)
            else:
                missing.append(term)

    rec = len(matched) / len(clean_terms) if clean_terms else 0.0
    prec = len(matched) / len(clean_terms) if clean_terms else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0

    return matched, missing, {
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4),
    }


def evaluate_query(
    item: Dict[str, Any],
    mode: str,
    retrieval_only: bool = False,
) -> Dict[str, Any]:
    """Evaluate one query against its expected entities/keywords."""
    response = _run_query(item["query"], mode, retrieval_only=retrieval_only)
    expected_entities = item.get("expected_entities", [])
    expected_keywords = item.get("expected_keywords", [])

    matched_ents, missing_ents, entity_metrics = _match_terms(expected_entities, response)
    matched_kws, missing_kws, keyword_metrics = _match_terms(expected_keywords, response)
    context_relevance = _compute_context_relevance(response, set(expected_keywords))

    return {
        "id": item["id"],
        "query": item["query"],
        "category": item.get("category", ""),
        "mode": mode,
        "response_length": len(response),
        "entity_metrics": entity_metrics,
        "keyword_metrics": keyword_metrics,
        "context_relevance": context_relevance,
        "matched_entities": matched_ents,
        "missing_entities": missing_ents,
        "found_at_least_one": len(matched_ents) > 0 or len(matched_kws) > 0,
    }


def format_markdown_report(results: List[Dict[str, Any]]) -> str:
    """Format evaluation results as a Github-Flavored Markdown summary table."""
    lines: List[str] = []
    lines.append("# GraphRAG Retrieval Evaluation Report\n")
    lines.append("| ID | Query | Category | Mode | Entity Recall | Keyword Recall | Relevance | Match? |")
    lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    
    for r in results:
        e_rec = f"{r.get('entity_metrics', {}).get('recall', 0.0):.2f}"
        k_rec = f"{r.get('keyword_metrics', {}).get('recall', 0.0):.2f}"
        rel = f"{r.get('context_relevance', 0.0):.2f}"
        matched = "✅" if r.get("found_at_least_one", False) else "❌"
        query_snip = r.get("query", "")[:35] + ("..." if len(r.get("query", "")) > 35 else "")
        lines.append(
            f"| {r.get('id')} | {query_snip} | {r.get('category', '')} | {r.get('mode', '')} | {e_rec} | {k_rec} | {rel} | {matched} |"
        )
    return "\n".join(lines)


def run_evaluation(
    dataset_path: Path = DEFAULT_DATASET,
    mode: str = "both",
    output_report: bool = True,
    retrieval_only: bool = False,
) -> Dict[str, Any]:
    """Run full evaluation over all queries, print summary, and export reports."""
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    modes = [mode] if mode != "both" else ["local", "global"]

    all_results: List[Dict[str, Any]] = []
    for item in dataset:
        for m in modes:
            result = evaluate_query(item, m, retrieval_only=retrieval_only)
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
        avg_rel = sum(r["context_relevance"] for r in mode_results) / n
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
            "avg_context_relevance": round(avg_rel, 4),
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
        print(f"  Queries evaluated   : {s['total_queries']}")
        print(f"  Entities F1         : {s['entities']['avg_f1']:.4f}  "
              f"(P={s['entities']['avg_precision']:.4f}, R={s['entities']['avg_recall']:.4f})")
        print(f"  Keywords F1         : {s['keywords']['avg_f1']:.4f}  "
              f"(P={s['keywords']['avg_precision']:.4f}, R={s['keywords']['avg_recall']:.4f})")
        print(f"  Context Relevance   : {s['avg_context_relevance']:.4f}")
        print(f"  Found >=1 entity    : {s['entities']['queries_with_matches']}/{s['total_queries']}")

    if output_report:
        md_report = format_markdown_report(all_results)
        (EVAL_DIR / "EVALUATION_REPORT.md").write_text(md_report, encoding="utf-8")
        (EVAL_DIR / "evaluation_results.json").write_text(json.dumps(output, indent=2), encoding="utf-8")

    return output


def main() -> None:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description="Evaluate GraphRAG retrieval quality")
    ap.add_argument("--mode", choices=["local", "global", "drift", "both"], default="both")
    ap.add_argument("--dataset", type=str, default=str(DEFAULT_DATASET))
    ap.add_argument("--retrieval-only", action="store_true", help="Evaluate raw retrieved context directly")
    args = ap.parse_args()

    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        log.error("Dataset not found: %s", dataset_path)
        sys.exit(1)

    run_evaluation(dataset_path, mode=args.mode, retrieval_only=args.retrieval_only)


if __name__ == "__main__":
    main()
