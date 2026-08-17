# How It Works: Knowledge Graph, Embeddings, Multi-Agent Guardrails & LLMs in This Project

This document details how **Vector Embeddings**, **Microsoft GraphRAG**, **SME Technology Ontologies**, **Action-Verb Impact Scoring**, **Self-Healing Guardrails**, and **Multi-Provider LLMs** operate together in the Prasad Resumes GraphRAG platform.

---

## Table of Contents

1. [Core Architectural Concepts](#core-architectural-concepts)
2. [SME Technology Ontology & Taxonomy](#sme-technology-ontology--taxonomy)
3. [Action-Verb Impact Scoring & Recency Decay](#action-verb-impact-scoring--recency-decay)
4. [Conversational Q&A & Self-Healing Guardrail Flow](#conversational-qa--self-healing-guardrail-flow)
5. [ATS Resume Tailoring Flow](#ats-resume-tailoring-flow)
6. [Graph Post-Processing & Entity Resolution](#graph-post-processing--entity-resolution)
7. [Synthetic Benchmark Evaluation Harness](#synthetic-benchmark-evaluation-harness)
8. [Multimodal Voice Assistant & UI](#multimodal-voice-assistant--ui)
9. [Hierarchical Subsystems & File Reference](#hierarchical-subsystems--file-reference)

---

## 1. Core Architectural Concepts

### 1. Vector Embeddings
- **[Documented]** Converts textual questions and resume text units into dense 1536-dimensional float vectors that capture semantic meaning.
- **[Inferred]** Questions and resume text units are indexed in **LanceDB**. When a query arrives, vector distance retrieves the most semantically relevant text units.

### 2. Microsoft GraphRAG (Knowledge Graph)
- **[Documented]** Connects entities (`Prasad Rane`, `AWS ECS Fargate`, `Rocket Mortgage`, `Kafka`, `FastAPI`) via rich relationships.
- **[Inferred]** Indexes master resumes and the 85KB story bank into entities, relationships, text units, and hierarchical community reports stored in Parquet tables.

### 3. Serverless Multi-Provider LLM Gateway
- **[Documented]** Generates answers and adapts executive summaries without vendor lock-in.
- **[Inferred]** Uses `facade.py` to route across **Alibaba Cloud Token Plan** (`qwen3.6/3.7`), **OpenRouter** (`openai/text-embedding-3-small`), and direct **Google Gemini AI Studio API** with automatic failover (`_try_chain`) and circuit breaking.

---

## 2. SME Technology Ontology & Taxonomy

**File:** [`src/generators/sme_ontology.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/generators/sme_ontology.py)

**[Documented]** Candidate resumes rarely match job descriptions verbatim. A JD asking for *"Event-Driven Architecture"* or *"Deep Learning Frameworks"* requires semantic bridge matching to *"Kafka"* or *"PyTorch"*.

```mermaid
graph TD
    JD["JD Keyword: 'Deep Learning'"] --> Ont[SMEOntology Engine]
    Ont --> Syn["Synonyms: dl, deep learning"]
    Ont --> Children["Child Skills: PyTorch, TensorFlow, Keras"]
    Ont --> Parents["Parent Domains: AI/ML, Data Science"]
    Children --> Match["Matches Prasad's Master Resume Experience"]
```

### Key Capabilities:
- **[Documented] Synonym Normalization:** Canonicalizes variations like `k8s` $\rightarrow$ `kubernetes`, `postgres` $\rightarrow$ `postgresql`, `py-torch` $\rightarrow$ `pytorch`, `fast-api` $\rightarrow$ `fastapi`.
- **[Documented] Category-to-Children Expansion:** Expands high-level requirements into concrete tools.
- **[Documented] Bidirectional Relatedness Check:** Verifies whether two technical terms belong to the same technical taxonomy.

---

## 3. Action-Verb Impact Scoring & Recency Decay

**File:** [`src/generators/scoring.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/generators/scoring.py)

**[Documented]** To comply with **EEOC** and **EU AI Act** requirements for explainable candidate evaluation, ranking uses a deterministic, parameterized formula rather than black-box graph embeddings:

$$W_{(c,s)} = \alpha \cdot \text{DurationScore} + \beta \cdot \text{RecencyScore} + \gamma \cdot \text{ImpactScore}$$

```mermaid
flowchart LR
    Bullet["'Architected AWS ECS pipeline reducing query latency by 70%'"] --> Scorer[ImpactScorer]
    Scorer --> V["Verb Tier 1: Architected (1.00)"]
    Scorer --> M["Metric Bonus: 70% (+0.20)"]
    Scorer --> R["Recency: 2026 Reference (1.00)"]
    V & M & R --> Final["Final Score: 1.000 (Rank #1)"]
```

### Scoring Components:
1. **[Documented] Bloom's Taxonomy / Action-Verb Tiering:**
   - **Tier 1 ($1.0$):** *Architected, Spearheaded, Engineered, Orchestrated, Pioneered, Founded*
   - **Tier 2 ($0.7$):** *Implemented, Developed, Built, Optimized, Migrated, Scaled, Delivered*
   - **Tier 3 ($0.4$):** *Maintained, Supported, Assisted, Monitored, Updated, Documented*
2. **[Documented] Quantified Impact Detection:** Detects percentages (`70%`), currency (`$400K`), latency improvements (`50ms`, `3.5x`), and scale indicators (`10M requests`).
3. **[Documented] Exponential Recency Decay:** Applies $e^{-\lambda \cdot \Delta t}$ with $\lambda = 0.15$, prioritizing recent achievements while preserving full career history.

---

## 4. Conversational Q&A & Self-Healing Guardrail Flow

**[Documented]** When a user submits a question (via text or speech), the system follows this multi-stage execution pipeline:

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Web as FastAPI Web Server
    participant Router as IntentClassifier
    participant Engine as GraphRAGEngine
    participant Guardrail as RetrievalGuardrail
    participant Gateway as LLM Gateway Facade

    User->>Web: POST /api/chat-stream (Question)
    Web->>Router: classify_with_details(query)
    Router-->>Engine: Mode (local/drift/global) + Extracted Entities
    Engine->>Engine: retrieve(query, mode)
    Engine->>Guardrail: evaluate_context(query, context, entities)
    alt Context Density is Low (< 30 tokens)
        Guardrail-->>Engine: Action: fallback_drift / fallback_global
        Engine->>Engine: Escalate Retrieval Mode (Self-Healing)
    end
    Engine->>Gateway: call_serverless_llm_stream(system_prompt, query)
    Gateway-->>Web: SSE Tokens Stream
    Web-->>User: Live Markdown Answer + Trace Badge
```

---

## 5. ATS Resume Tailoring Flow

**[Documented]** When tailoring a resume for a specific target company:

1. **ATS Keyword Extraction:** `ats_matcher.extract_ats_keywords(jd_text, expand_ontology=True)` extracts direct keywords and expands domain terms via `SMEOntology`.
2. **Candidate Bullet Ranking:** `rank_experience_bullets()` scores every bullet from `MASTER_RESUME.txt` using `ImpactScorer`.
3. **LLM Executive Summary Synthesis:** Dynamically adapts domain summaries (*AI/LLM-Forward*, *Cloud-Forward*, *Platform-Forward*, *Security-Forward*) to mirror JD priorities.
4. **Precision Keyword Bolding:** Highlights JD-matched technical terms while strictly maintaining $<20\%$ bold character ratio.
5. **ReportLab PDF Rendering:** Compiles `raw_resume.txt` into `Prasad_Rane_Resume.pdf`, enforcing tight margins (`0.55"` left/right, `0.45"` top/bottom), KeepTogether job blocks, and a strict 2-page budget guarantee.

---

## 6. Graph Post-Processing & Entity Resolution

**File:** [`src/postprocessing/entity_resolver.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/postprocessing/entity_resolver.py)

**[Documented]** Graph extraction models frequently extract aliases of the same entity (e.g., `Prasad Rane` vs. `Prasad Sudhir Rane`, or `AWS ECS` vs. `Amazon Elastic Container Service`).
- **Union-Find Deduplication:** Identifies synonym clusters and merges disconnected nodes into unified canonical entities.
- **Edge Rewiring:** Automatically updates source/target references across relationship tables to eliminate orphan graph edges.

---

## 7. Synthetic Benchmark Evaluation Harness

**File:** [`src/observability/benchmark_eval.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/observability/benchmark_eval.py)

**[Documented]** To measure retrieval accuracy quantitatively:
- **Metrics Tracked:**
  - **Context Precision:** $\frac{|\text{Retrieved Entities} \cap \text{Expected Entities}|}{|\text{Expected Entities}|}$
  - **Context Recall:** Token overlap between ground-truth reference facts and retrieved context.
  - **Faithfulness:** Ratio of generated claims directly supported by retrieved context.
  - **Execution Latency:** Retrieval and guardrail evaluation latency in milliseconds.
- **Execution Command:**
  ```powershell
  python src/cli.py benchmark --mode all
  ```
  Generates automated evaluation reports at [`output/benchmark_report.md`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/output/benchmark_report.md).

---

## 8. Multimodal Voice Assistant & UI

- **Speech-to-Text (Voice Queries):** Click the microphone button in the web search bar to speak questions. Uses the browser's `SpeechRecognition` API with real-time transcription and automatic submission.
- **Text-to-Speech (Audio Briefings):** Click the speaker button on any assistant answer to hear a synthesized audio briefing via `SpeechSynthesis`.
- **Reasoning & Guardrail Trace:** Expandable badge under assistant answers displaying query intent, retrieved graph entities, and self-healing recovery traces.

---

## 9. Hierarchical Subsystems & File Reference

| Subsystem | Continent Doc | Primary Files | Key Responsibilities |
| :--- | :--- | :--- | :--- |
| **Config** | [Continent Doc](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/docs/hierarchical/src/config/README.md) | [`src/config/providers.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/config/providers.py) | Provider registry and settings resolution `[Documented]` |
| **Converters** | [Continent Doc](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/docs/hierarchical/src/converters/README.md) | [`src/converters/pdf_parser.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/converters/pdf_parser.py), [`resume_structured_parser.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/converters/resume_structured_parser.py) | PDF text extraction and master resume structuring `[Documented]` |
| **Gateway** | [Continent Doc](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/docs/hierarchical/src/gateway/README.md) | [`src/gateway/facade.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/gateway/facade.py), [`circuit_breaker.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/gateway/circuit_breaker.py) | Multi-provider failover (`_try_chain`) & circuit breaker `[Documented]` |
| **Generators** | [Continent Doc](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/docs/hierarchical/src/generators/README.md) | [`src/generators/ats_matcher.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/generators/ats_matcher.py), [`pdf_renderer.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/generators/pdf_renderer.py) | ATS matching, scoring, bolding caps & ReportLab PDF compilation `[Documented]` |
| **LLM** | [Continent Doc](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/docs/hierarchical/src/llm/README.md) | [`src/llm/service.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/llm/service.py) | Application-level LLM client wrapper `[Documented]` |
| **Observability** | [Continent Doc](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/docs/hierarchical/src/observability/README.md) | [`src/metrics.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/metrics.py), [`src/observability/__init__.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/observability/__init__.py) | Structured logging, latency metrics & benchmark evaluation `[Documented]` |
| **Postprocessing**| [Continent Doc](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/docs/hierarchical/src/postprocessing/README.md) | [`src/postprocessing/entity_resolver.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/postprocessing/entity_resolver.py) | Union-Find entity deduplication & edge rewiring `[Documented]` |
| **Proxy** | [Continent Doc](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/docs/hierarchical/src/proxy/README.md) | [`src/proxy/litellm_runner.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/proxy/litellm_runner.py) | Local LiteLLM proxy execution on port 8002 `[Documented]` |
| **Query** | [Continent Doc](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/docs/hierarchical/src/query/README.md) | [`src/query/graphrag_engine.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/query/graphrag_engine.py), [`intent_classifier.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/query/intent_classifier.py) | Intent classification, GraphRAG engine & guardrails `[Documented]` |
| **Shared** | [Continent Doc](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/docs/hierarchical/src/shared/README.md) | [`src/shared/api_models.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/shared/api_models.py), [`api_routes.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/shared/api_routes.py) | Shared Pydantic API schemas & route registration `[Documented]` |
| **Web** | [Continent Doc](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/docs/hierarchical/src/web/README.md) | [`src/web/app.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/web/app.py), [`src/web/static/app.js`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/web/static/app.js) | FastAPI routes, SSE endpoints, and Web Speech UI `[Documented]` |
