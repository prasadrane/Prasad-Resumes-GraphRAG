# PROJECT: Prasad-Resumes-GraphRAG

**PURPOSE:** GraphRAG knowledge graph extraction, multi-provider serverless query routing, real-time ATS match scoring, and ATS-tailored resume generation platform.

**GENERATED:** 2026-08-17 | **COMMIT:** `HEAD` | **LEVELS:** Earth, Continent | **GRAPH:** 8,526 nodes · 23,268 edges

---

## 1. Project Overview

**[Documented]** This repository builds and queries a GraphRAG knowledge graph over Prasad Rane's professional experience, skills, and story bank content. It generates rule-based, ATS-tailored raw text and ReportLab PDF resumes with guaranteed page budgets, real-time ATS match scoring, and verifiable citation traces.

**[Inferred]** The application architecture separates into five primary operational pipelines:
1. **Source Ingestion & URL Scraping:** Transforms unstructured resume files, story banks, and live Job Description URLs ([`src/converters`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/converters)) into normalized master data.
2. **Graph Processing & Semantic Extraction:** Leverages Microsoft GraphRAG and post-processing entity resolution ([`src/postprocessing`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/postprocessing)) to construct queryable graph artifacts.
3. **Retrieval & Intent-Routed Querying:** Classifies questions into intents (`LOCAL`, `GLOBAL`, `DRIFT`), executes hybrid vector and graph searches with self-healing guardrails ([`src/query`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/query)), and dispatches across multi-provider LLMs ([`src/gateway`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/gateway)).
4. **ATS Resume Tailoring & Analytics Engine:** Extracts job description keywords via domain ontologies, scores bullet impact, adapts executive summaries, computes composite ATS match scores, and renders precise PDF layouts ([`src/generators`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/generators)).
5. **Observability & Benchmarking:** Tracks end-to-end latency, provider telemetry, and synthetic retrieval quality metrics ([`src/observability`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/observability)).

---

## 2. Subsystem Map (Continent Index)

| # | Subsystem | Purpose | Files | Public Interfaces / Exports | Continent Docs |
|---|-----------|---------|-------|-----------------------------|----------------|
| 1 | `src/config` | Provider configuration, registry & shared LLM constants | 3 | `ProviderConfig`, `get_provider_config`, `llm_constants` | [config/README.md](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/docs/hierarchical/src/config/README.md) |
| 2 | `src/converters` | Document parsing, JD URL scraper & structured resume extraction | 6 | `PDFParser`, `StructuredResumeParser`, `extract_jd_from_url`, `convert_inputs` | [converters/README.md](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/docs/hierarchical/src/converters/README.md) |
| 3 | `src/gateway` | Multi-provider serverless LLM router, circuit breaker & SSE decoder | 6 | `call_serverless_llm`, `CircuitBreaker`, `parse_sse_stream`, `AlibabaProvider`, `GeminiProvider`, `OpenRouterProvider` | [gateway/README.md](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/docs/hierarchical/src/gateway/README.md) |
| 4 | `src/generators` | ATS keyword matcher, ontology, ATS scorer, modular generator & PDF renderer | 12 | `extract_ats_keywords`, `calculate_ats_score`, `SMEOntology`, `ImpactScorer`, `select_tailored_summary`, `render_pdf_resume`, `ResumeData` | [generators/README.md](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/docs/hierarchical/src/generators/README.md) |
| 5 | `src/llm` | High-level LLM abstraction service | 2 | `LLMService`, `get_llm_service` | [llm/README.md](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/docs/hierarchical/src/llm/README.md) |
| 6 | `src/observability` | Structured logging & synthetic benchmark evaluation harness | 1 | `get_logger`, `BenchmarkEvaluator`, `MetricsCollector` | [observability/README.md](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/docs/hierarchical/src/observability/README.md) |
| 7 | `src/postprocessing` | Graph entity resolution & alias normalization | 2 | `EntityResolver`, `ResolutionPair`, `postprocess_graph` | [postprocessing/README.md](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/docs/hierarchical/src/postprocessing/README.md) |
| 8 | `src/proxy` | Local LiteLLM proxy runner | 2 | `LiteLLMRunner`, `start_proxy` | [proxy/README.md](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/docs/hierarchical/src/proxy/README.md) |
| 9 | `src/query` | GraphRAG search engine, static graph reader, guardrails & conversation store | 6 | `GraphRAGEngine`, `IntentClassifier`, `RetrievalGuardrail`, `StaticGraphReader`, `ConversationStore` | [query/README.md](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/docs/hierarchical/src/query/README.md) |
| 10 | `src/shared` | Shared Pydantic API schemas & route handlers | 3 | `QueryRequest`, `ATSSimulationRequest`, `ExtractJDURLRequest`, `ResumeGenerationRequest`, `shared_router` | [shared/README.md](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/docs/hierarchical/src/shared/README.md) |
| 11 | `src/web` | FastAPI application, SSE streams & web UI | 5 | `app`, static assets (`app.js`, `styles.css`, `index.html`) | [web/README.md](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/docs/hierarchical/src/web/README.md) |

---

## 3. Primary API Routes

**[Documented]** The application exposes the following FastAPI / Serverless endpoints:

| Method | Route Path | Purpose | Handler Subsystem |
|:---|:---|:---|:---|
| `GET` | `/` | Web user interface entry point | `src/web` |
| `GET` | `/api/health` | Service health check | `src/web` |
| `POST` | `/api/chat-stream` | Real-time SSE query streaming with self-healing guardrails | `src/query` + `src/gateway` |
| `POST` | `/api/query` | Synchronous GraphRAG question answering | `src/query` + `src/gateway` |
| `POST` | `/api/ats-score` | Real-time ATS match score, keyword breakdown, and suggestions | `src/generators` + `src/shared` |
| `POST` | `/api/extract-jd-url` | Scrape and extract normalized JD body and metadata from URL | `src/converters` + `src/shared` |
| `POST` | `/api/generate` | Synchronous ATS-tailored resume generation | `src/generators` |
| `POST` | `/api/generate-stream`| Streaming ATS resume synthesis | `src/generators` + `src/web` |
| `POST` | `/api/keywords` | Extract ATS keywords from job description | `src/generators` |
| `POST` | `/api/render_pdf` | Compile raw resume markdown to downloadable PDF | `src/generators` |
| `GET` | `/api/default-resume` | Fetch default parsed master resume structure | `src/generators` |
| `POST` | `/api/save-edit` | Save user inline resume edits | `src/shared` |
| `GET` | `/api/history` | Retrieve session chat / resume history | `src/query` |
| `GET` | `/api/metrics` | In-process latency & call counters | `src/metrics` / `src/observability` |
| `GET` | `/api/pdf/{company}/{filename}` | Static PDF download route | `src/web` |

---

## 4. Operational Entry Points

| Script / Module | Entry Command | Responsibility |
|:---|:---|:---|
| [`src/cli.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/cli.py) | `python src/cli.py {convert,index,query,generate,benchmark,proxy,ui}` | Unified repository CLI dispatcher |
| [`scripts/run_litellm.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/scripts/run_litellm.py) | `python scripts/run_litellm.py` | Local LiteLLM proxy runner (port 8002) |
| [`scripts/convert_inputs.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/scripts/convert_inputs.py) | `python scripts/convert_inputs.py` | Source file normalization to `input/` |
| [`scripts/postprocess_graph.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/scripts/postprocess_graph.py) | `python scripts/postprocess_graph.py` | Post-index graph deduplication & alias resolution |
| [`scripts/query.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/scripts/query.py) | `python scripts/query.py --local/--global "..."` | Direct knowledge graph query wrapper |
| [`scripts/benchmark_eval.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/scripts/benchmark_eval.py) | `python scripts/benchmark_eval.py` | Synthetic benchmark retrieval evaluation harness |
| [`scripts/generate_architecture_diagram.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/scripts/generate_architecture_diagram.py) | `python scripts/generate_architecture_diagram.py` | Programmatic SVG architecture generator with geometric assertions and Playwright renderer |

---

## 5. Cross-Cutting Architectural Patterns

### Multi-Provider Failover & Circuit Breakers (`src/gateway`)
**[Documented]** The system avoids single-vendor reliance by implementing a fallback chain (`_try_chain`) across Alibaba Cloud Qwen (`qwen3.7-plus`), Google Gemini AI Studio (`gemini-2.5-flash-lite`), and OpenRouter (`openai/text-embedding-3-small`, `freellmapi-chat`). Each provider is wrapped in an isolated `CircuitBreaker` to prevent cascade failures on rate limits.

### Modular Resume Generation Architecture (`src/generators`)
**[Documented]** The resume tailoring engine follows strict SRP division across `domain_matcher.py` (taxonomy selection), `prompt_builder.py` (single-call LLM prompt formatting), `text_formatter.py` (ATS $<20\%$ character bold constraints), `ats_scorer.py` (real-time scoring), and `resume_generator.py` (clean orchestration).

### Self-Healing Retrieval Guardrails (`src/query`)
**[Documented]** Pre-synthesis retrieval guardrails inspect retrieved context density. If token density is below threshold (< 30 tokens) or entity overlap is sparse, the engine automatically escalates retrieval mode from `local` to `drift` or `global` before answering.
