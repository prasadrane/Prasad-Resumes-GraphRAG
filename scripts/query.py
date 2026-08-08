#!/usr/bin/env python3
"""
query.py — Entrypoint wrapper for querying the Prasad Resumes knowledge graph.
Imports modular implementation from src.query.
"""

import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

import argparse
from src.query.search_engine import execute_graphrag_query

EXAMPLES = """
Example queries:
  LOCAL:
    "What AWS technologies did Prasad use at Rocket Mortgage?"
    "Show all stories related to observability"

  GLOBAL:
    "What are the recurring themes across all resumes?"
    "What is Prasad's overall technical profile?"
"""

def run_query(query: str, mode: str):
    print(f"\n[{mode.upper()} SEARCH] {query}\n" + "-"*60)
    result = execute_graphrag_query(query, mode, root_dir=ROOT_DIR)
    print(result)

def interactive():
    print("\n" + "="*60)
    print("  Prasad Resumes — GraphRAG Knowledge Graph CLI Engine")
    print("="*60)
    print(EXAMPLES)
    print("Commands: 'local <q>', 'global <q>', 'quit'\n")
    while True:
        try:
            raw = input(">> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nBye!")
            break
        if not raw or raw.lower() in ("quit", "exit", "q"):
            break
        if raw.lower().startswith("local "):
            run_query(raw[6:].strip(), "local")
        elif raw.lower().startswith("global "):
            run_query(raw[7:].strip(), "global")
        else:
            run_query(raw, "local")

def main():
    parser = argparse.ArgumentParser(description="Query the Prasad Resumes GraphRAG knowledge graph")
    parser.add_argument("--local",  metavar="QUERY", help="Run a local search")
    parser.add_argument("--global", metavar="QUERY", dest="global_", help="Run a global search")
    args = parser.parse_args()

    if args.local:
        run_query(args.local, "local")
    elif args.global_:
        run_query(args.global_, "global")
    else:
        interactive()

if __name__ == "__main__":
    main()
