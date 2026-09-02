# Prasad Resumes — GraphRAG Knowledge Graph, Talent Analytics & Tailored Resume Generator

A production-grade, serverless-ready GraphRAG knowledge graph engine, automated ATS resume generator, real-time match scoring dashboard, and conversational talent analytics platform built over Prasad Rane's master resumes and story bank.

---

## 🏛️ System Architecture & Data Flow

![Architecture & System Data Flow](docs/architecture_diagram.png)

The platform operates across five decoupled layers sharing a unified knowledge and multi-provider LLM substrate:

1. **Multimodal User Ingestion & URL Scraper:** Ingests master resumes (`input/MASTER_RESUME.txt`), 85KB narrative story banks, and public job posting URLs (`src/converters/jd_extractor.py`). Supports real-time text and Web Speech API voice queries.
2. **Evaluator Agent In-The-Loop:** 2-Phase autonomous state machine (`src/evaluator`) executing pre-generation feasibility checks ("Apply vs. Do Not Apply"), story-grounded tailoring blueprints, anti-hallucination auditing, 4-dimension scoring, and closed-loop multi-turn auto-refinement.
3. **Intent Routing, SME Ontology & ATS Scoring:** Zero-shot intent classifier (8 intents), SME Technology Ontology (`SMEOntology` with 120+ skill taxonomies), and a real-time ATS match scoring engine (`ats_scorer.py`).
4. **Resume Tailoring & Story Context Orchestration:** Modular Single Responsibility (SRP) pipeline splitting domain matching (`domain_matcher.py`), single-call prompt construction (`prompt_builder.py`), and ATS markdown formatting (`text_formatter.py`).
5. **Multi-Provider LLM Gateway Layer:** Self-Healing Retrieval Guardrail (`RetrievalGuardrail`) with autonomous fallback escalation (`local` $\rightarrow$ `drift` $\rightarrow$ `global`), routed through a multi-provider LLM Gateway (`Alibaba Cloud qwen3.7-plus`, `Google Gemini AI Studio 2.5-flash-lite`, `OpenRouter free pool`).
6. **Multimodal Presentation & ATS Export:** Real-time SSE token streaming, in-memory markdown editor, and a standard 2-page ATS PDF compilation engine using ReportLab.

---

## 🚀 Key Innovations & Features

### 1. Fully Agentic Evaluator In-The-Loop (`src/evaluator`)
- **Pre-Generation Feasibility Check:** Ingests JD text or live URL, calculates dynamic match %, separates **Fillable Gaps** (grounded in Story Bank) vs **Unfillable Gaps**, and issues an "Apply with Strategy" or `"DO_NOT_APPLY"` verdict before generation.
- **Truthfulness & Anti-Hallucination Auditor:** Tokenizes and audits all generated resume bullets against the per-company story-bank corpora in `input/` (e.g. `input/Rocket-Mortgage.txt`) and `input/MASTER_RESUME.txt` to guarantee 0 fabricated claims or hallucinated tools.
- **4-Dimension Scorecard:** Evaluates 1) ATS Keyword Match %, 2) Story Grounding (0 unbacked claims), 3) Format & Page Budget Compliance (<20% bolding cap, 2-page length), and 4) Cover Letter Relevance.
- **Autonomous Multi-Turn Refinement:** Automatically generates surgical delta critiques and refines resume and cover letter content in a closed loop (capped at max turns).

### 2. Real-Time ATS Match Scorer & Actionable Analytics
- **Composite Match Scoring:** Computes holistic 0–100% match scores based on keyword coverage, experience depth, and quantitative metrics.
- **Section-by-Section Breakdown:** Visualizes match percentages for Skills, Experience, and Executive Summary.
- **Actionable Suggestions:** Provides direct suggestions (e.g. *Add 'Kafka' to Experience bullets to prove hands-on impact*).

### 3. Automated Job Description Extraction from URL
- **Multi-Portal Scraping:** Automatically extracts and normalizes job descriptions from LinkedIn, Greenhouse, Lever, Indeed, and career portals.
- **CLI & Web Integration:** Run `python src/cli.py generate --jd-url <URL>` to auto-infer company/role, tailor the resume, and report ATS scores.

### 4. SME Technology Ontology & Synonym Expansion
- **Canonical Normalization:** Normalizes variations like `k8s` $\rightarrow$ `kubernetes`, `postgres` $\rightarrow$ `postgresql`, `fast-api` $\rightarrow$ `fastapi`.
- **Bidirectional Skill Hierarchy:** Maps high-level JD requirements (e.g. *Event-Driven Architecture*, *Deep Learning*) to concrete master resume tools (*Kafka*, *PyTorch*, *AWS ECS Fargate*).

### 5. Action-Verb Impact Scoring & Recency Decay (EEOC / EU AI Act Compliant)
- **Bloom's Taxonomy Verb Tiering:** Scores candidate accomplishments using deterministic action-verb tiers (Tier 1 = $1.0$, Tier 2 = $0.7$, Tier 3 = $0.4$).
- **Quantified Impact Detection:** Detects and rewards business metrics (`70% latency reduction`, `$400K cost savings`, `10M requests`).
- **Exponential Recency Decay:** Prioritizes current skills via $e^{-\lambda \Delta t}$ ($\lambda = 0.15$) while maintaining full career history.

### 6. Self-Healing Retrieval Guardrail Agent
- **Pre-Synthesis Quality Inspection:** Checks context sufficiency and entity overlap before calling the LLM.
- **Autonomous Mode Escalation:** If initial local retrieval has low token density ($<30$ tokens), automatically escalates across `local` $\rightarrow$ `drift` $\rightarrow$ `global` and returns an execution trace badge in the UI.

### 7. Synthetic RAG Benchmark Evaluation Harness
- **Defensible Quantitative Tracking:** Evaluates retrieval performance across Context Precision, Context Recall, Faithfulness, and Latency.
- **CLI Runner:** Run `python src/cli.py benchmark` to execute test suites and export Markdown reports to `output/benchmark_report.md`.

---

## 📚 Hierarchical Documentation

Following Google Maps-style hierarchical documentation principles (**Earth → Continent → Country → City → Street**):

- 🌍 **[Master Architecture Index (Earth Level)](docs/hierarchical/README.md)**
- ⚙️ **[src/config (Provider Registry & Constants)](docs/hierarchical/src/config/README.md)**
- 📥 **[src/converters (Ingestion & JD URL Scraper)](docs/hierarchical/src/converters/README.md)**
- 🏢 **[src/gateway (Multi-Provider LLM Routing)](docs/hierarchical/src/gateway/README.md)**
- 📄 **[src/generators (Ontology, ATS Scorer, Modular Tailorer & PDF Renderer)](docs/hierarchical/src/generators/README.md)**
- 🤖 **[src/llm (LLM Service Abstraction)](docs/hierarchical/src/llm/README.md)**
- 📊 **[src/observability (Telemetry & Benchmarking)](docs/hierarchical/src/observability/README.md)**
- 🔗 **[src/postprocessing (Graph Deduplication & Entity Resolution)](docs/hierarchical/src/postprocessing/README.md)**
- 🔄 **[src/proxy (LiteLLM Proxy Runner)](docs/hierarchical/src/proxy/README.md)**
- 🔍 **[src/query (GraphRAG Engine & Guardrails)](docs/hierarchical/src/query/README.md)**
- 📦 **[src/shared (API Schemas & Shared Router)](docs/hierarchical/src/shared/README.md)**
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

### 3. Unified All-In-One Agentic Tailoring (`tailor`)
```powershell
# Pre-generation feasibility & gap analysis only:
python src/cli.py tailor --company "GitHub" --jd examples/github_billing_jd.txt --check-only

# End-to-end autonomous agentic tailoring (pre-check -> draft -> 4D audit -> auto-refinement -> PDF builds):
python src/cli.py tailor --company "Stripe" --jd examples/github_billing_jd.txt

# Directly from a live Job Posting URL:
python src/cli.py tailor --company "Stripe" --jd "https://jobs.stripe.com/senior-backend-engineer"
```

### 4. Standalone Resume Generation via CLI
```powershell
# Direct generation:
python src/cli.py generate --company Google --jd-file path/to/jd.txt
```

### 5. Query Knowledge Graph via CLI
```powershell
python src/cli.py query --mode local "What AWS technologies did Prasad use?"
```

### 6. Run Synthetic Benchmark Evaluation
```powershell
python src/cli.py benchmark --mode all --output output/benchmark_report.md
```

### 7. Run Complete Test Suite
```powershell
.\venv\Scripts\python.exe -m pytest tests/
# 455 passed, 0 failures (100% pass rate)
```

---

## 🌐 API Reference

| Method | Endpoint | Handler | Description |
|---|---|---|---|
| `GET` | `/` | `index_endpoint` | Material Design 3 single-page web UI |
| `POST` | `/api/generate` | `generate_resume_endpoint` | Tailors raw markdown & PDF resume against target JD |
| `POST` | `/api/ats-score` | `ats_score_endpoint` | Calculates real-time ATS match score, keyword breakdown, and suggestions |
| `POST` | `/api/extract-jd-url`| `extract_jd_url_endpoint` | Scrapes and extracts normalized JD body from public web URLs |
| `POST` | `/api/render_pdf` | `save_edit_endpoint` | Compiles raw markdown into standard ATS PDF |
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
