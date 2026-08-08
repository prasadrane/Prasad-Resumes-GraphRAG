# Technology Stack

## Language & Runtime Environment
- **Language:** Python 3.11+
- **Environment Management:** Python Virtual Environment (`venv/`)
- **Configuration:** `.env` (API key loading via `python-dotenv`)

## Core GraphRAG & AI Stack
- **GraphRAG Engine:** Microsoft GraphRAG 2.5 (`graphrag`)
- **LLM Proxy Middleware:** LiteLLM Proxy (`litellm`) running locally on `http://localhost:8002`
- **Primary Chat Model:** `freellmapi-chat` (OpenRouter pool via local API)
- **Fallback Chat Models:** Google Gemini Free Tier (`gemini-2.5-flash-lite`, `gemini-3.1-flash-lite`, `gemini-3.5-flash-lite`, `gemini-2.5-flash`, `gemini-2.0-flash`)
- **Primary Embedding Model:** Nvidia `llama-nemotron-embed-vl-1b-v2` (2048 dims)
- **Fallback Embedding Model:** Google `gemini-embedding-001` (3072 dims)

## Data Storage & Vector Engine
- **Vector Database:** LanceDB (`output/lancedb`)
- **Graph Index Storage:** Apache Parquet (`output/*.parquet`)
- **Caching Layer:** Persistent file cache (`cache/`) + Runtime LRU cache (`@lru_cache`)

## Deployment & Serverless Gateway
- **Deployment Platform:** Vercel Free Tier (Serverless Hobby Plan via `@vercel/python` / `vercel.json`)
- **Serverless Framework:** FastAPI (`api/index.py`)
- **Serverless Cloud Gateway:** `src/query/serverless_gateway.py` (Direct OpenRouter / Gemini API routing for stateless environments)
- **Static Graph Reader:** `src/query/static_graph_reader.py` (Fast pre-indexed graph search < 1s)

## Preprocessing & Utilities
- **PDF Extraction:** PyMuPDF (`fitz`), `pdfplumber`, `pypdf`
- **PDF Generation:** ReportLab (`reportlab`) rule-based PDF engine
- **Configuration Engine:** PyYAML (`pyyaml`)
- **Testing:** Standard Python `unittest` framework

