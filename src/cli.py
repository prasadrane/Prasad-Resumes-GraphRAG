"""
cli.py — Unified Command Line Interface for Prasad Resumes GraphRAG.
"""

import argparse
import os
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

def get_default_source_dir() -> Path:
    """Resolve default source directory from environment variable or relative path."""
    env_dir = os.getenv("SOURCE_RESUMES_DIR")
    if env_dir:
        return Path(env_dir)
    default_rel = ROOT_DIR.parent / "Prasad-Resumes"
    if default_rel.exists():
        return default_rel
    return Path(r"C:\Users\mamat\Github\Prasad-Resumes")

def build_parser() -> argparse.ArgumentParser:
    """Construct CLI argument parser."""
    parser = argparse.ArgumentParser(description="Prasad Resumes GraphRAG CLI Engine")
    subparsers = parser.add_subparsers(dest="command", help="Sub-command help")

    # Convert sub-command
    convert_parser = subparsers.add_parser("convert", help="Convert source documents to GraphRAG input text format")
    convert_parser.add_argument(
        "--source",
        type=str,
        default=str(get_default_source_dir()),
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
    generate_parser.add_argument("--company", type=str, required=True, help="Target company name")
    generate_parser.add_argument("--jd-file", type=str, help="Optional path to Job Description text file")

    # Query sub-command
    query_parser = subparsers.add_parser("query", help="Query the GraphRAG knowledge graph")
    query_parser.add_argument("--mode", choices=["local", "global"], default="local", help="Query mode (local or global)")
    query_parser.add_argument("query_string", type=str, help="Search query string")

    return parser

def main():
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
        jd_text = ""
        if args.jd_file:
            jd_path = Path(args.jd_file)
            if not jd_path.exists():
                print(f"[CLI ERROR] Job Description file not found: {jd_path}")
                sys.exit(1)
            jd_text = jd_path.read_text(encoding="utf-8")
        else:
            print(f"[CLI] Please paste the Job Description for {args.company} (Press Ctrl+D or Ctrl+Z then Enter to finish):")
            try:
                jd_text = sys.stdin.read()
            except (KeyboardInterrupt, EOFError):
                print("\nCancelled.")
                sys.exit(0)

        if not jd_text.strip():
            print("[CLI ERROR] Job Description cannot be empty.")
            sys.exit(1)

        print(f"[CLI] Performing ATS keyword extraction & generating tailored raw_resume.txt for {args.company}...")
        raw_resume_path = generate_raw_resume(args.company, jd_text)
        print(f"[CLI SUCCESS] Created: {raw_resume_path}")

        pdf_output_path = raw_resume_path.parent / "Prasad_Rane_Resume.pdf"
        print(f"[CLI] Rendering rule-based PDF resume (Prasad_Rane_Resume.pdf)...")
        render_pdf_resume(raw_resume_path, pdf_output_path)
        print(f"[CLI SUCCESS] Created: {pdf_output_path}")

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

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
