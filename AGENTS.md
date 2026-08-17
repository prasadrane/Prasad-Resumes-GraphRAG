# AI Agent Instructions for Prasad-Resumes-GraphRAG

## Purpose

This repository builds and queries a GraphRAG knowledge graph over Prasad Rane's resumes and story bank content, and generates rule-based, ATS-tailored raw text and PDF resumes.

## Key files & Indexing Assets

- `docs/hierarchical/` — Google Maps-style hierarchical documentation (Earth + 11 Continent subsystem docs)
- `graphify-out/` — Persistent Codebase Knowledge Graph (`graph.json`, `GRAPH_REPORT.md`, `graph.html`)
- `README.md` — primary setup, usage, architecture, and feature documentation
- `src/cli.py` — unified CLI for input conversion, knowledge graph queries, and tailored resume generation
- `src/generators/` — modular resume generator package (`resume_generator.py`, `pdf_renderer.py`, `pdf_styles.py`, `models.py`, `constants.py`, `ats_matcher.py`)
- `scripts/` — operational script wrappers (`convert_inputs.py`, `query.py`, `run_litellm.py`)
- `config/` — centralized configurations (`settings.yaml`, `litellm-config.yaml`)
- `output/`, `cache/`, `logs/` — runtime artifacts, not source files

## Codebase Entry Protocol (codebase-memory MCP & Graphify - Mandatory)

Before exploring raw files or executing cold-start scans, always use `codebase-memory` MCP and the pre-built Graphify knowledge graph index to navigate architecture, symbol relationships, and dependencies with minimal token consumption:

- **Hierarchical Index**: Read [`docs/hierarchical/README.md`](docs/hierarchical/README.md).
- **codebase-memory MCP Navigation**:
  - Project Overview: `get_architecture(project="C-Users-mamat-Github-Prasad-Resumes-GraphRAG", aspects=["overview", "clusters"])`
  - Subsystem Structure: `get_architecture(project=..., aspects=["structure"], path="src/<subsystem>")`
  - Symbol Search: `search_graph(project=..., query="<symbol_or_keyword>")`
  - Blast Radius & Changes: `detect_changes(project=...)`
- **Graphify Orientation**: Read `graphify-out/GRAPH_REPORT.md` or parse `graphify-out/graph.json`.
- **Querying Architecture / Symbols via Graphify**:
  ```powershell
  python -m graphify query "<natural language query or function/class name>"
  # e.g.:
  python -m graphify query "How does the gateway handle fallbacks?" --budget 1500
  python -m graphify path "BaseProvider" "GeminiProvider"
  ```
- **Incremental Re-indexing**:
  ```powershell
  python -m graphify --update
  ```

## Recommended workflow

1. Ensure the Python virtual environment is active (`.\venv\Scripts\Activate.ps1`).
2. Populate `.env` with a valid `GEMINI_API_KEY` and never commit this file.
3. Consult Graphify (`python -m graphify query ...`) to orient on the relevant modules.
4. Start LiteLLM Proxy: `python scripts/run_litellm.py` (or `python src/cli.py proxy`)
4. Convert source files when needed: `python scripts/convert_inputs.py` (or `python src/cli.py convert`)
5. Build or update the GraphRAG index: `python -m graphrag index --root .`
6. Query the graph:
   - `python scripts/query.py --local "..."`
   - `python scripts/query.py --global "..."`
   - Or via CLI: `python src/cli.py query --mode local "..."`
7. Generate tailored raw text & PDF resume:
   - `python src/cli.py generate --company <Company_Name> --jd-file <Path_To_JD.txt>`

## Project conventions

- This repo uses GraphRAG 2.5 with a LiteLLM proxy and OpenRouter/Google Gemini models.
- Uses Pydantic models (`ResumeData`, `JobEntry`) in `src/generators/models.py` for structured resume data modeling.
- PDF generation adheres to exact layout standards (Calibri/Helvetica fonts, tight margins, 2-page max budget, KeepTogether job blocks, left alignment, clickable links).
- Code is 100% generic and candidate-agnostic, supporting dynamic candidate name, contact, and header extraction.
- Centralized configurations live in `config/settings.yaml` and `config/litellm-config.yaml`.
- Modular code lives under `src/` with unit tests under `tests/`.

## What to avoid

- Do not modify or commit `venv/`, `output/`, `cache/`, `logs/`, or `.env`.
- Do not hardcode API keys into source files.
- Avoid changing model endpoints or embedding models without checking `README.md` and `config/settings.yaml` first.

## Useful links

- [README.md](README.md)
- [GEMINI.md](GEMINI.md)
