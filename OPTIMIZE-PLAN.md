# Unified Optimization Plan — GraphRAG Resume System

**Created:** 2026-08-12  
**Sources:** `NOTES.md` (code simplification & reliability) + `EMBEDDING-OPTIMIZE-NOTE.md` (embedding & graph quality)  
**Goal:** Transform codebase from "working" to "production-ready" — cleaner code, higher retrieval quality, better observability, and scalable architecture.

---

## 🧭 Executive Summary

This plan merges two previously separate optimization efforts into **one unified execution strategy** designed for parallel subagent work. The plan identifies **5 independent workstreams** that can run simultaneously with minimal cross-dependencies, plus **2 integration phases** that must run sequentially after the parallel work completes.

**Key principle:** Each workstream owns a distinct set of files. No two workstreams modify the same file. Integration phases reconcile any cross-cutting concerns.

---

## 📊 Workstream Overview

| ID | Name | Source | Duration | Files Owned | Dependencies |
|----|------|--------|----------|-------------|--------------|
| **W1** | LLM Gateway Reliability | NOTES Phase 1-2 | Week 1-2 | `src/gateway/*`, `src/llm/service.py`, `tests/test_llm_service.py` | None |
| **W2** | Embedding & Graph Quality | EMBEDDING Priority 1-3 | Week 1-2 | `settings.yaml`, `src/postprocessing/*`, `scripts/postprocess_graph.py` | None |
| **W3** | Performance & Caching | NOTES Phase 3 | Week 2-3 | `src/query/search_engine.py`, `src/gateway/base.py` | W1 (gateway changes) |
| **W4** | Observability & Operations | NOTES Phase 4 | Week 3 | `src/web/app.py`, `src/metrics.py`, `src/shared/api_models.py` | None |
| **W5** | Extensibility & Config | NOTES Phase 5 + EMBEDDING Priority 4-6 | Week 3-4 | `src/generators/ats_matcher.py`, `src/generators/resume_generator.py`, `src/query/intent_classifier.py`, `config/*`, `evaluation/*` | W2 (entity resolution output) |
| **I1** | Integration & Cross-Validation | Both | Week 4 | All workstream outputs | W1-W5 complete |
| **I2** | End-to-End Testing & Polish | Both | Week 5 | Test suite, docs, README | I1 complete |

---

##  Overlap Analysis & Resolution

### Overlap 1: `src/generators/` module
- **NOTES** wants to simplify `ats_matcher.py` and `resume_generator.py` (move patterns to config, add type hints)
- **EMBEDDING** wants to add `resume_structured_parser.py` and conversion scripts
- **Resolution:** W5 owns both. The structured parser is a new file; simplification of existing files happens in the same workstream. No conflict.

### Overlap 2: `src/query/` module
- **NOTES** wants to add caching to `search_engine.py` (W3)
- **EMBEDDING** wants to add `intent_classifier.py` (W5)
- **Resolution:** Different files, no conflict. W3 owns `search_engine.py`; W5 owns `intent_classifier.py`. If intent classifier needs to call search_engine, it uses the public API — no coupling.

### Overlap 3: Configuration files
- **NOTES** wants `config/tech_patterns.yaml`, `config/domain_keywords.yaml`
- **EMBEDDING** modifies `settings.yaml` for multi-pass extraction
- **Resolution:** Different files, no conflict. W5 creates new YAML files; W2 modifies existing `settings.yaml`.

### Overlap 4: Provider/Gateway changes
- **NOTES** Phase 1-2 modifies gateway extensively (retry, circuit breaker, shared helpers)
- **EMBEDDING** doesn't touch gateway
- **Resolution:** W1 owns all gateway changes. W3 (caching) depends on W1's gateway stabilization — W3 starts after W1 completes.

### Overlap 5: Evaluation framework
- **EMBEDDING** Priority 6 creates `evaluation/query_dataset.json` and `evaluation/evaluate_retrieval.py`
- **NOTES** doesn't have evaluation
- **Resolution:** W5 owns evaluation. No conflict.

---

## 🚀 Workstream Details

### W1: LLM Gateway Reliability
**Owner:** Subagent 1  
**Duration:** Week 1-2  
**Files:** `src/gateway/base.py`, `src/gateway/facade.py`, `src/gateway/alibaba.py`, `src/gateway/gemini.py`, `src/gateway/openrouter.py`, `src/gateway/circuit_breaker.py` (new), `src/llm/service.py`, `tests/test_llm_service.py`, `tests/test_gateway_providers.py`

**Tasks:**
1. **1.1** Consolidate `call_llm` / `call_llm_safe` / `call_llm_for_resume` / `call_llm_safe_for_resume` → 2 functions with `safe` and `use_case` params
2. **1.2** Extract `pad_embedding()` to `base.py` (used by gemini.py and facade.py)
3. **1.3** Extract `is_rate_limit_error()` to `base.py` (used by gemini.py, alibaba.py, facade.py)
4. **1.4** Replace `print()` with `logging` in gateway and llm modules
5. **1.5** Add `retry_with_backoff(max_retries=3, base_delay=1.0)` decorator to facade.py
6. **1.6** Implement `CircuitBreaker` class in new `circuit_breaker.py` module
7. **1.7** Wire circuit breaker into `_try_chain()` failover logic

**Entry condition:** No dependencies — can start immediately.  
**Exit condition:** All gateway tests pass, circuit breaker state transitions verified, retry timing confirmed.

---

### W2: Embedding & Graph Quality
**Owner:** Subagent 2  
**Duration:** Week 1-2  
**Files:** `settings.yaml`, `src/postprocessing/entity_resolver.py` (new), `scripts/postprocess_graph.py` (new), `tests/test_entity_resolver.py` (new)

**Tasks:**
1. **2.1** Update `settings.yaml`: `max_gleanings: 1` → `3` for multi-pass entity extraction
2. **2.2** Run indexing with new settings, measure entity count increase (target: +15-25%)
3. **2.3** Create `src/postprocessing/entity_resolver.py` with `EntityResolver` class:
   - String similarity via `SequenceMatcher`
   - Semantic similarity via embeddings for TECHNOLOGY entities
   - Merge entities above similarity threshold (default 0.85)
   - Update relationships to use canonical names
4. **2.4** Create `scripts/postprocess_graph.py` to run entity resolution on output parquet files
5. **2.5** Test entity resolution: verify merged entities are actual duplicates, no distinct entities lost

**Entry condition:** No dependencies — can start immediately.  
**Exit condition:** Entity count increases 15-25% after multi-pass, decreases 10-20% after resolution, manual inspection confirms quality.

---

### W3: Performance & Caching
**Owner:** Subagent 3  
**Duration:** Week 2-3 (starts after W1)  
**Files:** `src/query/search_engine.py`, `src/gateway/base.py`

**Tasks:**
1. **3.1** Add `TTLCache` class to `search_engine.py` (max_size=100, ttl=300s)
2. **3.2** Wrap `execute_graphrag_query()` with cache lookup/insert
3. **3.3** Configure aiohttp connection pooling in `base.py`: `TCPConnector(limit=100, limit_per_host=10, ttl_dns_cache=300)`
4. **3.4** Add cache metrics (hit rate, miss rate, eviction count)

**Entry condition:** W1 complete (gateway stabilized).  
**Exit condition:** Cache hits verified, TTL expiry confirmed, connection pool limits tested under load.

---

### W4: Observability & Operations
**Owner:** Subagent 4  
**Duration:** Week 3  
**Files:** `src/web/app.py`, `src/metrics.py` (new), `src/shared/api_models.py`, `tests/test_health_check.py` (new), `tests/test_metrics.py` (new)

**Tasks:**
1. **4.1** Implement `StructuredLogger` with correlation ID via `ContextVar`
2. **4.2** Add correlation ID propagation across all modules (gateway, generators, query)
3. **4.3** Implement `MetricsCollector` with counters and histograms in new `src/metrics.py`
4. **4.4** Add `/api/metrics` endpoint to export metrics (Prometheus-compatible format)
5. **4.5** Enhance `/api/health` endpoint with dependency checks (LLM gateway, GraphRAG engine, database)
6. **4.6** Add Pydantic validators to `api_models.py` (query sanitization, JD length limits, mode patterns)

**Entry condition:** No dependencies — can start immediately.  
**Exit condition:** Health check returns detailed status, metrics endpoint exports data, correlation IDs appear in logs.

---

### W5: Extensibility & Config
**Owner:** Subagent 5  
**Duration:** Week 3-4  
**Files:** `src/generators/ats_matcher.py`, `src/generators/resume_generator.py`, `src/generators/constants.py`, `src/query/intent_classifier.py` (new), `src/converters/resume_structured_parser.py` (new), `config/tech_patterns.yaml` (new), `config/domain_keywords.yaml` (new), `evaluation/query_dataset.json` (new), `evaluation/evaluate_retrieval.py` (new), `scripts/convert_structured_resume.py` (new)

**Tasks:**
1. **5.1** Move `KNOWN_TECH_PATTERNS` from `ats_matcher.py` to `config/tech_patterns.yaml`
2. **5.2** Move `DOMAIN_KEYWORDS` from `resume_generator.py` to `config/domain_keywords.yaml`
3. **5.3** Centralize magic numbers in `constants.py`: `EMBEDDING_DIM`, `LLM_MAX_TOKENS`, `LLM_DEFAULT_TIMEOUT`, `GRAPHRAG_STORY_CAP`
4. **5.4** Add consistent type hints to `resume_generator.py` and `ats_matcher.py`
5. **5.5** Create `src/query/intent_classifier.py` with `IntentClassifier` class:
   - Classify queries as SKILL_LOOKUP, COMPANY_LOOKUP, EXPERIENCE_LOOKUP, GENERAL_QUERY
   - Return retrieval strategy per intent
6. **5.6** Create `src/converters/resume_structured_parser.py` for structured resume parsing before GraphRAG indexing
7. **5.7** Create `evaluation/query_dataset.json` with 20-30 real queries and expected results
8. **5.8** Create `evaluation/evaluate_retrieval.py` to measure retrieval precision/recall

**Entry condition:** W2 complete (entity resolution output available for evaluation).  
**Exit condition:** Config files load correctly, intent classifier accuracy >80%, evaluation framework runs end-to-end.

---

### I1: Integration & Cross-Validation
**Owner:** Main agent (you)  
**Duration:** Week 4  
**Files:** All workstream outputs

**Tasks:**
1. **I1.1** Verify W1-W5 changes don't conflict (no duplicate imports, no circular dependencies)
2. **I1.2** Run full test suite — all 163 tests must pass
3. **I1.3** Verify circuit breaker + cache interaction (circuit breaker opens → cache serves stale data)
4. **I1.4** Verify intent classifier + caching interaction (different intents use different cache keys)
5. **I1.5** Verify entity resolution + evaluation framework (evaluation measures post-resolution quality)
6. **I1.6** Update `docs/` with new architecture decisions

**Entry condition:** W1-W5 all complete.  
**Exit condition:** No integration issues, all tests pass, documentation updated.

---

### I2: End-to-End Testing & Polish
**Owner:** Main agent (you) + judge panel workflow  
**Duration:** Week 5  
**Files:** Test suite, README.md, docs/

**Tasks:**
1. **I2.1** Run e2e baseline test (`scripts/run_e2e_baseline.py`)
2. **I2.2** Run evaluation framework on baseline, then on optimized system — measure improvement
3. **I2.3** Update README.md with new features (caching, circuit breaker, metrics, evaluation)
4. **I2.4** Run judge panel workflow on updated architecture diagram (if diagram changed)
5. **I2.5** Final code review — check for remaining `print()` statements, missing type hints, magic numbers
6. **I2.6** Performance benchmark — measure latency before/after caching

**Entry condition:** I1 complete.  
**Exit condition:** All acceptance criteria met, README updated, benchmarks documented.

---

## 📈 Parallelization Strategy

### Week 1-2: Three workstreams in parallel
```
Subagent 1: W1 (Gateway Reliability)
Subagent 2: W2 (Embedding & Graph Quality)
Subagent 4: W4 (Observability & Operations)
```
These three workstreams touch completely different files — zero overlap.

### Week 2-3: Add two more workstreams
```
Subagent 1: W1 complete → starts W3 (Performance & Caching)
Subagent 2: W2 complete → idle (or helps W5)
Subagent 3: New subagent starts W5 (Extensibility & Config)
Subagent 4: W4 complete → idle (or helps W5)
```
W3 depends on W1 (gateway changes). W5 depends on W2 (entity resolution output for evaluation).

### Week 4: Integration
```
Main agent: I1 (Integration & Cross-Validation)
```
All subagents complete. Main agent verifies integration.

### Week 5: Polish
```
Main agent + judge panel: I2 (End-to-End Testing & Polish)
```
Final verification and documentation.

---

## 🎯 Success Criteria

### Code Quality
- [ ] 30% reduction in lines of code (from consolidation)
- [ ] Zero `print()` statements in production code
- [ ] All functions have type hints
- [ ] Magic numbers centralized in `constants.py`
- [ ] Hardcoded patterns moved to config files

### Reliability
- [ ] 99.9% success rate on LLM calls (retry + circuit breaker)
- [ ] Circuit breaker state transitions verified under load
- [ ] Retry with exponential backoff prevents thundering herd

### Performance
- [ ] 50% reduction in repeated query latency (caching)
- [ ] Connection pooling prevents exhaustion under load
- [ ] Cache hit rate >60% for typical usage patterns

### Graph Quality
- [ ] Entity count increases 15-25% after multi-pass extraction
- [ ] Entity count decreases 10-20% after resolution (deduplication)
- [ ] Merged entities verified as actual duplicates (manual inspection)

### Observability
- [ ] All requests traceable via correlation ID
- [ ] `/api/health` returns detailed dependency status
- [ ] `/api/metrics` exports Prometheus-compatible metrics
- [ ] Structured logging with JSON format

### Evaluation
- [ ] Evaluation dataset covers 20-30 real queries
- [ ] Retrieval F1 score improves 10-20% after optimizations
- [ ] Query classification accuracy >80%

### Testing
- [ ] Maintain 100% test pass rate (163 tests)
- [ ] New tests added for circuit breaker, cache, entity resolver, intent classifier
- [ ] E2E baseline test passes

---

## ⚠️ Risk Assessment

| Workstream | Risk Level | Mitigation | Rollback Strategy |
|------------|------------|------------|-------------------|
| W1 (Gateway) | Medium | Feature flags for circuit breaker | Revert git commits |
| W2 (Embedding) | Low | Conservative similarity threshold (0.85) | Re-run indexing with old settings |
| W3 (Performance) | Medium | Cache can be disabled via env var | Set `CACHE_ENABLED=false` |
| W4 (Observability) | Low | Additive changes only | Remove new endpoints |
| W5 (Extensibility) | Medium | Config files validated on load | Revert to hardcoded patterns |
| I1 (Integration) | Medium | Sequential verification | Fix conflicts before merging |
| I2 (Polish) | Low | Standard testing | N/A |

---

## 🔧 Implementation Guidelines

### For Subagents
1. **Work in isolation:** Each workstream has its own file set. Do not modify files owned by other workstreams.
2. **Test as you go:** Each task must have corresponding tests before marking complete.
3. **Document changes:** Update docstrings and add comments for non-obvious decisions.
4. **Report blockers:** If you discover a dependency on another workstream, report immediately.

### For Integration Phase
1. **Verify file ownership:** Ensure no file was modified by multiple workstreams.
2. **Check imports:** No circular dependencies, no duplicate imports.
3. **Run full test suite:** All 163 tests must pass before proceeding.
4. **Integration tests:** Add tests for cross-workstream interactions (circuit breaker + cache, intent classifier + caching).

### For Final Polish
1. **Performance benchmarks:** Measure before/after for caching, retry, circuit breaker.
2. **Documentation:** Update README.md, `docs/`, and CLAUDE.md with new architecture.
3. **Code review:** Run `/simplify` and `/code-review` skills on final state.

---

##  Session Log

**2026-08-12 (unified plan created)**:
- Merged `NOTES.md` (code simplification & reliability) and `EMBEDDING-OPTIMIZE-NOTE.md` (embedding & graph quality) into single plan
- Identified 5 independent workstreams + 2 integration phases
- Designed for parallel subagent execution with minimal cross-dependencies
- Created `OPTIMIZE-PLAN.md` with detailed task breakdowns, success criteria, and risk assessment
- Next: Begin Week 1-2 parallel workstreams (W1, W2, W4)
