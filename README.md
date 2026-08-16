# Prasad Resumes — GraphRAG Knowledge Graph, Talent Analytics & Tailored Resume Generator

A production-grade, serverless-ready GraphRAG knowledge graph engine, automated ATS resume generator, and conversational talent analytics platform built over Prasad Rane's master resumes and story bank.

---

## 🏛️ System Architecture & Data Flow

![Architecture & System Data Flow](docs/architecture_diagram.svg)

The platform operates across four decoupled layers sharing a unified knowledge and multi-provider LLM substrate:

1. **Multimodal User Input & Ingestion:** Ingests master resumes (`input/MASTER_RESUME.txt`) and 85KB narrative story banks into GraphRAG Parquet tables and LanceDB vector stores. Supports real-time text and Web Speech API voice queries.
2. **Intent Routing & Knowledge Layer:** Zero-shot intent classifier (6 intents) and SME Technology Ontology (`SMEOntology`) with synonym normalization and child-skill query expansion.
3. **Guardrails & LLM Gateway Layer:** Self-Healing Retrieval Guardrail (`RetrievalGuardrail`) inspecting pre-synthesis token density and entity overlap with autonomous fallback escalation (`local` $\rightarrow$ `drift` $\rightarrow$ `global`), routed through a multi-provider LLM Gateway (`Alibaba Cloud`, `OpenRouter`, `Google Gemini REST`).
4. **Multimodal Presentation & ATS Export:** Real-time token streaming with audio briefing synthesis (`SpeechSynthesis`), in-memory markdown editor, and a standard 2-page ATS PDF compilation engine.

---

## 🚀 Key Innovations & Features

### 1. SME Technology Ontology & Synonym Expansion
- **Canonical Normalization:** Normalizes variations like `k8s` $\rightarrow$ `kubernetes`, `postgres` $\rightarrow$ `postgresql`, `py-torch` $\rightarrow$ `pytorch`, `fast-api` $\rightarrow$ `fastapi`.
- **Bidirectional Skill Hierarchy:** Maps high-level JD requirements (e.g. *Event-Driven Architecture*, *Deep Learning*) to concrete master resume tools (*Kafka*, *PyTorch*, *AWS ECS Fargate*).

### 2. Action-Verb Impact Scoring & Recency Decay (EEOC / EU AI Act Compliant)
- **Bloom's Taxonomy Verb Tiering:** Scores candidate accomplishments using deterministic action-verb tiers (Tier 1 = $1.0$, Tier 2 = $0.7$, Tier 3 = $0.4$).
- **Quantified Impact Detection:** Detects and rewards business metrics (`70% latency reduction`, `$400K cost savings`, `10M requests`).
- **Exponential Recency Decay:** Prioritizes current skills via $e^{-\lambda \Delta t}$ ($\lambda = 0.15$) while maintaining full career history.

### 3. Self-Healing Retrieval Guardrail Agent
- **Pre-Synthesis Quality Inspection:** Checks context sufficiency and entity overlap before calling the LLM.
- **Autonomous Mode Escalation:** If initial local retrieval has low token density ($<30$ tokens), automatically escalates across `local` $\rightarrow$ `drift` $\rightarrow$ `global` and returns an execution trace badge in the UI.

### 4. Synthetic RAG Benchmark Evaluation Harness
- **Defensible Quantitative Tracking:** Evaluates retrieval performance across Context Precision, Context Recall, Faithfulness, and Latency.
- **CLI Runner:** Run `python src/cli.py benchmark` to execute test suites and export Markdown reports to `output/benchmark_report.md`.

### 5. Multimodal Voice Assistant & Interactive Web UI
- **Voice Query Input:** Speak naturally into the search bar using browser Web Speech API.
- **Audio Briefings:** Click speaker icons on answers for synthesized text-to-speech audio summaries.
- **In-Memory Markdown & PDF Preview:** Edit raw resume content live and re-render standard ATS PDFs in one click without losing page budget.

---

## 📚 Hierarchical Documentation

Following Google Maps-style hierarchical documentation principles (**Earth → Continent → Country → City → Street**):

- 🌍 **[Master Architecture Index (Earth Level)](docs/hierarchical/README.md)**
- 🏢 **[src/gateway (Multi-Provider LLM Routing)](docs/hierarchical/src/gateway/README.md)**
- 🔍 **[src/query (GraphRAG Engine & Guardrails)](docs/hierarchical/src/query/README.md)**
- 📄 **[src/generators (Ontology, Scoring & PDF Renderer)](docs/hierarchical/src/generators/README.md)**
- 📥 **[src/converters (Ingestion & Normalization)](docs/hierarchical/src/converters/README.md)**
- 📊 **[src/observability (Telemetry & Benchmarking)](docs/hierarchical/src/observability/README.md)**
- 🌐 **[src/web (FastAPI Server & Voice UI)](docs/hierarchical/src/web/README.md)**
- 📖 **[Comprehensive How-It-Works Walkthrough](docs/HOW-IT-WORKS.md)**
- 📑 **[Strategic Architectural Blueprint](docs/STRATEGIC_ARCHITECTURAL_BLUEPRINT.md)**
- 📋 **[Engineering Progress Tracker](docs/PROGRESS_TRACKER.md)**

---

## ⚙️ Configuration & Environment Variables

Create a `.env` file in the project root:

```env
# Alibaba Cloud Token Plan (Primary LLM for chat & resume generation)
ALIBABA_API_KEY=sk-sp-your_alibaba_token_plan_key

# OpenRouter API (Primary embedding model & chat fallback)
OPENROUTER_API_KEY=sk-or-v1-your_openrouter_api_key

# Google Gemini AI Studio API (High-quota fallback & GraphRAG indexer)
GEMINI_API_KEY=your_gemini_api_key
GRAPHRAG_API_KEY=your_gemini_api_key

# Optional: Provider Registry Routing
CHAT_PROVIDER=alibaba          # alibaba | openrouter | gemini
RESUME_PROVIDER=alibaba        # alibaba | openrouter | gemini
EMBEDDING_PROVIDER=openrouter   # openrouter | gemini
```

---

## 💻 Quick Start & Commands

### 1. Activate Environment
```powershell
.\venv\Scripts\Activate.ps1
```

### 2. Launch Minimalist Web UI
```powershell
python src/cli.py ui
# Runs `vercel dev` under the hood on http://localhost:3000
```

### 3. Generate Tailored Resume via CLI
```powershell
python src/cli.py generate --company <Company_Name> --jd-file <Path_To_JD.txt>
```

### 4. Query Knowledge Graph via CLI
```powershell
python src/cli.py query --mode local "What AWS technologies did Prasad use?"
```

### 5. Run Synthetic Benchmark Evaluation
```powershell
python src/cli.py benchmark --mode all --output output/benchmark_report.md
```

### 6. Run Unit Test Suite
```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
# 367/367 passing tests (100% pass rate)
```

---

## 🌐 API Reference

| Method | Endpoint | Handler | Description |
|---|---|---|---|
| `GET` | `/` | `index_endpoint` | Material Design 3 single-page web UI |
| `POST` | `/api/generate` | `generate_resume_endpoint` | Tailors raw markdown & PDF resume against target JD |
| `POST` | `/api/render_pdf` | `render_pdf_endpoint` | Compiles raw markdown into standard ATS PDF |
| `POST` | `/api/save-edit` | `save_edit_endpoint` | Saves edited markdown and re-renders PDF |
| `POST` | `/api/query` | `query_endpoint` | Synchronous GraphRAG Q&A query |
| `POST` | `/api/chat-stream` | `chat_stream_endpoint` | SSE token streaming with guardrail traces |
| `GET` | `/api/default-resume` | `default_resume_endpoint` | Retrieves pre-compiled master resume and PDF |

---

## 🚀 Deployment Options

### Option A: Oracle Cloud (OCI Always Free) — Automated CI/CD (Recommended)
- **Zero Cold Starts & Dedicated 24GB RAM:** Runs full GraphRAG indexing, LiteLLM proxy, and FastAPI 24/7 at $0/month.
- **Automated CI/CD:** Powered by `.github/workflows/deploy-oci.yml` — every `git push` runs tests and updates the VM automatically via SSH + Docker Compose.
- 📖 **[Oracle Cloud Automated Deployment Guide](docs/ORACLE_CLOUD_DEPLOYMENT.md)**

### Option B: Vercel Serverless (Free Tier)
- **Zero-Server Maintenance:** Deploy frontend & serverless API in one click:
  ```powershell
  vercel --prod
  ```
- Uses `api/index.py` with in-memory `StaticGraphReader` (<2ms retrieval) and `src/gateway` REST streaming.

---

## 🔒 Legal & Algorithmic Compliance

- **EEOC & Uniform Guidelines Compliant:** Completely candidate-agnostic, strictly skill-and-experience indexed without demographic profiling.
- **EU AI Act Transparency:** Deterministic, inspectable Bloom's Taxonomy scoring replaces opaque black-box GNN ranking.
