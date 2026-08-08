#!/usr/bin/env python3
"""
convert_inputs.py — Entrypoint wrapper for input conversion.
Imports modular implementation from src.converters.
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.cli import get_default_source_dir
from src.converters.input_converter import convert_documents

INPUT_DIR = ROOT_DIR / "input"

def main():
    parser = argparse.ArgumentParser(description="Convert PDFs and Markdown to .txt for GraphRAG indexing")
    parser.add_argument(
        "--source",
        type=str,
        default=str(get_default_source_dir()),
        help="Source directory containing PDFs and MD files",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing output files even if unchanged")
    args = parser.parse_args()

    source_dir = Path(args.source)
    print(f"\n=== Input Converter: {source_dir} -> {INPUT_DIR} ===\n")
    stats = convert_documents(source_dir, INPUT_DIR, force=args.force)
    print(f"\n=== Conversion Summary ===")
    print(f"    Processed OK: {stats['ok']} | Skipped: {stats['skip']} | Errors: {stats['error']}\n")

if __name__ == "__main__":
    main()
