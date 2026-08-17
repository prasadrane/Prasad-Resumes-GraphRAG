# PROJECT: Prasad-Resumes-GraphRAG

**PURPOSE:** GraphRAG knowledge graph extraction, multi-provider serverless query routing, and ATS-tailored resume generation platform.

**GENERATED:** 2026-08-17 | **COMMIT:** `1a7a581c` | **LEVELS:** Earth, Continent | **GRAPH:** 4,798 nodes · 17,003 edges

---

## 1. Project Overview

**[Documented]** This repository builds and queries a GraphRAG knowledge graph over Prasad Rane's professional experience, skills, and story bank content. It generates rule-based, ATS-tailored raw text and ReportLab PDF resumes with guaranteed page budgets and verifiable citation traces.

**[Inferred]** The application architecture separates into four primary operational pipelines:
1. **Source Ingestion & Conversion:** Transforms unstructured resume and story bank documents into normalized master data ([`src/converters`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/converters)).
2. **Graph Processing & Semantic Extraction:** Leverages Microsoft GraphRAG and post-processing entity resolution ([`src/postprocessing`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/postprocessing)) to construct queryable graph artifacts.
3. **Retrieval & Intent-Routed Querying:** Classifies questions into intents (`LOCAL`, `GLOBAL`, `DRIFT`), executes hybrid vector and graph searches with self-healing guardrails ([`src/query`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/query)), and dispatches across multi-provider LLMs ([`src/gateway`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/gateway)).
4. **ATS Resume Tailoring Engine:** Extracts job description keywords via domain ontologies, scores bullet impact, adapts executive summaries, and renders precise PDF layouts ([`src/generators`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/generators)).

---

## 2. Subsystem Map (Continent Index)

| # | Subsystem | Purpose | Files | Public Interfaces / Exports | Continent Docs |
|---|-----------|---------|-------|-----------------------------|----------------|
| 1 | `src/config` | Provider configuration & registry | 2 | `ProviderConfig`, `get_provider_config` | [config/README.md](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/docs/hierarchical/src/config/README.md) |
| 2 | `src/converters` | Document parsing & structured resume extraction | 5 | `PDFParser`, `StructuredResumeParser`, `convert_inputs` | [converters/README.md](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/docs/hierarchical/src/converters/README.md) |
| 3 | `src/gateway` | Multi-provider serverless LLM router & circuit breaker | 7 | `call_serverless_llm`, `CircuitBreaker`, `AlibabaProvider`, `GeminiProvider`, `OpenRouterProvider` | [gateway/README.md](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/docs/hierarchical/src/gateway/README.md) |
| 4 | `src/generators` | ATS keyword matcher, ontology, scoring & PDF renderer | 8 | `extract_ats_keywords`, `SMEOntology`, `ImpactScorer`, `render_resume_pdf`, `ResumeData` | [generators/README.md](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/docs/hierarchical/src/generators/README.md) |
| 5 | `src/llm` | High-level LLM abstraction service | 2 | `LLMService`, `get_llm_service` | [llm/README.md](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/docs/hierarchical/src/llm/README.md) |
| 6 | `src/observability` | Structured logging & benchmark evaluation harness | 1 | `get_logger`, `BenchmarkEvaluator`, `MetricsCollector` | [observability/README.md](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/docs/hierarchical/src/observability/README.md) |
| 7 | `src/postprocessing` | Graph entity resolution & alias normalization | 2 | `EntityResolver`, `ResolutionPair`, `postprocess_graph` | [postprocessing/README.md](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/docs/hierarchical/src/postprocessing/README.md) |
| 8 | `src/proxy` | Local LiteLLM proxy runner | 2 | `LiteLLMRunner`, `start_proxy` | [proxy/README.md](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/docs/hierarchical/src/proxy/README.md) |
| 9 | `src/query` | GraphRAG search engine, guardrails & conversation store | 7 | `GraphRAGEngine`, `IntentClassifier`, `RetrievalGuardrail`, `TTLCache`, `ConversationStore` | [query/README.md](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/docs/hierarchical/src/query/README.md) |
| 10 | `src/shared` | Shared Pydantic API schemas & route handlers | 3 | `QueryRequest`, `ResumeGenerationRequest`, `SaveEditRequest`, `register_routes` | [shared/README.md](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/docs/hierarchical/src/shared/README.md) |
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
| [`evaluation/evaluate_retrieval.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/evaluation/evaluate_retrieval.py) | `python evaluation/evaluate_retrieval.py` | Synthetic benchmark retrieval evaluation harness |

---

## 5. Cross-Cutting Architectural Patterns

### Multi-Provider Failover & Circuit Breakers (`src/gateway`)
**[Documented]** The system avoids single-vendor reliance by implementing a fallback chain (`_try_chain`) across Alibaba Cloud Qwen (`qwen3.6/3.7`), Google Gemini AI Studio (`gemini-2.5-flash-lite`, `gemini-3.1-flash-lite`), and OpenRouter (`openai/text-embedding-3-small`). Each provider is wrapped in an isolated `CircuitBreaker` to prevent cascade failures on rate limits.

### Deterministic Action-Verb Impact Scoring (`src/generators`)
**[Documented]** Candidate bullet points are ranked using a closed-form formula combining Bloom's taxonomy action-verb tiers (Tier 1 = 1.0, Tier 2 = 0.7, Tier 3 = 0.4), detected quantitative metric multipliers, and exponential recency decay ($e^{-\lambda \Delta t}$).

### Self-Healing Retrieval Guardrails (`src/query`)
**[Documented]** Pre-synthesis retrieval guardrails inspect retrieved context density. If token density is below threshold (< 30 tokens) or entity overlap is sparse, the engine automatically escalates retrieval mode from `local` to `drift` or `global` before answering.
