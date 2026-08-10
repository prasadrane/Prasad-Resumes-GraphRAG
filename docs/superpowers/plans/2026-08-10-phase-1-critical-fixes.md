# Phase 1 — Critical Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the four critical/high findings from the code review — path traversal in the legacy PDF route, the `req.content` AttributeError in the Vercel entrypoint, redundant PDF dependencies, and silent exception swallowing — each guarded by a regression test and verified against the Phase 0 E2E safety net.

**Architecture:** Minimal, surgical fixes on a dedicated branch. Every task follows the Phase 0 verification loop: make change → unit tests → E2E baseline → commit. The Phase 0 baseline (`scripts/run_e2e_baseline.py`) is the gate; any failure is a hard stop.

**Tech Stack:** Python 3.11 (project venv), FastAPI, pytest/pytest-playwright (E2E), unittest (unit tests).

**Governing spec:** `docs/superpowers/specs/2026-08-10-incremental-refactoring-e2e-safety-net-design.md` (Section 6, Phase 1).

## Global Constraints

- Always use `venv/Scripts/python.exe` (the project venv; never bare `python`/`pytest`). Shell is Git Bash on Windows.
- Work happens on branch `refactor/phase-1-critical-fixes`, created from `master`. Commit there; do not push.
- After EVERY task, run the full verification gate (both commands) and both must be green before committing:
  - `venv/Scripts/python.exe -m unittest discover tests` → expected: `OK`. The pre-existing `[WARN] ... Falling back / Using base content` lines from LLM-dependent unit tests are expected noise, NOT failures.
  - `venv/Scripts/python.exe scripts/run_e2e_baseline.py` → expected: all deterministic tests pass, 3 `live` tests deselected, exit code 0.
- Baseline/E2E tests NEVER call LLM APIs; only deterministic endpoints.
- Fixes are minimal and surgical: no drive-by refactors, no behavior changes beyond the stated fix. Duplication/architecture work belongs to Phase 2.
- Never commit `.env`; never rotate keys or rewrite git history (owner-deferred security follow-up, spec Section 9).
- E2E tests hitting the local server target `src.web.app:app` (NOT `api/index.py`), consumed via the session-scoped `app_server` fixture in `tests/e2e/conftest.py` which yields a base-URL string.
- Untracked files `CLAUDE.md`, `architecture_analysis.md`, `architecture_visualization.html` stay untracked — never add them to commits.

---

### Task 1: Fix path traversal in the legacy PDF route

**Files:**
- Create branch: `refactor/phase-1-critical-fixes` from `master`
- Create: `tests/e2e/test_security_regressions.py`
- Modify: `src/web/app.py:150-157` (`serve_pdf_legacy`)

**Interfaces:**
- Consumes: the `app_server` session fixture from `tests/e2e/conftest.py` (yields base-URL string; boots `src.web.app:app`).
- Produces: the fixed `serve_pdf_legacy` route; two E2E regression tests that every later phase runs against.

- [ ] **Step 1: Create the phase branch**

```bash
git checkout -b refactor/phase-1-critical-fixes
```

Expected: `Switched to a new branch 'refactor/phase-1-critical-fixes'` (from `master` @ `7030ad5` or later).

- [ ] **Step 2: Write the failing regression tests**

Create `tests/e2e/test_security_regressions.py`:

```python
"""
Phase 1 security regression tests for the local UI server (src.web.app:app).

These pin the fix to the legacy PDF route so a future refactor cannot
silently re-introduce path traversal or containment bypass.
"""

import httpx


def test_legacy_pdf_route_rejects_traversal_segments(app_server):
    # %2e%2e decodes to ".." server-side; kept percent-encoded so the HTTP
    # client does not normalize the dot segments away before sending.
    resp = httpx.get(f"{app_server}/api/pdf/%2e%2e/%2e%2e", timeout=30.0)
    assert resp.status_code == 403


def test_legacy_pdf_route_still_serves_real_pdfs(app_server):
    # Ensure the default resume artifacts exist first.
    prep = httpx.get(f"{app_server}/api/default-resume", timeout=120.0)
    assert prep.status_code == 200

    resp = httpx.get(
        f"{app_server}/api/pdf/Default/Prasad_Rane_Default_Resume.pdf",
        timeout=30.0,
    )
    assert resp.status_code == 200
    assert resp.headers.get("content-type", "").startswith("application/pdf")
    assert resp.content.startswith(b"%PDF")
```

- [ ] **Step 3: Run the new tests to verify the traversal test fails**

Run: `venv/Scripts/python.exe -m pytest tests/e2e/test_security_regressions.py -v` (allow up to 3 minutes; the app boots in a subprocess).
Expected: `test_legacy_pdf_route_rejects_traversal_segments` FAILS (current code returns 404, not 403); `test_legacy_pdf_route_still_serves_real_pdfs` PASSES. If the traversal test instead errors with 500, that is also an acceptable red state — it still must end at 403 after the fix.

- [ ] **Step 4: Apply the fix**

In `src/web/app.py`, replace the current `serve_pdf_legacy` function (lines 150-157):

```python
@app.get("/api/pdf/{company}/{filename}")
def serve_pdf_legacy(company: str, filename: str):
    """Legacy route: Serve requested PDF file."""
    # Find matching PDF file under company
    matches = list(OUTPUT_DIR.rglob(f"**/{company}/{filename}"))
    if not matches:
        raise HTTPException(status_code=404, detail="Requested PDF resume not found.")
    return FileResponse(str(matches[0]), media_type="application/pdf", filename=filename)
```

with:

```python
@app.get("/api/pdf/{company}/{filename}")
def serve_pdf_legacy(company: str, filename: str):
    """Legacy route: Serve requested PDF file."""
    # Reject traversal attempts before globbing user input
    if ".." in company or ".." in filename:
        raise HTTPException(status_code=403, detail="Access denied.")
    # Find matching PDF file under company
    matches = list(OUTPUT_DIR.rglob(f"**/{company}/{filename}"))
    if not matches:
        raise HTTPException(status_code=404, detail="Requested PDF resume not found.")
    target_file = matches[0].resolve()
    # Security check: ensure path is within OUTPUT_DIR (same guard as serve_output_file)
    if not str(target_file).startswith(str(OUTPUT_DIR.resolve())):
        raise HTTPException(status_code=403, detail="Access denied.")
    return FileResponse(str(target_file), media_type="application/pdf", filename=filename)
```

Do not modify anything else in the file.

- [ ] **Step 5: Run the regression tests to verify green**

Run: `venv/Scripts/python.exe -m pytest tests/e2e/test_security_regressions.py -v`
Expected: 2 passed.

- [ ] **Step 6: Run the full verification gate**

Run: `venv/Scripts/python.exe -m unittest discover tests`
Expected: `OK` (65 tests; `[WARN]` LLM-fallback lines are expected noise).

Run: `venv/Scripts/python.exe scripts/run_e2e_baseline.py` (allow up to 10 minutes)
Expected: all deterministic tests pass (now 16 — the 14 Phase 0 tests plus the 2 new security tests), 3 deselected, exit code 0.

If either is red, revert the change (`git checkout -- src/web/app.py tests/e2e/test_security_regressions.py`) and diagnose before proceeding.

- [ ] **Step 7: Commit**

```bash
git add src/web/app.py tests/e2e/test_security_regressions.py
git commit -m "fix(phase1): reject path traversal in legacy PDF route"
```

---

### Task 2: Fix `req.content` AttributeError in the Vercel entrypoint

**Files:**
- Modify: `api/index.py:115` (inside `render_pdf_endpoint`)
- Modify: `tests/test_vercel_api.py` (add two tests to `TestVercelAPI`)

**Interfaces:**
- Consumes: `api.index.app` via `fastapi.testclient.TestClient` — the same pattern `tests/test_vercel_api.py` already uses.
- Produces: a `render_pdf_endpoint` that returns 400 on empty input instead of a masked 500; two unittest regression tests.

**Background:** `RenderPdfRequest` (api/index.py:87-89) has only `raw_text` and `company` fields — no `content` field. Line 115 reads `req.raw_text or req.content or ""`; when `raw_text` is empty the `or` chain evaluates `req.content`, raising `AttributeError`, which the outer `except` masks as a 500. (The local `src/web/app.py` `SaveEditRequest` DOES have `content`, which is why only the serverless entrypoint is broken.)

- [ ] **Step 1: Write the failing regression tests**

Append these two methods inside the `TestVercelAPI` class in `tests/test_vercel_api.py` (after `test_query_endpoint_distinct_responses`, before the `if __name__` block):

```python
    def test_render_pdf_empty_text_returns_400(self):
        """Regression: empty raw_text must yield 400, not a masked 500 AttributeError."""
        response = self.client.post("/api/render_pdf", json={"raw_text": ""})
        self.assertEqual(response.status_code, 400)

    def test_render_pdf_with_text_returns_pdf_data_uri(self):
        raw = "# Prasad Rane\n\n## Professional Summary\nSenior software engineer.\n"
        response = self.client.post("/api/render_pdf", json={"raw_text": raw})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertTrue(data["pdf_url"].startswith("data:application/pdf;base64,"))
```

- [ ] **Step 2: Run the new tests to verify the empty-text test fails**

Run: `venv/Scripts/python.exe -m unittest tests.test_vercel_api.TestVercelAPI.test_render_pdf_empty_text_returns_400 tests.test_vercel_api.TestVercelAPI.test_render_pdf_with_text_returns_pdf_data_uri -v`
Expected: `test_render_pdf_empty_text_returns_400` FAILS (currently returns 500); `test_render_pdf_with_text_returns_pdf_data_uri` PASSES.

- [ ] **Step 3: Apply the fix**

In `api/index.py`, change line 115 inside `render_pdf_endpoint` from:

```python
        text_content = req.raw_text or req.content or ""
```

to:

```python
        text_content = req.raw_text or ""
```

Do not modify anything else in the file.

- [ ] **Step 4: Run the regression tests to verify green**

Run: `venv/Scripts/python.exe -m unittest tests.test_vercel_api -v`
Expected: all tests in the module pass (7 total: the 5 pre-existing plus the 2 new).

- [ ] **Step 5: Run the full verification gate**

Run: `venv/Scripts/python.exe -m unittest discover tests`
Expected: `OK` (now 67 tests; `[WARN]` LLM-fallback lines are expected noise).

Run: `venv/Scripts/python.exe scripts/run_e2e_baseline.py` (allow up to 10 minutes)
Expected: all deterministic tests pass, 3 deselected, exit code 0.

- [ ] **Step 6: Commit**

```bash
git add api/index.py tests/test_vercel_api.py
git commit -m "fix(phase1): use req.raw_text in serverless render_pdf endpoint"
```

---

### Task 3: Remove redundant PDF libraries from requirements-dev.txt

**Files:**
- Modify: `requirements-dev.txt` (remove `pdfplumber` and `pypdf` lines)

**Interfaces:**
- Produces: a slimmed dev requirements file. Only `pymupdf` is used by application code (`src/generators/pdf_renderer.py`); repo-wide verification (done at planning time) found no `pdfplumber`/`pypdf` imports anywhere under `src/` or `api/`.

- [ ] **Step 1: Verify no code imports the redundant libs**

Run: `grep -rniE "pdfplumber|pypdf" src/ api/ scripts/ tests/ || echo "NO_IMPORTS_FOUND"`
Expected: `NO_IMPORTS_FOUND`. If any import is found, STOP and report — do not remove the dependency.

- [ ] **Step 2: Remove the redundant lines**

Replace the contents of `requirements-dev.txt` with:

```
# Local Development, GraphRAG Indexing & Proxy Dependencies
-r requirements.txt
graphrag
litellm
lancedb
pymupdf

# E2E test stack (Phase 0 safety net)
pytest
pytest-playwright
httpx
```

(Only the `pdfplumber` and `pypdf` lines are removed; everything else is unchanged.)

Do NOT uninstall anything from the venv — this task edits the requirements file only. Installed copies remain harmless, and other tooling outside the app may use them.

- [ ] **Step 3: Run the full verification gate**

Run: `venv/Scripts/python.exe -m unittest discover tests`
Expected: `OK` (67 tests).

Run: `venv/Scripts/python.exe scripts/run_e2e_baseline.py` (allow up to 10 minutes)
Expected: all deterministic tests pass, 3 deselected, exit code 0.

- [ ] **Step 4: Commit**

```bash
git add requirements-dev.txt
git commit -m "chore(phase1): drop unused pdfplumber and pypdf from dev requirements"
```

---

### Task 4: Replace silent exception swallowing with logged warnings

**Files:**
- Modify: `src/query/static_graph_reader.py` (module imports + the two `except Exception: pass` blocks at lines ~22 and ~38)

**Interfaces:**
- Produces: the same fallback behavior as before, but with a logged warning (including traceback) whenever the precomputed entities JSON or the master resume cannot be read — instead of silently returning `[]` later in the chain.

- [ ] **Step 1: Add the logger**

In `src/query/static_graph_reader.py`, change the import block (lines 6-13) from:

```python
import os
import re
import json
from pathlib import Path
from typing import List, Dict, Any

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = ROOT_DIR / "output"
```

to:

```python
import os
import re
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = ROOT_DIR / "output"
```

- [ ] **Step 2: Replace the first silent swallow (JSON parse)**

In `read_precomputed_entities`, change:

```python
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
```

to:

```python
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            logger.warning(
                "Failed to parse %s; falling back to master resume sections.",
                json_path,
                exc_info=True,
            )
```

- [ ] **Step 3: Replace the second silent swallow (master resume read)**

In the same function, change:

```python
        except Exception:
            pass
            
    return []
```

to:

```python
        except Exception:
            logger.warning(
                "Failed to read %s; returning empty entity list.",
                master_resume,
                exc_info=True,
            )
            
    return []
```

Do not change any other logic — the fallback behavior is identical.

- [ ] **Step 4: Run the focused module tests**

Run: `venv/Scripts/python.exe -m unittest tests.test_static_graph_reader tests.test_search_engine -v`
Expected: all pass (behavior unchanged).

- [ ] **Step 5: Run the full verification gate**

Run: `venv/Scripts/python.exe -m unittest discover tests`
Expected: `OK` (67 tests).

Run: `venv/Scripts/python.exe scripts/run_e2e_baseline.py` (allow up to 10 minutes)
Expected: all deterministic tests pass, 3 deselected, exit code 0.

- [ ] **Step 6: Commit**

```bash
git add src/query/static_graph_reader.py
git commit -m "fix(phase1): log warnings instead of silently swallowing reader errors"
```

---

## Phase 1 Complete

Exit criteria — all must hold:
- Four commits on `refactor/phase-1-critical-fixes`: traversal fix, `req.content` fix, requirements cleanup, logged warnings.
- Full gate green at HEAD: `venv/Scripts/python.exe -m unittest discover tests` → `OK` (67 tests); `venv/Scripts/python.exe scripts/run_e2e_baseline.py` → all deterministic pass, 3 deselected, exit 0.
- No changes to `.env`, no key rotation, no history rewriting; `CLAUDE.md` and the two architecture files remain untracked.

The verification loop for every later phase is unchanged: make change → unit tests → `scripts/run_e2e_baseline.py` → screenshots → commit. Any red is a hard stop and revert.
