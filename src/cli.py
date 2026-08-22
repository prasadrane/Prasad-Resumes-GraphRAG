"""
cli.py — Unified Command Line Interface for Prasad Resumes GraphRAG.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.converters.input_converter import convert_documents
from src.query.search_engine import execute_graphrag_query
from src.proxy.litellm_runner import start_proxy_server, check_proxy_health
from src.generators.resume_generator import generate_raw_resume
from src.generators.pdf_renderer import render_pdf_resume
from src.generators.cover_letter_generator import CoverLetterGenerator
from src.agents.orchestrator import AgenticPipelineOrchestrator

def build_parser() -> argparse.ArgumentParser:
    """Construct CLI argument parser."""
    parser = argparse.ArgumentParser(description="Prasad Resumes GraphRAG CLI Engine")
    subparsers = parser.add_subparsers(dest="command", help="Sub-command help")

    # Convert sub-command
    convert_parser = subparsers.add_parser("convert", help="Convert source documents to GraphRAG input text format")
    convert_parser.add_argument(
        "--source",
        type=str,
        required=True,
        help="Source directory containing PDFs and MD files",
    )
    convert_parser.add_argument("--force", action="store_true", help="Overwrite existing output files")

    # Index sub-command
    index_parser = subparsers.add_parser("index", help="Build or update the GraphRAG knowledge graph index")
    index_parser.add_argument("--root", type=str, default=str(ROOT_DIR), help="Root directory for GraphRAG index")

    # Proxy sub-command
    proxy_parser = subparsers.add_parser("proxy", help="Launch the LiteLLM proxy server")
    proxy_parser.add_argument("--port", type=int, default=8002, help="Port to run LiteLLM proxy on")
    proxy_parser.add_argument("--config", type=str, default=str(ROOT_DIR / "config" / "litellm-config.yaml"), help="Path to LiteLLM config file")

    # Generate sub-command
    generate_parser = subparsers.add_parser("generate", help="Generate tailored resume text and rule-based PDF from Job Description")
    generate_parser.add_argument("--company", type=str, default="", help="Target company name (auto-inferred if --url is provided)")
    generate_parser.add_argument("--jd-file", type=str, help="Optional path to Job Description text file")
    generate_parser.add_argument("--jd-url", type=str, help="Optional URL to automatically scrape Job Description from")
    generate_parser.add_argument("--url", type=str, help="Alias for --jd-url")
    generate_parser.add_argument("--agentic", action="store_true", default=False, help="Enable autonomous Evaluator-Optimizer multi-subagent loop")
    generate_parser.add_argument("--min-score", type=float, default=90.0, help="Target ATS score threshold for agentic loop convergence")
    generate_parser.add_argument("--max-iterations", type=int, default=2, help="Maximum refinement iterations for agentic loop")

    # Cover Letter sub-command
    cover_parser = subparsers.add_parser("cover-letter", help="Generate a tailored cover letter from Job Description")
    cover_parser.add_argument("--company", type=str, default="", help="Target company name")
    cover_parser.add_argument("--role", type=str, default="Senior Software Engineer", help="Target role title (default: Senior Software Engineer)")
    cover_parser.add_argument("--jd-file", type=str, help="Path to Job Description text file")
    cover_parser.add_argument("--jd-url", type=str, help="URL to scrape Job Description from")
    cover_parser.add_argument("--url", type=str, help="Alias for --jd-url")
    cover_parser.add_argument("--output", type=str, help="Output file path (default: stdout)")

    # Query sub-command
    query_parser = subparsers.add_parser("query", help="Query the GraphRAG knowledge graph")
    query_parser.add_argument("--mode", choices=["local", "global"], default="local", help="Query mode (local or global)")
    query_parser.add_argument("query_string", type=str, help="Search query string")

    # Benchmark sub-command
    bench_parser = subparsers.add_parser("benchmark", help="Run synthetic evaluation benchmarks across GraphRAG retrieval modes")
    bench_parser.add_argument("--output", type=str, default=str(ROOT_DIR / "output" / "benchmark_report.md"), help="Path to save markdown benchmark report")
    bench_parser.add_argument("--mode", choices=["local", "drift", "global", "all"], default="all", help="Retrieval mode to evaluate")

    # UI sub-command
    subparsers.add_parser("ui", help="Launch the Web UI server via vercel dev")

    return parser

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "convert":
        source_path = Path(args.source)
        target_path = ROOT_DIR / "input"
        print(f"[CLI] Converting documents from {source_path} to {target_path}...")
        stats = convert_documents(source_path, target_path, force=args.force)
        print(f"[CLI] Conversion complete: {stats}")

    elif args.command == "index":
        root_path = Path(args.root)
        if not check_proxy_health(port=8002):
            print("[WARN] LiteLLM Proxy is not running on http://localhost:8002. Indexing might fail if proxy is required.")
        print(f"[CLI] Starting GraphRAG indexing with root: {root_path}...")
        cmd = [sys.executable, "-m", "graphrag", "index", "--root", str(root_path)]
        res = subprocess.run(cmd, cwd=str(root_path))
        if res.returncode != 0:
            print(f"[CLI ERROR] GraphRAG index failed with code {res.returncode}")
            sys.exit(res.returncode)

    elif args.command == "proxy":
        config_path = Path(args.config)
        print(f"[CLI] Starting LiteLLM proxy server on port {args.port} using {config_path}...")
        start_proxy_server(config_path, port=args.port)

    elif args.command == "generate":
        company = args.company
        target_url = args.url or args.jd_url
        jd_text = ""

        if args.agentic:
            print(f"[CLI AGENTIC] Initializing Multi-Subagent Evaluator-Optimizer Engine...")
            if target_url:
                print(f"[CLI AGENTIC] Target Job URL: {target_url}")
            elif args.jd_file:
                jd_path = Path(args.jd_file)
                if not jd_path.exists():
                    print(f"[CLI ERROR] Job Description file not found: {jd_path}")
                    sys.exit(1)
                jd_text = jd_path.read_text(encoding="utf-8")
            else:
                if not company:
                    print("[CLI ERROR] --company name or --url is required for agentic generation.")
                    sys.exit(1)
                print(f"[CLI] Please paste Job Description for {company} (Press Ctrl+D or Ctrl+Z then Enter to finish):")
                try:
                    jd_text = sys.stdin.read()
                except (KeyboardInterrupt, EOFError):
                    print("\nCancelled.")
                    sys.exit(0)

            orchestrator = AgenticPipelineOrchestrator()
            events = orchestrator.run(
                jd_text=jd_text,
                url=target_url,
                company_name=company,
                max_iterations=args.max_iterations,
                min_score=args.min_score,
            )

            for event in events:
                if event.step == "ingestion":
                    print(f"[*] [{event.agent}] {event.status}")
                elif event.step == "ingestion_complete":
                    posting = event.payload.get("posting", {})
                    print(f"[+] [{event.agent}] Company: {posting.get('company')} | Role: {posting.get('role_title')}")
                elif event.step == "critic_eval":
                    print(f"[EVAL] [{event.agent}] Baseline ATS Score: {event.payload.get('score')}%")
                elif event.step == "graph_retrieval":
                    print(f"[SEARCH] [{event.agent}] {event.status}")
                elif event.step == "optimization":
                    print(f"[OPT] [{event.agent}] {event.status}")
                elif event.step == "iteration_complete":
                    print(f"[SCORE] [{event.agent}] Iteration {event.payload.get('iteration')} Score: {event.payload.get('score')}% (+{event.payload.get('score_delta')}%)")
                    for diff in event.payload.get("diffs", []):
                        print(f"   * [{diff.get('role_title')}] {diff.get('refined_bullet')[:90]}...")
                elif event.step == "rendering":
                    print(f"[RENDER] [{event.agent}] {event.status}")
                elif event.step == "complete":
                    print("\n" + "=" * 60)
                    print(f"[SUCCESS] Tailored Resume Successfully Generated!")
                    print(f"   Company:    {event.payload.get('company')}")
                    print(f"   Role:       {event.payload.get('role_title')}")
                    print(f"   Final ATS:  {event.payload.get('final_score')}%")
                    print(f"   PDF Output: {event.payload.get('pdf_path')}")
                    print("=" * 60 + "\n")
            return

        if target_url:
            from src.converters.jd_extractor import extract_jd_from_url
            print(f"[CLI] Scraping and extracting Job Description from {target_url}...")
            try:
                extracted = extract_jd_from_url(target_url)
                jd_text = extracted["jd_text"]
                if not company:
                    company = extracted["company"]
                print(f"[CLI] Extracted role: '{extracted['title']}' at '{company}'")
            except Exception as e:
                print(f"[CLI ERROR] Failed to fetch Job Description from URL: {e}")
                sys.exit(1)
        elif args.jd_file:
            jd_path = Path(args.jd_file)
            if not jd_path.exists():
                print(f"[CLI ERROR] Job Description file not found: {jd_path}")
                sys.exit(1)
            jd_text = jd_path.read_text(encoding="utf-8")
        else:
            if not company:
                print("[CLI ERROR] --company name is required when not using --url.")
                sys.exit(1)
            print(f"[CLI] Please paste the Job Description for {company} (Press Ctrl+D or Ctrl+Z then Enter to finish):")
            try:
                jd_text = sys.stdin.read()
            except (KeyboardInterrupt, EOFError):
                print("\nCancelled.")
                sys.exit(0)

        if not company:
            company = "Target Company"

        if not jd_text.strip():
            print("[CLI ERROR] Job Description cannot be empty.")
            sys.exit(1)

        print(f"[CLI] Performing ATS keyword extraction & generating tailored raw_resume.txt for {company}...")
        raw_resume_path = generate_raw_resume(company, jd_text)
        print(f"[CLI SUCCESS] Created: {raw_resume_path}")

        pdf_output_path = raw_resume_path.parent / "Prasad_Rane_Resume.pdf"
        print(f"[CLI] Rendering rule-based PDF resume (Prasad_Rane_Resume.pdf)...")
        render_pdf_resume(raw_resume_path, pdf_output_path)
        print(f"[CLI SUCCESS] Created: {pdf_output_path}")

        # Real-time ATS match scoring
        if raw_resume_path.exists():
            from src.generators.ats_scorer import calculate_ats_score
            report = calculate_ats_score(raw_resume_path.read_text(encoding="utf-8"), jd_text)
            print("\n" + "=" * 60)
            print(f"[SCORE] ATS Match Score: {report.overall_score}%")
            print(f"   - Skills Coverage:       {report.section_scores.skills}%")
            print(f"   - Experience Coverage:   {report.section_scores.experience}%")
            print(f"   - Metric Quantification: {report.section_scores.quantification}%")
            if report.suggestions:
                print("Suggestions:")
                for s in report.suggestions:
                    print(f"   • {s}")
            print("=" * 60 + "\n")

    elif args.command == "cover-letter":
        company = args.company
        target_url = args.url or args.jd_url
        jd_text = ""

        if target_url:
            from src.converters.jd_extractor import extract_jd_from_url
            print(f"[CLI] Scraping Job Description from {target_url}...")
            try:
                extracted = extract_jd_from_url(target_url)
                jd_text = extracted["jd_text"]
                if not company:
                    company = extracted["company"]
                print(f"[CLI] Extracted role: '{extracted['title']}' at '{company}'")
            except Exception as e:
                print(f"[CLI ERROR] Failed to fetch Job Description from URL: {e}")
                sys.exit(1)
        elif args.jd_file:
            jd_path = Path(args.jd_file)
            if not jd_path.exists():
                print(f"[CLI ERROR] Job Description file not found: {jd_path}")
                sys.exit(1)
            jd_text = jd_path.read_text(encoding="utf-8")
        else:
            if not company:
                print("[CLI ERROR] --company or --jd-url is required.")
                sys.exit(1)
            print(f"[CLI] Please paste the Job Description for {company} (Ctrl+D / Ctrl+Z then Enter to finish):")
            try:
                jd_text = sys.stdin.read()
            except (KeyboardInterrupt, EOFError):
                print("\nCancelled.")
                sys.exit(0)

        if not company:
            company = "Target Company"

        if not jd_text.strip():
            print("[CLI ERROR] Job Description cannot be empty.")
            sys.exit(1)

        print(f"[CLI] Generating tailored cover letter for {company}...")
        generator = CoverLetterGenerator()
        data = generator.generate(company=company, jd_text=jd_text, role_title=args.role)
        md = generator.render_markdown(data)

        # Determine output directory (date-stamped, same as resume)
        if args.output:
            out_path = Path(args.output)
            if out_path.suffix.lower() == ".pdf":
                pdf_path = out_path
                md_path = out_path.with_suffix(".txt")
            else:
                md_path = out_path
                pdf_path = out_path.with_suffix(".pdf")
            out_dir = out_path.parent
        else:
            from src.generators.resume_generator import get_output_dir
            out_dir = get_output_dir(company)
            md_path = out_dir / "cover_letter.txt"
            pdf_path = out_dir / "cover_letter.pdf"

        out_dir.mkdir(parents=True, exist_ok=True)

        # Write text
        md_path.write_text(md, encoding="utf-8")
        print(f"[CLI SUCCESS] Cover letter (text) saved to: {md_path}")

        # Render PDF
        generator.render_pdf(data, pdf_path)
        print(f"[CLI SUCCESS] Cover letter (PDF) saved to: {pdf_path}")

    elif args.command == "query":
        if not check_proxy_health(port=8002):
            print("[WARN] LiteLLM Proxy does not appear to be active on http://localhost:8002.")
        print(f"[{args.mode.upper()} SEARCH] {args.query_string}\n" + "-" * 60)
        try:
            result = execute_graphrag_query(args.query_string, args.mode, root_dir=ROOT_DIR)
            print(result)
        except Exception as e:
            print(f"[CLI ERROR] Query failed: {e}")
            sys.exit(1)

    elif args.command == "benchmark":
        from scripts.benchmark_eval import run_benchmark
        run_benchmark(output_path=Path(args.output), mode=args.mode)

    elif args.command == "ui":
        import importlib.util

        # Try vercel dev first, fall back to uvicorn
        vercel_available = False
        try:
            res = subprocess.run(
                ["vercel", "--version"],
                capture_output=True,
                cwd=str(ROOT_DIR),
            )
            if res.returncode == 0:
                vercel_available = True
        except FileNotFoundError:
            pass

        if vercel_available:
            print("[CLI] Starting Web UI via vercel dev...")
            res = subprocess.run(["vercel", "dev"], cwd=str(ROOT_DIR))
            if res.returncode != 0:
                print(f"[CLI ERROR] vercel dev exited with code {res.returncode}")
                sys.exit(res.returncode)
        else:
            # Fallback: start uvicorn directly
            spec = importlib.util.find_spec("uvicorn")
            if spec is None:
                print("[CLI ERROR] vercel CLI not found and uvicorn not installed.")
                print("       Install uvicorn: pip install uvicorn[standard]")
                print("       Or install vercel CLI: npm i -g vercel")
                sys.exit(1)
            print("[CLI] Starting Web UI via uvicorn (port 3000)...")
            res = subprocess.run(
                [
                    sys.executable, "-m", "uvicorn",
                    "src.web.app:app", "--host", "0.0.0.0", "--port", "3000"
                ],
                cwd=str(ROOT_DIR),
            )
            if res.returncode != 0:
                print(f"[CLI ERROR] uvicorn exited with code {res.returncode}")
                sys.exit(res.returncode)

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
