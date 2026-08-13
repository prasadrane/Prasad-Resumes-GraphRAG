#!/usr/bin/env python
"""Post-process GraphRAG output parquet files with entity resolution.

Reads the raw entity and relationship tables from GraphRAG indexing output,
applies deduplication / merging via EntityResolver, and writes cleaned
parquet files alongside the originals.

Usage:
    python scripts/postprocess_graph.py
    python scripts/postprocess_graph.py --input-dir output
    python scripts/postprocess_graph.py --string-threshold 0.80 --semantic-threshold 0.75
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run entity resolution on GraphRAG output parquet files.",
    )
    parser.add_argument(
        "--input-dir",
        default="output",
        help="Directory containing GraphRAG parquet output (default: output)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for resolved parquet files (default: same as input)",
    )
    parser.add_argument(
        "--string-threshold",
        type=float,
        default=0.85,
        help="SequenceMatcher ratio threshold (default: 0.85)",
    )
    parser.add_argument(
        "--semantic-threshold",
        type=float,
        default=0.80,
        help="Semantic similarity threshold for TECHNOLOGY entities (default: 0.80)",
    )
    parser.add_argument(
        "--use-embeddings",
        action="store_true",
        default=False,
        help="Enable embedding-based semantic similarity (requires sentence_transformers)",
    )
    parser.add_argument(
        "--embedding-model",
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="sentence_transformers model name (default: all-MiniLM-L6-v2)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        default=False,
        help="Enable debug logging",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir or args.input_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── Load parquet files ────────────────────────────────────────────────
    try:
        import pandas as pd  # noqa: F811
    except ImportError:  # pragma: no cover
        logger.error("pandas is required. Install: pip install pandas pyarrow")
        sys.exit(1)

    entities_path = input_dir / "create_final_entities.parquet"
    relationships_path = input_dir / "create_final_relationships.parquet"

    if not entities_path.exists():
        logger.error("Entities parquet not found at %s", entities_path)
        sys.exit(1)
    if not relationships_path.exists():
        logger.warning("Relationships parquet not found at %s — resolving entities only", relationships_path)

    entities_df = pd.read_parquet(entities_path)
    logger.info("Loaded %d entities, %d columns: %s",
                len(entities_df), len(entities_df.columns), list(entities_df.columns))

    if not relationships_path.exists():
        relationships_df = None
    else:
        relationships_df = pd.read_parquet(relationships_path)
        logger.info("Loaded %d relationships", len(relationships_df))

    # ── Build resolver ────────────────────────────────────────────────────
    from src.postprocessing.entity_resolver import (
        create_entity_resolver_with_embeddings,
        EntityResolver,
    )

    if args.use_embeddings:
        resolver = create_entity_resolver_with_embeddings(
            model_name=args.embedding_model,
            string_threshold=args.string_threshold,
            semantic_threshold=args.semantic_threshold,
        )
        logger.info("EntityResolver created WITH embedding support (%s)", args.embedding_model)
    else:
        resolver = EntityResolver(
            string_threshold=args.string_threshold,
            semantic_threshold=args.semantic_threshold,
        )
        logger.info("EntityResolver created (string-only, threshold=%.2f)", args.string_threshold)

    # ── Resolve entities ──────────────────────────────────────────────────
    entity_records = entities_df.to_dict(orient="records")
    resolved_entities, merge_pairs = resolver.resolve(entity_records)

    logger.info("Merged %d entity pairs → %d/%d remaining",
                len(merge_pairs), len(resolved_entities), len(entities_df))

    resolved_df = pd.DataFrame(resolved_entities)
    resolved_path = output_dir / "create_final_entities_resolved.parquet"
    resolved_df.to_parquet(resolved_path, index=False)
    logger.info("Resolved entities written to %s (%d rows)", resolved_path, len(resolved_df))

    # Print sample merges
    if merge_pairs:
        logger.info("Sample merges (first 10):")
        for pair in merge_pairs[:10]:
            logger.info(
                "  [%s] %r → %r  (str=%.3f, sem=%s)",
                pair.type_, pair.merged_into, pair.canonical,
                pair.string_score, pair.semantic_score,
            )

    # ── Update relationships ──────────────────────────────────────────────
    relabeled_count = 0
    if relationships_df is not None:
        rel_records = relationships_df.to_dict(orient="records")
        updated_rels, relabels = resolver.update_relationships(rel_records)
        relabeled_count = len(relabels)

        updated_rel_df = pd.DataFrame(updated_rels)
        rel_resolved_path = output_dir / "create_final_relationships_resolved.parquet"
        updated_rel_df.to_parquet(rel_resolved_path, index=False)
        logger.info(
            "Updated %d of %d relationships → %s",
            relabeled_count, len(updated_rels), rel_resolved_path,
        )

    # ── Summary ───────────────────────────────────────────────────────────
    print("\n=== Entity Resolution Summary ===")
    print(f"Original entities : {len(entities_df)}")
    print(f"Merged duplicates : {len(merge_pairs)}")
    print(f"Resolved entities : {len(resolved_df)}")
    print(f"Reduction         : {(1 - len(resolved_df) / len(entities_df)) * 100:.1f}%")
    if relationships_df is not None:
        print(f"Relationships     : {len(relationships_df)}")
        print(f"Relabeled refs    : {relabeled_count}")
    print("=================================\n")


if __name__ == "__main__":
    main()
