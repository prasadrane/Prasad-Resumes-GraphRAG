# Phase 5 — Deployment Unification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify the dual deployment paths (local vs. Vercel) into a single entrypoint with environment-driven configuration, eliminating maintenance burden and "works locally, fails on Vercel" surprises.

**Architecture:** Single entrypoint (`api/index.py` wraps `src/web/app.py`), config-driven filesystem (`OUTPUT_DIR`), unified PDF serving (always data URI), consolidated static files, local dev via `vercel dev` (wrapped by `python src/cli.py ui`).

**Tech Stack:** Python 3.11, FastAPI, Vercel Functions, environment variables, base64 encoding.

**Base:** master @ b3dd01f · **Branch:** `refactor/phase-5-deployment-unification`

## Gate commands (this phase)

```bash
set -o pipefail
venv/Scripts/python.exe -m pytest tests/ -m "not live" --ignore=tests/e2e -q   # expect: 137 passed
venv/Scripts/python.exe -m unittest discover tests 2>&1 | grep -E "^(Ran [0-9]+ tests|OK|FAILED|ERROR)"   # expect: Ran 125 tests / OK
venv/Scripts/python.exe scripts/run_e2e_baseline.py 2>&1 | tail -3              # expect: 16 passed, 3 deselected, exit 0
```

After every E2E run: `git checkout -- tests/e2e/screenshots` before committing.

Additionally, after each task: test on `vercel dev` locally AND deploy to a Vercel preview to verify both paths work.

## Global Constraints

1. **Zero behavior changes.** The app must work identically before and after each step. Only the deployment architecture changes.
2. **Python is always `venv/Scripts/python.exe`** (Git Bash on Windows). Never `python` or `py` bare.
3. **Both runners stay green** after every task: pytest (137) + unittest (125). E2E unchanged (16 passed, 3 deselected).
4. **No new dependencies.** Vercel CLI is already required.
5. **Never commit `.env`.** Use explicit file paths in `git add` — never `git add -A` or `git add .`.
6. **Shell pipelines that gate on exit codes must use `set -o pipefail`.**
7. **Mock, never call, external services.**
8. **Test on BOTH local (`vercel dev`) AND Vercel preview after each task.** Catch deployment-specific issues early.
9. **Rollback plan:** each task is independently reversible. If a step breaks something, revert that commit.

---

## File Structure

| File | Responsibility | Task |
|---|---|---|
| `src/config.py` | Add `OUTPUT_DIR` env var handling | 1 |
| `src/shared/api_routes.py` | Replace hardcoded `output/` with `OUTPUT_DIR` | 1 |
| `src/web/app.py` | Replace hardcoded `output/` with `OUTPUT_DIR` | 1 |
| `api/index.py` | Replace hardcoded `/tmp/output` with `OUTPUT_DIR` | 1 |
| `vercel.json` | Add `OUTPUT_DIR=/tmp/output` environment variable | 1 |
| `src/shared/api_routes.py` | Always return data URIs for PDFs; remove `/output/{path}` route | 2 |
| `src/web/app.py` | Delete `/output/{path}` route | 2 |
| `src/web/static/app.js` | Ensure PDF download handles data URIs (verify) | 2 |
| `vercel.json` | Update static file serving to `src/web/static/` | 3 |
| `src/web/app.py` | Update static file path to `src/web/static/` | 3 |
| `api/index.py` | Import and wrap `src/web/app.py`; remove duplicate endpoints | 4 |
| `src/shared/api_routes.py` | Evaluate if shared-router pattern is still needed; delete if redundant | 4 |
| `src/cli.py` | Repurpose `ui` subcommand to run `vercel dev` | 5 |
| `README.md` | Update dev workflow documentation | 5 |
| `CLAUDE.md` | Update architecture documentation | 6 |
| `README.md` | Update architecture documentation | 6 |

---

### Task 1: Abstract filesystem via OUTPUT_DIR config

**Files:**
- Modify: `src/config.py` (add `OUTPUT_DIR`)
- Modify: `src/shared/api_routes.py` (use `OUTPUT_DIR`)
- Modify: `src/web/app.py` (use `OUTPUT_DIR`)
- Modify: `api/index.py` (use `OUTPUT_DIR`)
- Modify: `vercel.json` (set `OUTPUT_DIR=/tmp/output`)

**Changes:**
1. Add `OUTPUT_DIR` to `src/config.py` with default `output/`
2. Replace all hardcoded `output/` paths with `OUTPUT_DIR`
3. Replace hardcoded `/tmp/output` in `api/index.py` with `OUTPUT_DIR`
4. Set `OUTPUT_DIR=/tmp/output` in `vercel.json` environment

- [ ] **Step 1: Read current `src/config.py` and add `OUTPUT_DIR`**

Add:
```python
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
OUTPUT_DIR_PATH = ROOT_DIR / OUTPUT_DIR
```

- [ ] **Step 2: Update `src/shared/api_routes.py` to use `OUTPUT_DIR`**

Replace hardcoded `output/` references with `OUTPUT_DIR_PATH`.

- [ ] **Step 3: Update `src/web/app.py` to use `OUTPUT_DIR`**

Replace hardcoded `output/` references with `OUTPUT_DIR_PATH`.

- [ ] **Step 4: Update `api/index.py` to use `OUTPUT_DIR`**

Replace `/tmp/output` with `OUTPUT_DIR` (it will be set to `/tmp/output` via env var on Vercel).

- [ ] **Step 5: Update `vercel.json` to set `OUTPUT_DIR`**

Add to the environment section:
```json
"env": {
  "OUTPUT_DIR": "/tmp/output"
}
```

- [ ] **Step 6: Run both gates**

```bash
set -o pipefail
venv/Scripts/python.exe -m pytest tests/ -m "not live" --ignore=tests/e2e -q 2>&1 | tail -2
venv/Scripts/python.exe -m unittest discover tests 2>&1 | grep -E "^(Ran [0-9]+ tests|OK|FAILED|ERROR)"
```

Expected: 137 passed / 125 passed OK (config-only change).

- [ ] **Step 7: Test on `vercel dev` locally**

```bash
vercel dev
```

Navigate to `http://localhost:3000`, verify PDF generation works.

- [ ] **Step 8: Deploy to Vercel preview**

```bash
vercel --prod
```

Verify PDF generation works on the preview URL.

- [ ] **Step 9: Commit**

```bash
git add src/config.py src/shared/api_routes.py src/web/app.py api/index.py vercel.json
git commit -m "refactor(config): abstract filesystem via OUTPUT_DIR environment variable"
```

---

### Task 2: Unify PDF serving (always data URI)

**Files:**
- Modify: `src/shared/api_routes.py` (always return data URIs)
- Modify: `src/web/app.py` (delete `/output/{path}` route)
- Verify: `src/web/static/app.js` (ensure it handles data URIs)

**Changes:**
1. Modify PDF rendering endpoints to always return base64 data URIs
2. Delete the `/output/{path}` route from `src/web/app.py`
3. Verify the UI already handles data URIs (it does on Vercel today)

- [ ] **Step 1: Read `src/shared/api_routes.py` and modify PDF endpoints**

Ensure `/api/render_pdf` and `/api/save-edit` always return base64 data URIs (no conditional logic based on deployment target).

- [ ] **Step 2: Delete `/output/{path}` route from `src/web/app.py`**

Remove the route that serves files from disk. The UI will fetch data URIs directly.

- [ ] **Step 3: Verify `src/web/static/app.js` handles data URIs**

Check that the PDF download/preview logic works with data URIs (it should, since Vercel already uses them).

- [ ] **Step 4: Run both gates**

Expected: 137 passed / 125 passed OK (refactor only).

- [ ] **Step 5: Test on `vercel dev` locally**

Verify PDF download works with data URIs.

- [ ] **Step 6: Deploy to Vercel preview**

Verify PDF download works on the preview URL.

- [ ] **Step 7: Commit**

```bash
git add src/shared/api_routes.py src/web/app.py
git commit -m "refactor(pdf): unify PDF serving to always return data URIs"
```

---

### Task 3: Consolidate UI static files

**Files:**
- Modify: `vercel.json` (update static file path)
- Modify: `src/web/app.py` (update static file path)
- Delete: `static/` directory (if it exists separately from `src/web/static/`)

**Changes:**
1. Update `vercel.json` to serve static files from `src/web/static/`
2. Update `src/web/app.py` to serve static files from `src/web/static/` (if not already)
3. Delete the `static/` directory if it's a duplicate

- [ ] **Step 1: Read `vercel.json` and update static file serving**

Change the static file route to point to `src/web/static/`.

- [ ] **Step 2: Read `src/web/app.py` and verify static file path**

Ensure it serves from `src/web/static/` (it should already).

- [ ] **Step 3: Check if `static/` directory exists and is a duplicate**

```bash
ls static/ 2>&1
```

If it exists and is a copy of `src/web/static/`, delete it.

- [ ] **Step 4: Run both gates**

Expected: 137 passed / 125 passed OK (config-only change).

- [ ] **Step 5: Test on `vercel dev` locally**

Verify UI loads correctly.

- [ ] **Step 6: Deploy to Vercel preview**

Verify UI loads correctly on the preview URL.

- [ ] **Step 7: Commit**

```bash
git add vercel.json src/web/app.py
git rm -r static/ 2>/dev/null || true
git commit -m "refactor(static): consolidate UI static files to src/web/static/"
```

---

### Task 4: Unify entrypoints

**Files:**
- Modify: `api/index.py` (import and wrap `src/web/app.py`)
- Evaluate: `src/shared/api_routes.py` (delete if redundant)

**Changes:**
1. Modify `api/index.py` to import the FastAPI app from `src/web/app.py` and wrap it for Vercel
2. Remove duplicate endpoint logic from `api/index.py`
3. Evaluate if the shared-router pattern is still needed; delete if redundant

- [ ] **Step 1: Read current `api/index.py` and `src/web/app.py`**

Understand the current structure and what needs to be unified.

- [ ] **Step 2: Modify `api/index.py` to wrap `src/web/app.py`**

Import the FastAPI app and adapt it to Vercel's handler format. Remove duplicate endpoint definitions.

- [ ] **Step 3: Evaluate if `src/shared/api_routes.py` is still needed**

If `api/index.py` now imports `src/web/app.py` (which includes the shared router), the shared-router pattern may be redundant. Evaluate and decide.

- [ ] **Step 4: Run both gates**

Expected: 137 passed / 125 passed OK (refactor only).

- [ ] **Step 5: Test on `vercel dev` locally**

Verify all endpoints work.

- [ ] **Step 6: Deploy to Vercel preview**

Verify all endpoints work on the preview URL.

- [ ] **Step 7: Commit**

```bash
git add api/index.py src/shared/api_routes.py
git commit -m "refactor(entrypoints): unify local and Vercel entrypoints"
```

---

### Task 5: Repurpose `python src/cli.py ui` to run `vercel dev`

**Files:**
- Modify: `src/cli.py` (change `ui` subcommand)
- Modify: `README.md` (update dev workflow)

**Changes:**
1. Modify the `ui` subcommand in `src/cli.py` to run `vercel dev` instead of `uvicorn`
2. Update `README.md` to document the new workflow

- [ ] **Step 1: Read `src/cli.py` and modify the `ui` subcommand**

Change the implementation to invoke `vercel dev` (via `subprocess.run` or similar).

- [ ] **Step 2: Update `README.md`**

Change the Quick Start section to reflect that `python src/cli.py ui` now runs `vercel dev`.

- [ ] **Step 3: Test the new workflow**

```bash
python src/cli.py ui
```

Verify it starts `vercel dev` and the app is accessible.

- [ ] **Step 4: Run both gates**

Expected: 137 passed / 125 passed OK (no test changes needed).

- [ ] **Step 5: Commit**

```bash
git add src/cli.py README.md
git commit -m "refactor(cli): repurpose 'ui' subcommand to run vercel dev"
```

---

### Task 6: Cleanup and documentation

**Files:**
- Modify: `CLAUDE.md` (update architecture documentation)
- Modify: `README.md` (update architecture documentation)
- Delete: any remaining dead code

**Changes:**
1. Update `CLAUDE.md` to reflect the new unified architecture
2. Update `README.md` to reflect the new architecture
3. Remove any dead code (old routes, duplicate files)

- [ ] **Step 1: Update `CLAUDE.md`**

Update the architecture section to describe the unified entrypoint, config-driven filesystem, and single static file directory.

- [ ] **Step 2: Update `README.md`**

Update the architecture section to match.

- [ ] **Step 3: Search for and remove dead code**

```bash
grep -r "output/{path}" src/ api/ 2>&1
grep -r "static/" src/ api/ 2>&1
```

Remove any references to the old paths.

- [ ] **Step 4: Run both gates**

Expected: 137 passed / 125 passed OK (docs-only change).

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md README.md
git commit -m "docs: update architecture documentation for unified deployment"
```

---

### Task 7: Final verification

- [ ] **Step 1: Run full gate set**

```bash
set -o pipefail
venv/Scripts/python.exe -m pytest tests/ -m "not live" --ignore=tests/e2e -q 2>&1 | tail -2
venv/Scripts/python.exe -m unittest discover tests 2>&1 | grep -E "^(Ran [0-9]+ tests|OK|FAILED|ERROR)"
venv/Scripts/python.exe scripts/run_e2e_baseline.py 2>&1 | tail -3
git checkout -- tests/e2e/screenshots
```

Expected: 137 passed / 125 OK / 16 passed 3 deselected.

- [ ] **Step 2: Verify no behavior change**

```bash
git diff --stat master..HEAD
```

Expected: only `src/config.py`, `src/shared/api_routes.py`, `src/web/app.py`, `api/index.py`, `vercel.json`, `src/cli.py`, `README.md`, `CLAUDE.md` changed.

- [ ] **Step 3: Verify clean tree**

```bash
git status --short
git log --oneline master..HEAD
```

Expected: only untracked files from `.gitignore`; six phase commits (one per task 1-6).

- [ ] **Step 4: Test on `vercel dev` one final time**

Verify the full workflow: UI loads, PDF generates, chat works.

- [ ] **Step 5: Deploy to Vercel production**

```bash
vercel --prod
```

Verify everything works on the production URL.

---

## Notes

- **Vercel CLI required:** `npm i -g vercel` must be run before starting this phase.
- **`vercel dev` vs `uvicorn`:** `vercel dev` is slower than `uvicorn` hot-reload, but it tests the actual deployment path. This is an acceptable tradeoff for architectural simplicity.
- **Data URI overhead:** 33% overhead on PDFs is acceptable for 2-page resumes (~100KB → ~133KB). Monitor user feedback.
- **Shared-router pattern:** After Task 4, evaluate if `src/shared/api_routes.py` is still needed. If `api/index.py` imports `src/web/app.py` (which includes the shared router), the pattern may be redundant. Delete if truly unnecessary.
- **Rollback plan:** each task is independently reversible. If a step breaks something, revert that commit.
