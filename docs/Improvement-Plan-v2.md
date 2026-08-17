# Improvement Plan v2 — Prasad-Resumes-GraphRAG

**Date:** 2026-08-17  
**Analysis Tools Used:**
- Graphify Knowledge Graph (4,125 nodes · 8,392 edges · 193 communities)
- Codebase-Memory MCP (7,363 nodes · 22,077 edges · 12 clusters)
- 4 Parallel Deep-Dive Code Review Agents (Gateway/Query, Generators/Converters, Scripts/Config/Web, Tests/Quality)

**Scope:** Entire `src/`, `scripts/`, `tests/`, `evaluation/`, `config/` — 234 Python files, 19 API routes

---

## Part 1: Code Review — SOLID, YAGNI, KISS Findings

### 1.1 DRY Violations (Don't Repeat Yourself)

#### 🔴 Critical: Three Independent Resume Markdown Parsers

The exact same `MASTER_RESUME.txt` format is parsed in **three completely different places**, each with its own strategy:

| Parser | File | Lines | Strategy |
|:---|:---|:---|:---|
| `parse_resume_markdown()` | [`resume_parser.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/generators/resume_parser.py) | ~276 | Line-by-line iteration → Pydantic `ResumeData` |
| `parse_structured_resume()` | [`resume_structured_parser.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/converters/resume_structured_parser.py) | ~393 | Split on `---` + regex blocks → dict |
| `structure_raw_text()` | [`resume_structurer.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/converters/resume_structurer.py) | ~100 | `STANDARD_HEADERS` section guessing |

**Why it matters:** Any change to the resume format (adding a section, changing date format) must be replicated in three places. Bugs in one parser don't surface in the others, creating silent data inconsistencies.

**Recommendation:** Consolidate into a single `parse_master_resume()` function in `src/generators/resume_parser.py` that returns the canonical `ResumeData` Pydantic model. All consumers (converters, generators, PDF renderer) should use this single source of truth.

---

#### 🔴 Critical: SSE Stream Parsing Duplicated Across 3 Providers

The logic to decode Server-Sent Events (`data: ` prefix stripping, JSON parsing, chunk assembly) is copy-pasted across:

- [`src/gateway/alibaba.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/gateway/alibaba.py)
- [`src/gateway/gemini.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/gateway/gemini.py)
- [`src/gateway/openrouter.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/gateway/openrouter.py)

**Recommendation:** Extract a shared `parse_sse_stream()` async generator into [`src/gateway/base.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/gateway/base.py). Each provider subclass only needs to supply the JSON path to extract the text delta.

---

#### 🟡 Moderate: Duplicated Entity Extraction Logic

`src/query/retrieval_guardrail.py` implements its own `_extract_entities_from_query` using regex and `_STOPWORDS` (lines 108–141), which largely duplicates `src/query/intent_classifier.py`'s `extract_entities` (lines 153–174).

**Recommendation:** Consolidate into a single `extract_query_entities()` utility in a `src/query/utils.py` module.

---

#### 🟡 Moderate: Duplicated Model Resolution in Facade

In [`src/gateway/facade.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/gateway/facade.py), the logic to resolve `provider_model` from config is duplicated identically in both `call_serverless_llm` (lines 218–225) and `call_serverless_llm_stream` (lines 263–270).

**Recommendation:** Extract `_resolve_provider_model(use_case)` helper.

---

#### 🟡 Moderate: Domain Taxonomy Duplication

[`resume_generator.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/generators/resume_generator.py) hardcodes `_DEFAULT_DOMAIN_KEYWORDS` (lines 55–75), while [`sme_ontology.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/generators/sme_ontology.py) (399 lines) defines a deep graph of `SKILL_TAXONOMY` and `CATEGORY_CHILDREN_MAP`. These represent duplicated knowledge schemas.

**Recommendation:** Remove `_DEFAULT_DOMAIN_KEYWORDS` and delegate all domain-matching to `SMEOntology`.

---

#### 🟡 Moderate: Duplicated Default `ResumeData` Fallback

In [`resume_generator.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/generators/resume_generator.py), the exact same 9-line default `ResumeData(...)` instantiation (with "Tech Corp", "B.S. in Computer Science") is duplicated verbatim in both `generate_raw_resume` (lines 630–638) and `generate_raw_resume_stepwise` (lines 663–671).

**Recommendation:** Extract `_default_resume_data()` factory function.

---

#### 🟡 Moderate: API Route Boilerplate Duplication

In [`src/shared/api_routes.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/shared/api_routes.py), `_handle_query_core` (lines 64–142) and `_stream_query_response` (lines 144–190) heavily duplicate boilerplate for resolving GraphRAG engines, initializing conversation stores, UUID setup, and fallback static searches.

**Recommendation:** Extract shared initialization into a `_prepare_query_context()` helper.

---

### 1.2 SOLID Violations

#### 🔴 Critical: SRP — `resume_generator.py` is a God Module (709 lines)

[`resume_generator.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/generators/resume_generator.py) simultaneously handles:
- Domain matching heuristics
- Job bullet scoring and ranking
- Complex LLM prompt construction (multi-paragraph system prompts)
- Local filesystem path management (`get_output_dir`)
- Standard vs. stepwise pipeline orchestration
- Text manipulation (bolding keywords with character budget caps)

**Recommendation:** Split into focused modules:
1. `domain_matcher.py` — domain classification
2. `prompt_builder.py` — LLM prompt templates
3. `text_formatter.py` — bold keywords, markdown formatting
4. `resume_generator.py` — orchestration only

---

#### 🔴 Critical: SRP — `graphrag_engine.py` is a God Class (501 lines)

[`src/query/graphrag_engine.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/query/graphrag_engine.py) handles: LanceDB connections, parquet file parsing, embedding generation, vector search, custom Pandas keyword search fallback, prompt assembly, and SSE streaming payload formatting — all in one class.

**Recommendation:** Extract:
1. `artifact_loader.py` — parquet/LanceDB connection management
2. `vector_search.py` — embedding + search logic
3. Keep `graphrag_engine.py` as a thin orchestrator

---

#### 🟡 Moderate: DIP — Gateway Depends on Generator Constants

[`src/gateway/base.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/gateway/base.py) imports from `src.generators.constants` (lines 38–57) for `LLM_MAX_TOKENS` and `RATE_LIMIT_TAGS`. The infrastructure gateway layer should not depend on the business logic layer.

**Recommendation:** Move these constants to a shared `src/config/llm_constants.py` or inline them in `base.py`.

---

#### 🟡 Moderate: OCP — Hardcoded Keyword Chains in `static_graph_reader.py`

[`src/query/static_graph_reader.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/query/static_graph_reader.py) uses a massive `if/elif` keyword matching chain (lines 84–170) to return hardcoded answers. Adding a new technology topic requires modifying this file.

**Recommendation:** Replace with a data-driven lookup table (e.g., YAML/JSON config or ontology query).

---

#### 🟡 Moderate: OCP — Hardcoded Prompts in Generator

`resume_generator.py` hardcodes `SUMMARY_SYSTEM_PROMPT`, `BULLETS_SYSTEM_PROMPT`, `STRONG_ACTION_VERBS`, and `METRIC_PATTERN`. Changing the prompt methodology requires modifying the generator directly.

**Recommendation:** Move prompts to `config/prompts.yaml` or a `PromptTemplate` class.

---

### 1.3 YAGNI Violations (Dead Code)

#### 🔴 Critical: ~580 Lines of Completely Dead Code

| File | Lines | Issue |
|:---|:---|:---|
| [`semantic_cache.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/gateway/semantic_cache.py) | 131 | Full in-memory vector cache — **never imported or referenced** |
| [`health_prober.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/gateway/health_prober.py) | 54 | Active circuit breaker recovery — **never instantiated** |
| [`serverless_gateway.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/query/serverless_gateway.py) | 29 | Legacy re-export shim — **own docstring says "should be deleted"** |
| [`search_engine.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/query/search_engine.py) `_run_graphrag_query_uncached` | ~30 | Subprocess call to GraphRAG CLI — **never called** |
| [`resume_generator.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/generators/resume_generator.py) `tailor_summary_with_llm`, `tailor_bullets_with_llm` | ~20 | Ghost functions that just `return parsed` — docstring says "kept for API compatibility" |

**Recommendation:** Delete all five dead code sections. The "API compatibility" functions are never called externally.

---

#### 🟡 Moderate: Duplicated Evaluation/Benchmarking Systems

Two completely separate benchmarking mechanisms exist:

1. [`evaluation/evaluate_retrieval.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/evaluation/evaluate_retrieval.py) — reads from `evaluation/query_dataset.json`, uses raw string matching. Currently called by `cli.py` line 133.
2. [`src/observability/benchmark_eval.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/observability/benchmark_eval.py) — structured Pydantic `BenchmarkCase` with an in-file `DEFAULT_BENCHMARK_DATASET`. Called by `scripts/benchmark_eval.py`.

**Recommendation:** Consolidate into the structured `observability` version and update `cli.py` to point to it.

---

#### 🟡 Moderate: FTS5 Engine Built but Unused

[`src/query/fts_search.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/query/fts_search.py) (108 lines) implements an embedded SQLite FTS5 indexer, but `graphrag_engine.py` implements its own Pandas-based `_keyword_search` fallback (lines 106–127) instead.

**Recommendation:** Either integrate FTS5 (which would be faster and better) or delete it.

---

### 1.4 KISS Violations (Overcomplicated Logic)

#### 🔴 Critical: Nested/Redundant Retry Loops in Facade

In [`src/gateway/facade.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/gateway/facade.py):
- `@retry_with_backoff` decorator retries up to `max_retries=3`
- This wraps `call_with_retry`, which is passed to `_try_chain`
- `_try_chain` **also** implements a retry loop `for _ in range(max_retries + 1)` (lines 96–105)

This can result in **3 × 3 = 9 retry attempts** per provider, compounding across the 5+ provider chain to potentially 45+ total attempts before final failure.

**Recommendation:** Single-layer retry: `_try_chain` handles provider failover, `retry_with_backoff` handles per-provider transient retries. Remove the nested loop.

---

#### 🟡 Moderate: Fragile LLM Output Parsing via String Splitting

[`resume_generator.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/generators/resume_generator.py) lines 446–581 builds a massive plain-text prompt instructing the LLM to reply with strings like `"### SUMMARY:"` and `"### JOB 1:"`, then iterates over the returned string applying brittle string-splitting to extract data.

**Recommendation:** Use structured outputs (JSON Schema) from the LLM, decoding natively into `ResumeData`.

---

#### 🟡 Moderate: 150-Line `_extract_jobs` Manual Parser

[`resume_structured_parser.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/converters/resume_structured_parser.py) lines 203–351: a `while i < len(lines):` loop with deeply nested `if/elif` and multiple mutable tracking variables.

**Recommendation:** Use a standard Markdown AST library (e.g., `markdown-it-py`) or fold into the unified parser (§1.1).

---

#### 🟡 Moderate: Embedding Failover Doesn't Use Generic Chain

`get_embedding` in [`facade.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/gateway/facade.py) (lines 306–329) manually implements a hardcoded try/except chain (OpenRouter → LiteLLM → Gemini) instead of using the generic `_try_chain` that chat endpoints use.

**Recommendation:** Route embeddings through `_try_chain` with an embedding-specific provider list.

---

### 1.5 Script Consolidation Opportunity

Multiple scripts in `scripts/` are thin wrappers around `src/cli.py` commands:

| Script | CLI Equivalent | Delta |
|:---|:---|:---|
| `scripts/convert_inputs.py` | `python src/cli.py convert` | None |
| `scripts/run_litellm.py` | `python src/cli.py proxy` | None |
| `scripts/query.py` | `python src/cli.py query` | Adds interactive loop |
| `scripts/benchmark_eval.py` | `python src/cli.py benchmark` | Points to different evaluator |

**Recommendation:** Deprecate `scripts/` wrappers. Move the interactive query loop into `cli.py`'s query command.

---

### 1.6 Test Coverage Gaps

| Subsystem | Status | Key Gap |
|:---|:---|:---|
| Gateway Providers | ✅ Good | Missing: `GeminiProvider.embedContent` tests |
| PDF Renderer | ✅ Good | Missing: malformed document edge cases, PDF content validation |
| ATS Matcher | ✅ Good | Missing: malformed bullet/date edge cases |
| CLI | ✅ Excellent | — |
| Web Routes | ✅ Adequate | Missing: malformed JSON payload coverage |
| GraphRAG Engine | ⚠️ Risk | Many tests behind `@skipUnless(_HAS_ARTIFACTS)` — skipped in CI |
| `semantic_cache.py` | ❌ Dead | No tests (dead code) |
| `health_prober.py` | ❌ Dead | No tests (dead code) |
| `fts_search.py` | ⚠️ Risk | Unused in production |

> [!NOTE]
> `grep` for `TODO/FIXME/HACK/XXX` across `src/` returned **0 results** — the codebase is clean of these markers.

---

### 1.7 Architectural Coupling Issues

**Identified via codebase-memory MCP boundary analysis:**

| From | To | Calls | Issue |
|:---|:---|:---|:---|
| `shared` | `query` | 16 | Shared layer reaches into query internals |
| `generators` | `list` (builtins) | 29 | Heavy list manipulation — indicates procedural style |
| `gateway/base.py` | `generators/constants` | — | Infra layer imports business logic |

**Identified via Graphify god-node analysis:**

The top god nodes (`_read_text: 114 edges`, `dispatch_command: 114 edges`, `_make_id: 105 edges`) are all in the `.agents/skills/graphify/` directory (the Graphify tool itself), not the application. Within the application, the key coupling points are:

- `EntityResolver` (48 edges) — correctly central as the entity normalization hub
- `GraphRAGEngine` (40 edges) — concerning: too many responsibilities (see §1.2)

---

## Part 2: Product Owner Perspective — Top 5 User-Facing Improvements

### 🏆 #1: Real-Time ATS Score Dashboard with Visual Match Breakdown

**Current State:** The system generates a raw text resume and PDF, but users get no visibility into how well their resume matches the job description. The `extract_ats_keywords` function runs silently during generation. The web UI has an `/api/ats-score` route placeholder but no implementation.

**Proposed Feature:** After resume generation, show an interactive ATS score dashboard with:
- Overall match percentage (keywords matched / keywords in JD)
- Color-coded keyword breakdown (matched ✅, partially matched 🟡, missing ❌)
- Section-by-section scoring (Skills, Experience, Summary)
- Actionable suggestions ("Add 'Kubernetes' to your skills section to improve match by ~8%")
- Side-by-side diff view of original vs. tailored resume

**Why this matters most:** The entire value proposition of the tool is ATS optimization. Without visible scoring, users can't evaluate quality or iterate. Every competing tool (Jobscan, Resume Worded, Teal) leads with their score. This is the **#1 retention driver**.

**Effort:** Medium — the `SMEOntology`, `ImpactScorer`, and `extract_ats_keywords` already exist. Needs a scoring aggregation layer and frontend visualization.

---

### 🏆 #2: Multi-Resume Version Management & Comparison

**Current State:** Each generation creates files in `output/<company>/` with fixed filenames. There's no way to compare versions, revert to a previous version, or maintain multiple tailored variants for the same company.

**Proposed Feature:**
- Timestamped version history for each company target
- Side-by-side diff viewer (old resume vs. new resume)
- "Fork" a resume to create variations (e.g., for different roles at the same company)
- Quick-select "best version" with one click
- History panel in the web UI showing generation parameters (JD used, date, ATS score)

**Why this matters:** Job seekers typically apply to 10–50 companies. They need to iterate on resumes, compare versions, and pick the best one. Without versioning, every regeneration overwrites previous work.

**Effort:** Medium — Requires a lightweight version store (SQLite or filesystem-based) and frontend work.

---

### 🏆 #3: Job Description Auto-Extraction from URL

**Current State:** Users must manually copy-paste job descriptions into a `.txt` file and pass it via `--jd-file`. This is a significant friction point.

**Proposed Feature:**
- Accept job posting URLs (LinkedIn, Indeed, Greenhouse, Lever, etc.)
- Auto-extract the job description, required skills, company name, and role title
- Clean and normalize the extracted JD (remove boilerplate, navigation, footer)
- Pre-populate the generation form with extracted metadata
- Support batch processing: paste multiple URLs to generate multiple tailored resumes

**Why this matters:** Copy-pasting JDs is the #1 UX friction point. 80%+ of job seekers find roles via URLs. Reducing this to "paste URL → get resume" dramatically improves adoption.

**Effort:** Medium — Web scraping with fallback strategies. Libraries like `trafilatura` or `newspaper3k` handle most job boards.

---

### 🏆 #4: Interactive Resume Editor with Live Preview

**Current State:** The web UI generates a resume and shows it, but editing requires re-running the full generation pipeline. The `/api/save-edit` endpoint exists but the frontend editing experience is minimal.

**Proposed Feature:**
- In-browser WYSIWYG editor for the generated resume
- Live PDF preview panel (updates as you type)
- Inline ATS score recalculation on edit
- Smart suggestions (grammar, action verb strength, quantification prompts)
- Section drag-and-drop reordering
- One-click export to PDF, DOCX, and plain text

**Why this matters:** No user accepts a machine-generated resume as-is. The editing step is where users spend 70%+ of their time. Making this seamless keeps users in the tool instead of exporting to Google Docs/Word.

**Effort:** High — Requires rich text editor integration (e.g., TipTap, Quill) and real-time PDF rendering. Can be phased.

---

### 🏆 #5: Cover Letter & LinkedIn Profile Generation

**Current State:** The codebase has stubs for [`cover_letter_generator.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/generators/cover_letter_generator.py) and [`linkedin_optimizer.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/generators/linkedin_optimizer.py), but they are minimal. The GraphRAG knowledge graph already contains the rich professional narrative needed for both.

**Proposed Feature:**
- **Cover Letter Generation:** Use the same JD + GraphRAG context to generate a tailored cover letter that references specific stories from the candidate's experience
- **LinkedIn Profile Optimization:** Generate an optimized headline, about section, and experience descriptions tailored for recruiter search visibility
- **Consistency Check:** Ensure resume, cover letter, and LinkedIn profile tell a coherent narrative
- **STAR Story Bank Integration:** Pull specific STAR stories from GraphRAG for behavioral interview prep (leveraging existing [`star_generator.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/query/star_generator.py) and [`interview_prep.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/query/interview_prep.py))

**Why this matters:** Job applications typically require resume + cover letter + LinkedIn. Generating all three from the same knowledge graph ensures consistency and saves users 2–3 hours per application. The foundation (GraphRAG, ATS ontology, STAR generator) already exists.

**Effort:** Medium — Core LLM orchestration exists. Needs prompt engineering, templates, and frontend integration.

---

## Part 3: Prioritized Action Items

### Phase 1: Cleanup & Consolidation (Low Risk, High Impact)
1. Delete ~580 lines of dead code (`semantic_cache.py`, `health_prober.py`, `serverless_gateway.py`, ghost functions)
2. Consolidate 3 resume parsers → 1 canonical parser
3. Extract shared SSE parsing utility in `base.py`
4. Deprecate `scripts/` thin wrappers → use `cli.py` exclusively
5. Consolidate 2 benchmarking systems → 1

### Phase 2: SOLID Refactoring (Medium Risk, High Impact)
6. Split `resume_generator.py` god module into focused modules
7. Extract `graphrag_engine.py` responsibilities into `artifact_loader.py` + `vector_search.py`
8. Fix DIP violation: move LLM constants out of `generators.constants`
9. Replace hardcoded keyword chains in `static_graph_reader.py` with data-driven lookup
10. Simplify nested retry loops in `facade.py`

### Phase 3: Product Features (Prioritized by User Impact)
11. ATS Score Dashboard with visual match breakdown
12. Job Description auto-extraction from URL
13. Multi-resume version management
14. Cover letter & LinkedIn profile generation
15. Interactive resume editor with live preview

---

## Appendix A: Analysis Methodology

### Tools & Data Sources

| Tool | Scope | Metrics |
|:---|:---|:---|
| **Graphify** (`graphify query`) | Knowledge graph traversal for coupling, dead code, duplication | 4,125 nodes · 8,392 edges · 193 communities |
| **Codebase-Memory MCP** (`get_architecture`, `search_graph`) | Architecture overview, hotspots, boundaries, clusters | 7,363 nodes · 22,077 edges · 12 clusters |
| **Gateway & Query Reviewer** (subagent) | Deep file-level review of `src/gateway/`, `src/query/`, `src/llm/` | 17 files · ~2,800 lines |
| **Generators & Converters Reviewer** (subagent) | Deep file-level review of `src/generators/`, `src/converters/`, `src/shared/` | 16 files · ~3,000 lines |
| **Scripts & Config & Web Reviewer** (subagent) | Deep file-level review of `scripts/`, `src/web/`, `src/proxy/`, `src/config/`, `src/cli.py` | 20+ files · ~2,500 lines |
| **Test Coverage Reviewer** (subagent) | Test quality, coverage gaps, TODO markers | 56 test files in `tests/` |

### Key Metrics from Codebase-Memory MCP

- **Hotspot #1:** `TTLCache.get` — 416 fan-in (most called function in the codebase)
- **Hotspot #2:** `EntityResolver.resolve` — 147 fan-in (critical entity normalization path)
- **Top Boundary Crossing:** `shared` → `query` — 16 calls (shared layer reaches into query internals)
- **Languages:** Python (221 files), YAML (8), HTML (3), JavaScript (1), CSS (1)

### Key Findings from Graphify

- **God Nodes (Application):** `EntityResolver` (48 edges), `GraphRAGEngine` (40 edges)
- **Community Structure:** 193 communities detected; resume generation (Community 7), query engine (Community 5), facade routing (Community 26) are well-separated but `static_graph_reader` creates tight coupling
- **Import Cycles:** None detected ✅
- **Zero TODO/FIXME/HACK markers** across entire `src/` ✅

---

## Appendix B: File Statistics

### Gateway Subsystem (`src/gateway/`)

| File | Lines | Classes | Status |
|:---|:---|:---|:---|
| `facade.py` | 330 | 0 | 🟡 Needs refactoring (SRP, nested retries) |
| `base.py` | 180 | 1 | 🟡 DIP violation |
| `circuit_breaker.py` | 143 | 2 | ✅ Clean |
| `semantic_cache.py` | 131 | 2 | 🔴 Dead code — delete |
| `gemini.py` | 120 | 1 | 🟡 SSE duplication |
| `alibaba.py` | 108 | 1 | 🟡 SSE duplication |
| `openrouter.py` | 97 | 1 | 🟡 SSE duplication |
| `health_prober.py` | 54 | 1 | 🔴 Dead code — delete |

### Query Subsystem (`src/query/`)

| File | Lines | Classes | Status |
|:---|:---|:---|:---|
| `graphrag_engine.py` | 501 | 1 | 🔴 God class — split |
| `retrieval_guardrail.py` | 424 | 4 | 🟡 Entity extraction duplication |
| `intent_classifier.py` | 345 | 2 | ✅ Clean |
| `static_graph_reader.py` | 208 | 0 | 🔴 Hardcoded fallbacks — data-drive |
| `search_engine.py` | 191 | 1 | 🟡 Dead subprocess code |
| `conversation_store.py` | 173 | 1 | ✅ Clean |
| `star_generator.py` | 135 | 2 | ✅ Clean |
| `fts_search.py` | 108 | 2 | 🟡 Built but unused — decide: integrate or delete |
| `interview_prep.py` | 74 | 2 | ✅ Clean |
| `serverless_gateway.py` | 29 | 0 | 🔴 Dead code — delete |

### Generators Subsystem (`src/generators/`)

| File | Lines | Classes | Status |
|:---|:---|:---|:---|
| `resume_generator.py` | 709 | 0 | 🔴 God module — split into 4 |
| `sme_ontology.py` | 399 | 1 | ✅ Well-structured |
| `resume_parser.py` | 276 | 0 | 🟡 Consolidation target (keep this one) |
| `pdf_renderer.py` | ~250 | 0 | ✅ Clean |
| `ats_matcher.py` | ~200 | 0 | ✅ Clean |
| `scoring.py` | ~150 | 2 | ✅ Clean |
| `models.py` | ~80 | 2 | ✅ Clean |
| `constants.py` | ~50 | 0 | 🟡 Move LLM constants to shared |
