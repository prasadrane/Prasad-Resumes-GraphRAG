# CLAUDE.md

This file provides guidance to Claude Code (cla.ai/code) when working with code in this repository.

## Project Overview

GraphRAG knowledge graph engine and automated ATS resume generator built over Prasad Rane's master resume and story bank content. The system uses Microsoft GraphRAG for knowledge extraction, LiteLLM proxy for multi-model LLM routing (OpenRouter + Google Gemini), and generates tailored 2-page PDF resumes with ATS-compliant formatting.

## Codebase Orientation & Indexing Protocol (Graphify)

**Mandatory Rule for Claude Code & AI Agents:**
Always consult the Graphify knowledge graph index before reading raw files or doing cold-starts across the repository.

1. **Pre-built Index Assets**:
   - `graphify-out/graph.json`: Complete graph structure (3,700+ nodes, 7,900+ edges, 170 communities).
   - `graphify-out/GRAPH_REPORT.md`: Architectural overview, God Nodes, and surprising connections.
   - `graphify-out/graph.html`: Interactive visualization.

2. **Querying the Knowledge Graph (Default Tool for Navigation & Context)**:
   ```bash
   # Traverse and inspect architecture/symbols with token-budgeted precision
   python -m graphify query "<your question or symbol>"
   python -m graphify query "How does Gateway failover work?" --budget 1500
   python -m graphify path "BaseProvider" "AlibabaProvider"
   ```

3. **Incremental Index Updates**:
   ```bash
   # Update graph index when new files or functions are added
   python -m graphify --update
   ```

## Common Development Commands

### Environment Setup
```bash
# Activate virtual environment (PowerShell)
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements-dev.txt  # Includes graphrag, litellm, lancedb, pdf tools
```

### Running the Application
```bash
# Start LiteLLM Proxy (required for GraphRAG indexing, port 8002)
python scripts/run_litellm.py
# Or via CLI:
python src/cli.py proxy

# Launch Web UI (runs `vercel dev` on port 3000 — matches production path)
python src/cli.py ui

# Convert source documents to GraphRAG input format
python scripts/convert_inputs.py
# Or via CLI:
python src/cli.py convert --source <path_to_source_dir>

# Build/update GraphRAG knowledge graph index
python -m graphrag index --root .

# Query knowledge graph
python src/cli.py query --mode local "What AWS technologies did Prasad use?"
python src/cli.py query --mode global "Summarize Prasad's career trajectory"

# Generate tailored resume (raw text + PDF)
python src/cli.py generate --company <Company_Name> --jd-file <Path_To_JD.txt>
```

### Testing
```bash
# Run all unit tests (unittest discovery)
python -m unittest discover tests

# Run a single test file
python -m unittest tests/test_ats_matcher.py

# Run with verbose output
python -m unittest discover tests -v

# Run pytest-style tests (fixtures in conftest.py, pytest-playwright for e2e)
python -m pytest tests/

# Run e2e baseline smoke test
python scripts/run_e2e_baseline.py

# Run with coverage
coverage run -m unittest discover tests
coverage report
```

### Docker Deployment
```bash
# Build and run LiteLLM proxy container (port 8002)
docker-compose up -d

# Build Docker image manually
docker build -t graphrag-proxy .
```
Note: The Dockerfile only packages the LiteLLM proxy, not the full web app or GraphRAG indexer.

### Vercel Deployment
```bash
# Deploy to Vercel (requires OPENROUTER_API_KEY and GEMINI_API_KEY in env)
vercel --prod
```

## Architecture & System Design

### Core Pipeline Flow
1. **Input Preprocessing** (`src/converters/`): Parses raw PDFs/Markdown into canonical `input/MASTER_RESUME.txt` and `input/03-Story-Bank.txt`
2. **GraphRAG Indexing**: Extracts entities, relationships, communities; stores embeddings in LanceDB (`output/lancedb`) and Parquet tables
3. **LLM Gateway** (`src/gateway/`): Provider-driven routing with `_try_chain` failover. Three providers — AlibabaProvider (Anthropic API), OpenRouterProvider (OpenAI API), GeminiProvider (Google REST) — orchestrated by `facade.py`. Provider selection via `src/config/providers.py` registry.
4. **Resume Generation** (`src/generators/`): NLP keyword extraction, executive summary adaptation, skill reordering, ATS-compliant PDF rendering
5. **FastAPI Web UI** (`src/web/` & `api/index.py`): Material Design 3 interface with ATS tailoring, raw Markdown editor, and GraphRAG Q&A chatbot

### Unified Deployment Architecture (Critical)
The app has a single entrypoint and unified code path for both local and production:
- **Single FastAPI app** (`src/web/app.py`): Contains all endpoint logic and serves the Material Design 3 UI
- **Vercel wrapper** (`api/index.py`): Thin wrapper that imports `src/web/app.py` and re-exports it for Vercel Python Functions (ASGI apps accepted directly)
- **Local dev** (`python src/cli.py ui`): Runs `vercel dev` on port 3000 — tests the actual production path locally
- **Production** (`vercel --prod`): Deploys `api/index.py` which wraps the same `src/web/app.py`
- **Shared router** (`src/shared/api_routes.py`): Endpoints like `/api/query`, `/api/chat-stream` are defined once in `shared_router` and included by `src/web/app.py` — never duplicate these endpoints
- **Shared models** (`src/shared/api_models.py`): Pydantic request/response schemas used across all endpoints

### Multi-Model LLM Fallback Architecture
Three LLM paths exist — understand which one is being used:
- **Gateway package** (`src/gateway/`): Used by Vercel deployment and `src/llm/service.py` wrappers. Three providers — Alibaba (Anthropic API), OpenRouter (OpenAI API), Gemini (Google REST) — with `_try_chain` failover. Provider selection via `src/config/providers.py` registry (`CHAT_PROVIDER`, `RESUME_PROVIDER`, `EMBEDDING_PROVIDER` env vars)
- **LiteLLM proxy** (port 8002, `config/litellm-config.yaml`): Used by GraphRAG indexing and local queries. Fallback chain: `freellmapi-chat` → `gemini-2.5-flash-lite` → `gemini-3.1-flash-lite` → `gemini-3.5-flash-lite` → `gemini-2.5-flash` → `gemini-2.0-flash`
- **LLM service** (`src/llm/service.py`): Thin wrappers (`call_llm`, `call_llm_safe`) used by resume generators. Routes through gateway. `call_llm_safe` catches all exceptions and returns empty string for graceful degradation
- **Embeddings**: `nvidia/nemotron-3-embed-1b:free` via OpenRouter (primary) → `text-embedding-004` via Gemini (fallback)

### Key Modules

#### `src/converters/`
- `input_converter.py`: Converts PDFs/Markdown to plain text
- `pdf_parser.py`: PDF text extraction using PyMuPDF/pdfplumber
- `resume_structurer.py`: Structures raw resume data into canonical format

#### `src/generators/`
- `ats_matcher.py`: NLP-based ATS keyword extraction and job description matching
- `resume_generator.py`: Assembles tailored raw resume with bold keyword marking (<20% cap, max 3 phrases/bullet)
- `resume_parser.py`: Parses resume markdown into structured components
- `pdf_renderer.py` & `pdf_styles.py`: Renders 2-page max PDF with tight margins (0.55" L/R, 0.45" T/B), KeepTogether blocks, clickable links
- `models.py`: Pydantic models (`ResumeData`, `JobEntry`) for structured data
- `constants.py`: Centralized constants (fonts, colors, spacing)

#### `src/gateway/`
- `base.py`: `BaseProvider` ABC + shared lazy aiohttp session (`_ensure_session()`)
- `alibaba.py`: AlibabaProvider — Anthropic-compatible protocol (`x-api-key` + `anthropic-version`)
- `openrouter.py`: OpenRouterProvider — OpenAI-compatible protocol (`Authorization: Bearer`)
- `gemini.py`: GeminiProvider — Google REST protocol (`?key=` query param auth)
- `facade.py`: Orchestration — `_client()` cache, `_try_chain` failover, public API (`call_serverless_llm`, `call_serverless_llm_stream`, `get_embedding`)
- `__init__.py`: Re-exports public API + registry-resolved `ALIBABA_RESUME_MODEL`

#### `src/query/`
- `search_engine.py`: Executes GraphRAG local/global queries (used by shared router)
- `graphrag_engine.py`: GraphRAGEngine with 3 retrieval modes (local · global · drift), SSE streaming, conversation memory
- `static_graph_reader.py`: Fast static graph reader for serverless (<1s execution, reads precomputed entities from Parquet)
- `serverless_gateway.py`: **Deprecated re-export shim** (~30 lines). Delegates to `src.gateway`. Old import path still works.

#### `src/proxy/`
- `litellm_runner.py`: Manages LiteLLM proxy lifecycle and health checks

#### `src/web/`
- `app.py`: Canonical FastAPI application with Material Design 3 UI (includes `shared_router`); used by both local dev and Vercel production
- `static/`: Frontend assets (HTML, CSS, JS)

#### `src/shared/`
- `api_models.py`: Pydantic schemas (`ResumeGenerationRequest`, `SaveEditRequest`, `QueryRequest`) shared across both deployment targets
- `api_routes.py`: `shared_router` with endpoints that must remain identical in both local and serverless apps

#### `src/config.py`
Centralized path resolution. `ROOT_DIR` is derived from this file's location. Key exports: `INPUT_DIR`, `OUTPUT_DIR`, `MASTER_RESUME_PATH`, `WEB_STATIC_DIR`. Bootstrap exception: `api/index.py` and `src/cli.py` compute their own `ROOT_DIR` before importing `src.*` because they need it on `sys.path` first.

#### `api/index.py`
Thin Vercel serverless wrapper — adds the project root to `sys.path`, then imports and re-exports `app` from `src/web/app.py`. All endpoint logic lives in `src/web/app.py` and `src/shared/api_routes.py`; this file contains zero endpoint definitions. Vercel Python Functions accept ASGI apps directly, so no additional adapter is needed.

## Configuration Files

- `settings.yaml`: GraphRAG 2.5 configuration (models, chunking, entity extraction, community reports). Points chat at `localhost:8002` (LiteLLM proxy) with `freellmapi-chat` model
- `config/litellm-config.yaml`: LiteLLM proxy model routing and fallback configuration
- `config/settings.yaml`: Duplicate/alternative GraphRAG settings — check which one `graphrag index --root .` resolves (it uses the root-level `settings.yaml`)
- `.env`: API keys (OPENROUTER_API_KEY, GEMINI_API_KEY, FREELLMAPI_API_KEY)
- `vercel.json`: Vercel deployment routing configuration (catch-all to `api/index.py`)
- `Dockerfile` & `docker-compose.yml`: Container deployment for LiteLLM proxy only

## Environment Variables

Required in `.env` (never commit this file):
```env
GRAPHRAG_API_KEY=<your_gemini_api_key>
OPENROUTER_API_KEY=<your_openrouter_api_key>
FREELLMAPI_API_KEY=<your_freellmapi_key>
```

## Key Input/Output Paths

- **Input**: `input/MASTER_RESUME.txt`, `input/03-Story-Bank.txt`
- **Output**: `output/lancedb/` (embeddings), `output/*.parquet` (graph tables)
- **Generated Resumes**: `output/<Company>/Prasad_Rane_<Company>_Resume.pdf`
- **Cache**: `cache/` (GraphRAG intermediate files)
- **Logs**: `logs/` (indexing and query logs)

## Testing Patterns

- Unit tests use Python's built-in `unittest` framework (discoverable with `python -m unittest discover tests`)
- Pytest fixtures are defined in `tests/conftest.py` (e.g., `sample_master_resume_text`) — these are consumed by pytest-style test functions, not unittest
- E2E tests use `pytest-playwright` and `httpx` (see `scripts/run_e2e_baseline.py`)
- Test files follow naming convention: `test_<module_name>.py` in `tests/` mirroring `src/` structure
- Mock external dependencies (API calls, file I/O) where appropriate
- PDF rendering tests verify layout constraints (page count, margins, fonts)

## Critical Design Constraints

### Resume Generation Rules
- **2-page maximum budget**: Preserve full career history across all companies
- **ATS compliance**: <20% bold character cap, max 3 bold phrases per bullet
- **Clean header**: Omit default title header; flow from contact info to Executive Summary
- **Keyword bolding**: Highlight JD-matched technical terms across summary, experience, and skills
- **Skill category prioritization**: Reorder categories by JD relevance (without dropping skills)
- **Executive summary adaptation**: Score domain variants against JD to select best match

### PDF Layout Standards
- Fonts: Calibri/Helvetica family
- Margins: 0.55" left/right, 0.45" top/bottom
- KeepTogether blocks for job entries (prevent awkward page breaks)
- Clickable contact links (email, phone, LinkedIn)
- Left-aligned text throughout

### Serverless Resilience
- Redirect output directory creation to `/tmp/output` on read-only filesystems
- Serve PDFs via inline data URIs (base64 encoding)
- Use `static_graph_reader.py` for fast queries without full GraphRAG runtime

## What NOT to Commit

Per `.gitignore`:
- `venv/` (virtual environment)
- `.env` (API keys)
- `output/`, `cache/`, `logs/` (runtime artifacts)
- `__pycache__/`, `*.pyc` (Python cache files)
- `.pytest_cache/` (test cache)
- `.graphify/`, `scratch/`, `*.tmp` (temporary files)
- `.coverage`, `coverage.xml`, `htmlcov/` (coverage reports)

## Additional Resources

- `README.md`: User-facing setup, features, and architecture documentation
- `AGENTS.md`: AI agent workflow instructions and project conventions
- `GEMINI.md`: Detailed Gemini integration guide with model quotas and fallback strategy
- `docs/`: Architecture diagrams and supplementary documentation
