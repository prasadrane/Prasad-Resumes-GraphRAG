"""
scripts/benchmark_eval.py — Automated Synthetic Evaluation Harness runner.

Usage:
    python scripts/benchmark_eval.py [--output output/benchmark_report.md] [--mode all]
"""

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.observability.benchmark_eval import BenchmarkEvaluator, DEFAULT_BENCHMARK_DATASET
from src.query.search_engine import execute_graphrag_query


def run_benchmark(output_path: Path, mode: str = "all") -> None:
    print("=" * 80)
    print("GraphRAG Synthetic Evaluation Harness")
    print(f"Dataset Size: {len(DEFAULT_BENCHMARK_DATASET)} query cases")
    print(f"Target Mode:  {mode}")
    print("=" * 80)

    evaluator = BenchmarkEvaluator()

    # Define engine wrapper using search_engine
    def engine_fn(query: str, retrieval_mode: str = "local") -> str:
        try:
            return execute_graphrag_query(query, mode=retrieval_mode, root_dir=ROOT_DIR)
        except Exception as e:
            return f"[Error]: {e}"

    modes_to_eval = ["local", "drift", "global"] if mode == "all" else [mode]
    reports = []

    for m in modes_to_eval:
        print(f"\n[Evaluating Mode: {m.upper()}] ...")
        report = evaluator.evaluate_dataset(
            dataset=DEFAULT_BENCHMARK_DATASET,
            engine=engine_fn,
            enable_guardrail=True,
        )
        reports.append(report)
        print(f"  • Mean Context Precision: {report.mean_precision:.2%}")
        print(f"  • Mean Context Recall:    {report.mean_recall:.2%}")
        print(f"  • Mean Faithfulness:       {report.mean_faithfulness:.2%}")
        print(f"  • Mean Query Latency:      {report.mean_latency_ms:.1f} ms")

    # Combine into unified markdown report
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    md_content = ["# GraphRAG Evaluation Benchmark Report\n", f"Generated automatically across {len(DEFAULT_BENCHMARK_DATASET)} synthetic test cases.\n\n"]
    for rep in reports:
        md_content.append(rep.to_markdown_table())
        md_content.append("\n---\n\n")

    full_md = "".join(md_content)
    output_path.write_text(full_md, encoding="utf-8")
    print(f"\n[SUCCESS] Benchmark report generated at: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="GraphRAG Synthetic Benchmark Runner")
    parser.add_argument(
        "--output",
        type=str,
        default=str(ROOT_DIR / "output" / "benchmark_report.md"),
        help="Output markdown report path",
    )
    parser.add_argument(
        "--mode",
        choices=["local", "drift", "global", "all"],
        default="all",
        help="Retrieval mode to evaluate",
    )
    args = parser.parse_args()
    run_benchmark(Path(args.output), mode=args.mode)


if __name__ == "__main__":
    main()
