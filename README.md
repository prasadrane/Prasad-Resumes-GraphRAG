# Prasad Resumes - GraphRAG Knowledge Graph & Tailored Resume Generator

GraphRAG knowledge graph engine and automated ATS resume generator built over Prasad Rane's master resume and story bank content. Powered primarily by **OpenRouter API** (with direct Google Gemini AI Studio API fallback).

---

## Architecture & System Data Flow

![Architecture & System Data Flow](docs/architecture_diagram.png)

The diagram shows two primary flows sharing common infrastructure:

- **Chat Q&A flow (left):** User question → Embedding API → LanceDB vector search → GraphRAG Engine (retrieval) → LLM Gateway → streamed SSE answer
- **Resume Tailoring flow (right):** Job Description + Master Resume → ATS Matcher (keyword extraction) → GraphRAG Engine (context retrieval) → LLM Gateway (tailoring prompt) → Markdown + PDF output

Shared components:
- **LLM Gateway (`src/gateway/`):** Provider-driven routing with `_try_chain` failover. Three providers — **Alibaba Cloud Token Plan** (Anthropic-compatible), **OpenRouter** (OpenAI-compatible), **Gemini Direct** (Google REST) — orchestrated by `facade.py`. Provider selection via `src/config/providers.py` registry (`CHAT_PROVIDER`, `RESUME_PROVIDER`, `EMBEDDING_PROVIDER` env vars).
- **GraphRAG Engine:** Three retrieval modes (local · global · drift), conversation memory, SSE streaming
- **LanceDB:** Vector store + knowledge graph for both flows

---

## Key Features

### 1. REAL ATS Resume Tailoring Engine (Zero Resume Shrinking)
- **Dynamic NLP Keyword & Technology Extraction**: Dynamically extracts specialized tools, cloud services, frameworks, and domain competencies from target job descriptions (*CrowdStrike*, *Falcon*, *AWS ECS Fargate*, *Amazon Bedrock*, *Kafka*, *OAuth2*, *Dynatrace*, *Single-Table DynamoDB*).
- **Dynamic Executive Summary Adaptation**: Scores candidate domain summary variants (*AI/LLM-Forward*, *Cloud & Reliability-Forward*, *Platform & DevEx-Forward*, *Security & Auth-Forward*) against JD requirements to select and adapt the best-matching summary.
- **Skill Category Prioritization**: Reorders technical skill categories dynamically so the categories most relevant to the JD appear first (without dropping any skills).
- **Precision Keyword Bolding**: Highlights JD-matched technical terms across summary, experience bullets, and skills section adhering to ATS <20% bold character caps.
- **Clean Header (Title Excluded)**: Completely omits default title header lines for clean, professional presentation flowing from candidate contact info directly into the Executive Summary.
- **Full 2-Page Budget Guarantee**: Preserves full bullet counts and complete career history across all 4 companies (Rocket Mortgage, London Computer Systems, EXFO, Tanish Infotech).

### 2. Interactive Preview Drawer & Raw Content Editor
- View rendered PDF previews side-by-side with an instant raw Markdown text editor.
- **Stateful In-Memory Editing**: No delay or infinite loading state when clicking *"Edit Raw Content"*.
- **Save & Re-render PDF**: Edit raw markdown directly in the UI drawer and re-render standard ATS PDFs in one click.

### 3. GraphRAG AI Chatbot (Ask Me Questions)
- Interactive Q&A interface powered by Prasad's GraphRAG knowledge graph and static resume search engine.
- **Purpose-Built Dual Query Modes**:
  - **Local Context**: Granular entity facts, exact project metrics (e.g. 70% Bedrock speedup, 40% Fargate cost reduction), company-by-company project details.
  - **Global Summary**: Synthesized executive career overviews, 10+ year trajectory pillars, cloud/AI migration milestones, and overarching technical leadership themes.
- Formatted Markdown responses with bullet lists, bold highlights, code blocks, clear chat reset, sample question action chips, and one-click copy to clipboard.

### 4. Vercel Serverless & Read-Only File System Resilience
- Fully resilient to serverless read-only filesystems (`/var/task`), automatically redirecting output directory creation to `/tmp/output`.
- Serves PDFs via inline data URIs and harmonizes API routes (`/api/generate`, `/api/render_pdf`, `/api/save-edit`, `/api/query`) across local servers and Vercel deployments.

---

## Configuration & Environment Variables

Create a `.env` file in the project root directory:

```env
# Primary LLM Provider (OpenRouter API)
OPENROUTER_API_KEY=sk-or-v1-your_openrouter_api_key_here

# Fallback LLM Provider (Google Gemini AI Studio API)
GEMINI_API_KEY=your_gemini_api_key_here

# GraphRAG Indexer (points at Gemini via LiteLLM proxy)
GRAPHRAG_API_KEY=your_gemini_api_key_here

# FreeLLMAPI (primary model in settings.yaml, routed via LiteLLM proxy)
FREELLMAPI_API_KEY=your_freellmapi_api_key_here

# Alibaba Cloud Token Plan (Anthropic-compatible, used for chat/resume)
ALIBABA_API_KEY=sk-sp-your_alibaba_token_plan_key
```

### Provider Registry (Flexible LLM Configuration)

The system uses a provider registry (`src/config/providers.py`) to map use-cases to LLM providers. You can switch providers via environment variables without code changes:

```env
# Optional: Override default providers (defaults shown below)
CHAT_PROVIDER=alibaba        # Chatbot: alibaba | openrouter | gemini
RESUME_PROVIDER=alibaba      # Resume generation: alibaba | openrouter | gemini
EMBEDDING_PROVIDER=openrouter # Embeddings: openrouter | gemini
```

**Default configuration:**
- **Chat:** Alibaba Cloud Token Plan (`qwen3.6-flash`, ~10-20s streaming)
- **Resume:** Alibaba Cloud Token Plan (`qwen3.7-plus`, ~3-4 min)
- **Embedding:** OpenRouter (`openai/text-embedding-3-small`)

**Adding a new provider:** Edit `src/config/providers.py`, add entry to `PROVIDERS` dict with `base_url`, `api_key_env`, `models`, `timeout`, and `response_format`. Then set the corresponding env var (e.g., `CHAT_PROVIDER=new_provider`).

### Gateway Package (`src/gateway/`)

The LLM gateway is a small package that wraps each provider as a self-contained class and exposes a single public API for callers:

```
src/gateway/
├── __init__.py      # Public API: call_serverless_llm, call_serverless_llm_stream,
│                    # get_embedding, ALIBABA_RESUME_MODEL
├── base.py          # BaseProvider ABC + shared aiohttp session
├── alibaba.py       # AlibabaProvider — Anthropic-compatible protocol
├── openrouter.py    # OpenRouterProvider — OpenAI-compatible protocol
└── gemini.py        # GeminiProvider — Google REST protocol (auth via ?key=)
└── facade.py        # Orchestration: _try_chain failover, provider cache, public API
```

**Adding a new provider to the gateway:**
1. Add a `ProviderConfig` entry in `src/config/providers.py`
2. Create `src/gateway/<provider>.py` implementing `BaseProvider` (override `chat()`, `chat_stream()`, and optionally `embed()`)
3. Register the class in `facade.py`'s `_PROVIDER_CLASSES` dict
4. Switch via env var (e.g., `CHAT_PROVIDER=new_provider`)

The old import path (`from src.query.serverless_gateway import ...`) still works via a re-export shim but new code should import from `src.gateway` directly.

---

## Quick Start Setup

### 1. Activate Virtual Environment
```powershell
.\venv\Scripts\Activate.ps1
```

### 2. Start LiteLLM Proxy (required for GraphRAG indexing)
```powershell
python src/cli.py proxy
```
The proxy runs on port 8002 and routes `freellmapi-chat` → OpenRouter/Gemini fallback chain.

### 3. Launch Web UI (FastAPI Server)
```powershell
python src/cli.py ui
```
This runs `vercel dev` under the hood, matching the production Vercel deployment path. Requires the Vercel CLI: `npm i -g vercel`.
Open **http://localhost:3000** in your browser (port assigned by `vercel dev`).

### 4. Generate Tailored Resume via CLI
```powershell
python src/cli.py generate --company <Company_Name> --jd-file <Path_To_JD.txt>
```

### 5. Query Knowledge Graph via CLI
```powershell
python src/cli.py query --mode local "What AWS technologies did Prasad use?"
```

### 6. Build or Re-Index Knowledge Graph
```powershell
python -m graphrag index --root .
```

### 7. Run Unit Test Suite
```powershell
.\venv\Scripts\python.exe -m unittest discover tests
```

---

## Vercel Serverless Deployment

The application uses a unified deployment model — `api/index.py` wraps `src/web/app.py`, so local development (`python src/cli.py ui` → `vercel dev`) and production use the same code path.

Deploy to **Vercel Free Tier**:

```powershell
vercel --prod
```

Ensure `OPENROUTER_API_KEY` and `GEMINI_API_KEY` are configured in Vercel project environment variables.

---

## API Reference

All endpoints are available on both the local server (`python src/cli.py ui` runs `vercel dev` on port 3000) and Vercel (`api/index.py`).

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Web UI (local only) |
| `POST` | `/api/generate` | Generate tailored resume from company + JD text |
| `POST` | `/api/render_pdf` | Render PDF from raw resume markdown |
| `POST` | `/api/save-edit` | Save edited raw resume and re-render |
| `POST` | `/api/query` | GraphRAG Q&A query |
| `POST` | `/api/chat-stream` | Streaming chatbot (SSE) |
| `GET` | `/api/default-resume` | Get default master resume content |

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `graphrag index` fails with connection error | LiteLLM proxy not running | Start it: `python src/cli.py proxy` |
| Chatbot returns raw entity dump, no LLM synthesis | Missing `OPENROUTER_API_KEY` and `GEMINI_API_KEY` | Add at least one to `.env` |
| `vercel dev` fails to start | Port conflict or Vercel CLI not installed | Kill conflicting process on port 3000, or run `vercel dev --port 3001` |
| `Address already in use: 8002` | LiteLLM proxy already running | Use the existing instance |
| PDF not generated on Vercel | Read-only filesystem | Output is auto-redirected to `/tmp/output` — check Vercel function logs |
