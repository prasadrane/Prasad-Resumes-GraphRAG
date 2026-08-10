# Incremental Refactoring with a Playwright E2E Safety Net

**Date:** 2026-08-10
**Status:** Approved
**Scope:** Safe, phase-by-phase improvement of the Prasad-Resumes-GraphRAG codebase without breaking the working application, verified via end-to-end browser tests.

---

## 1. Background

A multi-agent review of the codebase surfaced issues across five dimensions: security, code quality, architecture, testing/documentation, and performance. The findings are summarized below and motivate this plan.

### Critical findings
- **API keys committed to git.** `.env` containing `GRAPHRAG_API_KEY`, `OPENROUTER_API_KEY`, and `FREELLMAPI_API_KEY` is tracked in git history. Keys must be rotated and history scrubbed. *(Deferred by the owner — see Section 9.)*
- **Path traversal vulnerability.** `src/web/app.py:150-157` (`/api/pdf/{company}/{filename}`) injects user input directly into a glob pattern with no containment check.
- **AttributeError bug.** `api/index.py:115` reads `req.content` on `RenderPdfRequest`, which has no `content` field, so it always raises (masked by the outer `except`).

### High-priority findings
- Massive duplication between `src/web/app.py` and `api/index.py` (~500 lines of near-identical endpoints and models).
- ~150 lines of duplicated LLM orchestration between `generate_raw_resume` and `generate_raw_resume_stepwise` in `src/generators/resume_generator.py`.
- Circular import between `src/generators/ats_matcher.py` and `src/query/search_engine.py`.
- Silent exception swallowing (`except Exception: pass`) in `src/query/static_graph_reader.py:22,38`.
- `read_precomputed_entities()` reads from disk on every query (no caching).
- Internal error details leaked to HTTP clients.
- Hardcoded Windows developer paths (`src/cli.py:30`, `docker-compose.yml:17`).

### Medium-priority findings
- Test coverage gaps: `pdf_parser.py`, `pdf_styles.py`, `models.py`, and `cli.py::main()` have no tests; several tests are smoke-only.
- No `conftest.py`, no coverage config, no CI.
- Missing `uvicorn` in `requirements.txt` (breaks fresh install of `cli.py ui`).
- Redundant PDF libraries (`pdfplumber`, `pypdf` installed; only `pymupdf` used).
- README inaccuracies (missing proxy startup step, wrong env var name, missing `FREELLMAPI_API_KEY`).

### Low-priority findings
- Inconsistent type hints, magic numbers, dead aliases, mid-file imports, unclear variable names.

---

## 2. Goals and Non-Goals

### Goals
- Improve the codebase incrementally, **one phase at a time**, without breaking the working application.
- Establish an automated end-to-end (E2E) browser test baseline **before** any refactor, using Playwright + Chromium.
- Verify every phase with a repeatable loop: unit tests + E2E baseline + screenshot review.
- Keep each phase independently reversible via per-phase git branches and small commits.

### Non-Goals
- Not rewriting the application or changing its features/behavior.
- Not introducing new product capabilities.
- Not rotating API keys in this plan (owner-deferred; recorded as a follow-up).
- Not touching `venv/`, `output/`, `cache/`, `logs/` contents.

---

## 3. Guiding Principle

> **"Record the working app before touching it, then never make a change that fails the recording."**

Every phase ends with the same verification loop. Any failure is a hard stop and a revert. No phase begins until the previous one is green and committed.

---

## 4. Endpoint Classification

Verified by reading `api/index.py` and `src/web/app.py`. This split determines which flows belong to the always-run baseline versus the opt-in live suite.

### Deterministic (no LLM) — always in baseline
| Endpoint | What it exercises |
|---|---|
| `GET /` | Serves `index.html` (UI load) |
| `GET /api/history` | Returns `[]` |
| `POST /api/keywords` | Pure NLP keyword extraction |
| `GET /api/default-resume` | Master resume parse + PDF render (no LLM) |
| `POST /api/render_pdf`, `POST /api/save-edit` | PDF render from provided raw text |

### LLM-dependent — opt-in live suite
| Endpoint | Notes |
|---|---|
| `POST /api/generate` | Tailored generation |
| `POST /api/generate-stream` | Stepwise streaming generation |
| `POST /api/chat-stream` | GraphRAG chat streaming |
| `POST /api/query` | GraphRAG query |

The deterministic surface covers UI loading, tab navigation, keyword extraction, and the full PDF-rendering path — fast, free, and reliable. LLM endpoints are isolated so the baseline never burns API credits or flakes.

---

## 5. Phase 0 — The Safety Net

Build a characterization of the currently working app before changing any application code.

### 5.1 New dependencies
Add to `requirements-dev.txt`:
- `pytest`
- `pytest-playwright`
- `uvicorn` (the baseline fixture launches the app via uvicorn; it is also a runtime requirement of `cli.py ui` and is currently missing from `requirements.txt` — add it there too in this phase)

One-time setup: `playwright install chromium`.

### 5.2 New files
- **`tests/e2e/conftest.py`** — session-scoped fixtures:
  - `app_server`: launches `src.web.app:app` via a uvicorn subprocess on a **free port** (not hardcoded 8000), waits for a healthy response, yields `base_url`, then terminates the subprocess. Does **not** start LiteLLM proxy (baseline has no LLM calls).
  - `page`: Playwright browser page from `pytest-playwright`.
- **`tests/e2e/test_baseline_ui.py`** — browser flows:
  - Page loads and title is correct.
  - Default tab is active and master resume loads (raw textarea populated or PDF iframe `src` set).
  - Tab switching works: default → tailor → chat.
  - Tailor form elements present: `#company-input`, `#jd-input`, `#generate-btn`.
  - Chat elements present: mode buttons (`[data-mode="local"]`, `[data-mode="global"]`), chat input, `#clear-chat-btn`.
  - Status badge `#system-status` present.
- **`tests/e2e/test_baseline_api.py`** — deterministic endpoint checks:
  - `GET /` returns 200 and serves HTML.
  - `GET /api/history` returns `[]`.
  - `POST /api/keywords` returns a non-empty keyword list for a sample JD.
  - `GET /api/default-resume` returns `status: success`, a non-empty `raw_resume`, and a `pdf_url` that is a valid base64 data URI (decode succeeds, starts with `%PDF`).
  - `POST /api/render_pdf` with sample raw text returns a valid PDF data URI.
- **`tests/e2e/test_llm_live.py`** — the four LLM flows, each marked `@pytest.mark.live`, **skipped by default**, runnable with `pytest -m live`.
- **`tests/e2e/screenshots/baseline/`** — reference screenshots of each tab (default, tailor, chat) for human review.
- **`pytest.ini` or `pyproject.toml [tool.pytest.ini_options]`** — registers the `live` marker and sets test paths.

### 5.3 One-command run
- Fast baseline: `python -m pytest tests/e2e/ -v`
- With live LLM flows: `python -m pytest tests/e2e/ -v -m live`

### 5.4 Phase 0 exit criteria
- App boots cleanly under the fixture (health check passes).
- All deterministic baseline tests pass.
- Screenshots captured for the three tabs.
- Baseline, config, and design doc committed.

---

## 6. Phases 1–5

Each phase lists concrete deliverables and how it is verified.

### Phase 1 — Critical fixes
- Fix path traversal in `src/web/app.py:150-157` (add `OUTPUT_DIR.resolve()` containment check, matching the existing `serve_output_file` guard).
- Fix `req.content` AttributeError in `api/index.py:115` (use `req.raw_text`).
- Remove redundant PDF libs (`pdfplumber`, `pypdf`) from `requirements-dev.txt`.
- Replace silent `except Exception: pass` in `src/query/static_graph_reader.py:22,38` with logged warnings.
- **Verification:** baseline green + add regression tests for the path-traversal and `render_pdf` fixes.

> Note: `uvicorn` is added to `requirements.txt` in Phase 0 (see Section 5.1) because the baseline fixture requires it to boot the app.

### Phase 2 — Architecture
- Break the circular import between `ats_matcher.py` and `search_engine.py` (introduce an LLM-service abstraction layer).
- Extract shared routes/models out of `src/web/app.py` and `api/index.py` into a shared module; have both apps import it.
- Dedupe LLM orchestration in `resume_generator.py` (have `generate_raw_resume_stepwise` delegate to the shared tailoring logic).
- Centralize configuration (a single settings module instead of scattered `ROOT_DIR` recomputation and magic values).
- **Verification:** baseline green + unit tests green.

### Phase 3 — Testing & CI
- Add `tests/conftest.py` with shared fixtures.
- Add tests for `pdf_parser.py`, `pdf_styles.py`, `models.py`, and `cli.py::main()`.
- Upgrade smoke tests (`test_static_graph_reader.py`, `test_ats_matcher.py::test_match_graphrag_stories`) to real assertions.
- Add coverage config and a GitHub Actions workflow that runs unit + E2E baseline on every PR.
- **Verification:** coverage report generated + CI passes.

### Phase 4 — Documentation & polish
- Fix README: add LiteLLM proxy startup step, correct env var names (`GRAPHRAG_API_KEY`), add `FREELLMAPI_API_KEY` to `.env` sample, add API reference and troubleshooting.
- Add type hints to public functions.
- Extract magic numbers into named constants.
- Fix outdated comments (`settings.yaml:1`, `settings.yaml:69` path separator).
- Remove hardcoded Windows paths (`src/cli.py:30`, `docker-compose.yml:17`).
- **Verification:** docs-only changes; baseline still green (no behavior change).

### Phase 5 — Performance
- Cache `read_precomputed_entities()` (`@lru_cache` or load-once at startup).
- Convert synchronous LLM calls to async where feasible.
- Make keyword matching O(1) via a precomputed `dict[str, str]`.
- Pre-compile repeated regexes.
- Apply design patterns where they reduce coupling (Strategy for LLM providers, Factory for resume generation).
- **Verification:** baseline green + live LLM sanity check.

---

## 7. Verification Loop (per phase)

```
make change
  → run unit tests
  → run Playwright baseline
  → review screenshots
      ├─ all green → commit (small, focused) → next change
      └─ any red   → git revert / fix → re-run
```

A phase is "done" only when: unit tests pass, the E2E baseline passes, and screenshots show no visual regression. Then commit and proceed.

---

## 8. Git Workflow & Rollback

- **Branch per phase** (e.g., `refactor/phase-1-critical-fixes`).
- **Small commit per verified change** with a clear message.
- Baseline tests, Playwright config, and this design doc are **committed**.
- **Rollback granularity:** revert a single commit, or reset the whole phase branch. Nothing merges until reviewed.

---

## 9. Deferred Security Follow-Up (owner action)

Deferred by the owner but recorded here so it is not lost:
1. Rotate all three leaked keys (`GRAPHRAG_API_KEY`, `OPENROUTER_API_KEY`, `FREELLMAPI_API_KEY`) at the provider websites.
2. Update local `.env` with the new keys.
3. Remove `.env` from git tracking: `git rm --cached .env`.
4. Scrub git history: `git filter-branch --force --index-filter 'git rm --cached --ignore-unmatch .env' --prune-empty --tag-name-filter cat -- --all` (or `git filter-repo`), then force-push.
5. Confirm `.env` is in `.gitignore`.

Until this is done, the leaked keys remain usable by anyone who has seen the repo history.

---

## 10. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| App won't start without LiteLLM proxy | Baseline only exercises non-LLM paths; fixture health-check fails fast if the app doesn't boot |
| Flaky browser tests | Structural assertions (element present, non-empty) over pixel diffs; screenshots for human review only |
| LLM test cost/flakiness | Live tests skipped by default, opt-in via `-m live` |
| Hidden import-time side effects | Fixture health check surfaces boot failures immediately |
| Port conflicts | Fixture selects a free port dynamically |
| Refactor breaks a flow not in baseline | Grow the baseline during Phase 0 to cover all deterministic flows before any refactor |

---

## 11. Success Criteria

- A green, committed Playwright baseline exists before any application code changes.
- Each of Phases 1–5 lands on its own branch, verified green, and reviewed before merge.
- No regression in the deterministic UI/API surface across the entire effort.
- Unit test coverage increases and CI enforces it.
- All critical and high-priority findings from the review are resolved (except the deferred key rotation).
