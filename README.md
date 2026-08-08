# Prasad Resumes - GraphRAG Knowledge Graph & Tailored Resume Generator

LLM-powered knowledge graph built over Prasad's **Master Resume** (consolidated from 47+ resume variations and master source files) and **Behavioral Story Bank**, using Microsoft GraphRAG + Google Gemini + FreeLLMAPI / OpenRouter fallback pool, complete with an automated ATS-tailored raw text and rule-based PDF resume generation pipeline.

**Status:** 🚀 **Enterprise Modular & Production Ready** | Clean architecture with `src/` modules, `config/` settings, `scripts/` launchers, and test suites.

---

## 🏗️ Architecture & System Data Flow

```mermaid
flowchart TD
    subgraph InputProcessing["1. Input Preprocessing & Conversion"]
        A["Raw Resume PDFs & Markdown Docs"] -->|src/cli.py convert| B["PyMuPDF Parser (pdf_parser.py)"]
        B -->|Spatial Sorting & Clean Whitespace| C["Resume Structurer (resume_structurer.py)"]
        C -->|Header Normalization H2 Section Headings| D["input/MASTER_RESUME.txt & 03-Story-Bank.txt"]
    end

    subgraph IndexingPipeline["2. GraphRAG Indexing Engine"]
        D -->|src/cli.py index| E["Text Chunking (1000 tokens / 150 overlap)"]
        E --> F["Entity & Relationship Extraction (10 Custom Types)"]
        F --> G["Community Detection & Summarization"]
        G --> H["LanceDB Vector Store (output/lancedb)"]
        G --> I["Parquet Entity Tables (output/*.parquet)"]
    end

    subgraph ProxyRouter["3. LiteLLM Proxy Middleware (Port 8002)"]
        F -.->|LLM & Embedding Requests| J{"LiteLLM Proxy Router (config/litellm-config.yaml)"}
        
        subgraph ChatCascade["Chat LLM Fallback Cascade"]
            J -->|Primary| K["freellmapi-chat (OpenRouter Pool)"]
            K -- 429 / Rate Limit --> L["gemini-2.5-flash-lite (1500 RPD)"]
            L -- Quota Exceeded --> M["gemini-3.1-flash-lite (1500 RPD)"]
            M -- Quota Exceeded --> N["gemini-3.5-flash-lite (1500 RPD)"]
            N -- Secondary Fallback --> O["gemini-2.5-flash / gemini-2.0-flash"]
        end

        subgraph EmbedCascade["Embedding Fallback Cascade"]
            J -->|Primary| P["llama-nemotron-embed-vl-1b-v2 (2048 dims)"]
            P -- 429 / Rate Limit --> Q["gemini-embedding-001 (3072 dims)"]
            Q -- Fallback --> R["freellmapi-embeddings"]
        end
    end

    subgraph TailoredGenerator["4. Tailored Resume & PDF Generation Pipeline"]
        JD["Job Description Text File"] -->|src/cli.py generate| ATS["ATS Keyword Extraction (ats_matcher.py)"]
        ATS --> RAW["Raw Resume Assembly (resume_generator.py)"]
        D -.-> RAW
        RAW -->|output/<MM-DD-YYYY>/<Company>/raw_resume.txt| PDF["Rule-Based ReportLab PDF Renderer (pdf_renderer.py)"]
        PDF -->|output/<MM-DD-YYYY>/<Company>/Prasad_Rane_Resume.pdf| FINAL["Standard PDF Resume (Prasad_Rane_Resume.pdf)"]
    end

    subgraph QueryExecution["5. Search & Query Execution"]
        S["User Query"] --> T["Unified CLI (src/cli.py query) / scripts/query.py"]
        T --> U{"LRU Cache (Max 100)"}
        U -- Cache Hit --> V["Cached Response Output"]
        U -- Cache Miss --> W["Search Engine (src/query/search_engine.py)"]
        W -->|Local Search| H
        W -->|Global Search| I
        W -.->|LLM Synthesizer| J
        W --> V
    end
```

---

## 📁 Folder Structure

- `src/`                <- Enterprise modular application code
  - `converters/`      <- PDF parsing (`pdf_parser.py`) and section structuring (`resume_structurer.py`)
  - `generators/`      <- Resume generation (`resume_generator.py`), PDF renderer (`pdf_renderer.py`), styling (`pdf_styles.py`), Pydantic models (`models.py`), constants (`constants.py`), and ATS matcher (`ats_matcher.py`)
  - `query/`           <- Search execution (`search_engine.py`) with LRU caching & DIP runner
  - `proxy/`           <- LiteLLM proxy runner (`litellm_runner.py`)
  - `cli.py`           <- Unified CLI entrypoint (`convert`, `index`, `query`, `generate`, `proxy`)
- `config/`             <- Centralized pipeline & LLM fallback configs (`settings.yaml`, `litellm-config.yaml`)
- `scripts/`            <- Operational CLI helper wrappers (`convert_inputs.py`, `query.py`, `run_litellm.py`)
- `tests/`              <- Automated unit test suite (33 tests covering converters, generators, PDF renderer, ATS matcher, search engine, CLI)
- `input/`              <- Consolidated input files: [`MASTER_RESUME.txt`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/input/MASTER_RESUME.txt) & [`03-Story-Bank.txt`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/input/03-Story-Bank.txt)
- `output/`             <- GraphRAG index artifacts, LanceDB vector store, and date-organized company output folders (`output/<MM-DD-YYYY>/<Company>/`)
- `cache/`              <- LLM request cache (saves API quota and costs)
- `logs/`               <- Indexing and runtime log files
- `venv/`               <- Python virtual environment
- `.env`                <- `GEMINI_API_KEY` configuration (do not commit)
- `GEMINI.md`           <- Gemini model quotas & fallback architecture guide
- `AGENTS.md`           <- Agent instructions and workflow guidelines

---

## ⚙️ Quick Start Setup

### 1. Configure API Key
Add your Gemini API Key to `.env`:
```env
GEMINI_API_KEY=your_actual_key_here
```

### 2. Activate Virtual Environment
```powershell
.\venv\Scripts\Activate.ps1
```

### 3. Start LiteLLM Proxy (Port 8002)
```powershell
python scripts/run_litellm.py
```
*Or via unified CLI:*
```powershell
python src/cli.py proxy
```

### 4. Build Knowledge Graph (Index)
Via unified CLI:
```powershell
python src/cli.py index
```
Or via raw GraphRAG CLI:
```powershell
python -m graphrag index --root .
```

### 5. Query the Knowledge Graph
Using the unified CLI:
```powershell
python src/cli.py query --mode local "What AWS technologies did Prasad use at Rocket Mortgage?"
python src/cli.py query --mode global "What are the core technical themes across Prasad's experience?"
```
Or via script wrapper:
```powershell
python scripts/query.py --local "..."
python scripts/query.py --global "..."
```

### 6. Generate Tailored Raw Text & PDF Resume
Generate ATS-tailored raw Markdown resume (`raw_resume.txt`) and standard PDF resume (`Prasad_Rane_Resume.pdf`) for a target job description:
```powershell
python src/cli.py generate --company GitHub --jd-file path/to/github_jd.txt
```
*Outputs are created under `output/<MM-DD-YYYY>/<Company_Name>/`:*
- `output/<MM-DD-YYYY>/<Company_Name>/raw_resume.txt`
- `output/<MM-DD-YYYY>/<Company_Name>/Prasad_Rane_Resume.pdf`

### 7. Vercel Free Tier Serverless Deployment
This repository includes a serverless refactor allowing deployment to **Vercel Free Tier** using FastAPI (`api/index.py`), direct OpenRouter/Gemini API gateway (`src/query/serverless_gateway.py`), and pre-computed static graph reader (`src/query/static_graph_reader.py`).

- **Deploy via Vercel CLI:**
  ```powershell
  vercel --prod
  ```
- **Local Serverless Test:**
  ```powershell
  vercel dev
  ```
- **Required Environment Variables in Vercel:**
  - `OPENROUTER_API_KEY`: Key for direct cloud LLM routing
  - `GEMINI_API_KEY`: Key for direct Google Gemini fallback API

### 8. Run Unit Tests
```powershell
python -m unittest discover -s tests
```


---

## 📄 Resume Generation Standards & Rules

The PDF renderer follows strict ATS resume design standards:

- **Left Alignment**: Entire text is left-aligned.
- **Page Margins**: `0.55"` left/right, `0.45"` top/bottom.
- **Typography & Font Sizes**:
  - Name: `23pt` Bold (`#1a1a2e`)
  - Contact Line: `9.5pt` Normal (`#6b7280`) with clickable links for email, LinkedIn, portfolio, and credentials
  - Section Headers: `10.5pt` Bold (`#1a1a2e`)
  - Single-line Job Headings: `10.5pt` (`Title | Company Name | Location | Dates`)
  - Bullets & Body: `9.5pt` (`#374151`)
- **Job Block Integrity**: Wrapped in ReportLab `KeepTogether` flowables to prevent awkward page splits across jobs.
- **2-Page Maximum Constraint**: Strict page budget enforced with automated canvas page counters.
- **Candidate-Agnostic Engine**: Candidate name, contact details, and headers are parsed dynamically from the source Markdown resume.

---

## 🔄 Multi-Tier Fallback Architecture

To eliminate rate-limiting (`429`) and daily quota blocks during indexing and querying, requests are routed through **LiteLLM Proxy (port 8002)** using an automated multi-tier fallback chain:

### Chat Model Fallback Order
1. **`freellmapi-chat`** *(Primary)* — FreeLLMAPI routing to OpenRouter free models (no daily quota cap)
2. **`gemini-2.5-flash-lite`** — 1,500 RPD high-quota runner
3. **`gemini-3.1-flash-lite`** — 1,500 RPD high-quota fallback
4. **`gemini-3.5-flash-lite`** — 1,500 RPD high-quota fallback
5. **`gemini-2.5-flash`** — Low-quota fallback (20 RPD)
6. **`gemini-2.0-flash`** — Low-quota fallback (20 RPD)

### Embedding Model Fallback Order
1. **`llama-nemotron-embed-vl-1b-v2`** *(Primary)* — Nvidia 2048-dim via FreeLLMAPI -> OpenRouter
2. **`gemini-embedding-001`** — 1,500 RPD via Google AI Studio
3. **`freellmapi-embeddings`** — Dynamic embedding fallback pool

---

## 📊 Applied Pipeline Optimizations

| Parameter | Configuration / Value | Benefit |
| :--- | :--- | :--- |
| **Input Source** | Single `MASTER_RESUME.txt` + `03-Story-Bank.txt` | Clean entity boundaries & zero duplicates |
| **Primary Chat Model** | `freellmapi-chat` | Zero daily quota blocks |
| **Primary Embedding** | `llama-nemotron-embed-vl-1b-v2` | High-throughput vector embeddings |
| **Concurrency** | `3` concurrent requests | Reduced rate-limiting and stable execution |
| **Chunk Size / Overlap**| `1000` tokens / `150` overlap | Aligned to Markdown section boundaries |
| **Query Caching** | LRU cache (100 queries) | Instant (3-10x faster) repeated lookups |
| **Vector Store** | LanceDB (`output/lancedb`) | Fast embedding storage and retrieval |
| **Resume Generator** | Pydantic V2 Data Models + ReportLab | Type-safe, candidate-agnostic, 2-page ATS PDF generation |
