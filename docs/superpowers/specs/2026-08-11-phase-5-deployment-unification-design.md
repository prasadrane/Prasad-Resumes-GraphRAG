# Phase 5 — Deployment Unification Design

**Date:** 2026-08-11
**Status:** Draft (pending approval)
**Replaces:** Phase 5 (Performance) from the incremental refactoring roadmap — deferred to a future phase.

---

## 1. Problem Statement

The application currently runs in two modes with separate entrypoints:
- **Local server** (`src/web/app.py`): Full FastAPI app served via `python src/cli.py ui`
- **Vercel serverless** (`api/index.py`): Stateless entrypoint for `vercel --prod`

While the shared-router pattern (`src/shared/api_routes.py`) eliminated most endpoint duplication, the two-path architecture still creates:
- **Two mental models** for contributors (local vs. Vercel behavior)
- **Two test paths** (local tests + Vercel preview deployments)
- **Config-driven branches** (PDF serving mode, output directory)
- **Maintenance burden** (two entrypoints to keep in sync)

The GraphRAG query and LLM routing paths are already unified — both local and Vercel use `search_engine.py` → `static_graph_reader.py` + `serverless_gateway.py`. No heavy dependencies (LanceDB, GraphRAG runtime) are in the web UI path.

---

## 2. Goal

Unify the deployment paths into a single entrypoint and codebase, with environment-driven configuration for the remaining differences (filesystem, PDF serving). Local development uses `vercel dev` (wrapped by `python src/cli.py ui` for convenience).

---

## 3. Architecture

### 3.1 Single Entrypoint

**Current:**
```
src/web/app.py → local FastAPI app (port 8000)
api/index.py → Vercel handler (imports shared_router)
```

**Target:**
```
src/web/app.py → FastAPI app (unchanged)
api/index.py → Vercel handler that imports and wraps src/web/app.py
```

The `api/index.py` entrypoint becomes a thin wrapper that:
- Imports the FastAPI app from `src/web/app.py`
- Adapts it to Vercel's handler format (if needed — Vercel Python Functions support ASGI apps directly)
- No duplicate endpoint logic

### 3.2 Local Development

**Current:**
```bash
python src/cli.py ui  # runs uvicorn on src/web/app.py
```

**Target:**
```bash
python src/cli.py ui  # runs `vercel dev` under the hood
```

The `ui` subcommand in `src/cli.py` is repurposed to invoke `vercel dev`, giving developers the familiar command while testing the actual deployment path.

### 3.3 Filesystem Abstraction

**Current:**
- Local: writes to `output/`
- Vercel: read-only → writes to `/tmp/output`

**Target:**
- Config-driven via `OUTPUT_DIR` environment variable
- `src/config.py` reads `OUTPUT_DIR` (default: `output/`)
- Vercel sets `OUTPUT_DIR=/tmp/output` in `vercel.json` or via environment
- One codepath, two values

### 3.4 PDF Serving

**Current:**
- Local: returns `/output/{path}` (file URL)
- Vercel: returns base64 data URI

**Target:**
- Always return base64 data URI from the API
- The UI already handles data URIs (it does on Vercel today)
- Eliminates the `/output/{path}` route and config-driven branching
- 33% overhead (base64) is acceptable for 2-page resumes (~100KB → ~133KB)

### 3.5 UI Static Files

**Current:**
- `src/web/static/` (local)
- `static/` (Vercel, copied at deploy)

**Target:**
- One directory: `src/web/static/`
- Update `vercel.json` to serve static files from `src/web/static/`
- Eliminates the copy step and potential drift

### 3.6 GraphRAG Query and LLM Routing (No Change)

Both are already unified:
- `search_engine.py` → `static_graph_reader.py` (context) + `serverless_gateway.py` (LLM)
- No LanceDB or GraphRAG runtime in the web UI path
- Both local and Vercel use the same code

---

## 4. Migration Strategy (Incremental)

Each step is verified independently. The app must work on both `vercel dev` and preview deployments after each step.

### Step 1: Abstract filesystem via config
- Add `OUTPUT_DIR` to `src/config.py` (default: `output/`)
- Replace hardcoded `output/` paths with `OUTPUT_DIR`
- Set `OUTPUT_DIR=/tmp/output` for Vercel (in `vercel.json` or environment)
- Verify: local dev still works, Vercel preview still works

### Step 2: Unify PDF serving (always data URI)
- Modify `src/shared/api_routes.py` to always return data URIs
- Delete the `/output/{path}` route from `src/web/app.py`
- Update the UI to always fetch data URIs (it already does on Vercel)
- Verify: PDF download works on both local and Vercel

### Step 3: Consolidate UI static files
- Move `static/` contents to `src/web/static/` (if not already there)
- Update `vercel.json` to serve from `src/web/static/`
- Delete the `static/` directory
- Verify: UI loads correctly on both local and Vercel

### Step 4: Unify entrypoints
- Modify `api/index.py` to import and wrap `src/web/app.py`
- Remove duplicate endpoint logic from `api/index.py` (keep only the Vercel-specific wrapper)
- Optionally: delete `src/shared/api_routes.py` if the shared-router pattern is no longer needed (evaluate after this step)
- Verify: all endpoints work on both local and Vercel

### Step 5: Repurpose `python src/cli.py ui`
- Modify `src/cli.py` to run `vercel dev` instead of `uvicorn`
- Update documentation to reflect the new workflow
- Verify: `python src/cli.py ui` starts the app via `vercel dev`

### Step 6: Cleanup
- Remove dead code (old `/output/{path}` route, duplicate static files)
- Update README and CLAUDE.md with the new architecture
- Verify: all tests pass, documentation is accurate

---

## 5. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| `vercel dev` is slower than `uvicorn` hot-reload | Acceptable tradeoff for architectural simplicity; developers can still use `uvicorn` directly if needed |
| Data URI overhead slows PDF download | 33% overhead on ~100KB is negligible; monitor user feedback |
| Breaking existing local dev workflow | Repurpose `python src/cli.py ui` to wrap `vercel dev`; document the change |
| Vercel preview deployments fail after unification | Test each step on preview deployments; rollback if needed |
| Shared-router pattern becomes unnecessary | Evaluate after Step 4; delete if truly redundant |

---

## 6. Success Criteria

- [ ] Single entrypoint: `api/index.py` wraps `src/web/app.py`
- [ ] Local dev: `python src/cli.py ui` runs `vercel dev`
- [ ] PDF serving: always data URI (no config-driven branching)
- [ ] UI static files: one directory (`src/web/static/`)
- [ ] Filesystem: config-driven via `OUTPUT_DIR`
- [ ] All tests pass (pytest, unittest, E2E baseline)
- [ ] Vercel preview deployment works
- [ ] Documentation updated (README, CLAUDE.md)

---

## 7. What This Does NOT Include

- **Performance optimizations** (caching, async, O(1) keyword matching) — deferred to a future phase
- **GraphRAG query changes** — already unified, no action needed
- **LLM routing changes** — already unified, no action needed
- **New features** — this is a refactor-only phase

---

## 8. Dependencies

- `vercel` CLI must be installed (`npm i -g vercel`)
- Vercel project must be configured (already done)
- Python 3.11+ (already required)

---

## 9. Timeline Estimate

~1-2 days of focused work, broken into 6 incremental steps. Each step is independently verifiable and reversible.
