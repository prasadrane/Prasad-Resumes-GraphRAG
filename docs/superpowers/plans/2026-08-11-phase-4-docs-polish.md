# Phase 4 — Documentation & Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix README gaps (env vars, proxy startup, API reference), remove hardcoded Windows paths, fix stale comments, add narrow type hints and extract a small set of magic numbers into named constants — all without behavior changes.

**Architecture:** Docs-first phase with minimal code touch. Zero behavior change. Every gate must remain green after each task.

**Tech Stack:** Markdown, YAML, Python type hints, existing `src/generators/constants.py` for magic-number extraction.

**Base:** master @ aface75 · **Branch:** `refactor/phase-4-docs-polish`

## Gate commands (this phase — unchanged from Phase 3)

```bash
set -o pipefail
venv/Scripts/python.exe -m pytest tests/ -m "not live" --ignore=tests/e2e -q   # expect: 138 passed
venv/Scripts/python.exe -m unittest discover tests 2>&1 | grep -E "^(Ran [0-9]+ tests|OK|FAILED|ERROR)"   # expect: Ran 126 tests / OK
venv/Scripts/python.exe scripts/run_e2e_baseline.py 2>&1 | tail -3              # expect: 16 passed, 3 deselected, exit 0
```

After every E2E run: `git checkout -- tests/e2e/screenshots` before committing.

## Global Constraints

1. **Zero behavior changes.** No runtime logic may change. Type hints and constants extraction are refactor-only.
2. **Python is always `venv/Scripts/python.exe`** (Git Bash on Windows). Never `python` or `py` bare.
3. **Both runners stay green** after every task: pytest (138) + unittest (126). E2E unchanged (16 passed, 3 deselected).
4. **No new dependencies.**
5. **Never commit `.env`.** Use explicit file paths in `git add` — never `git add -A` or `git add .`.
6. **Shell pipelines that gate on exit codes must use `set -o pipefail`.**
7. **Mock, never call, external services.**
8. **The hardcoded fallback `C:\Users\mamat\Github\Prasad-Resumes` is removed entirely** (user decision: no longer needed since all content is consolidated in `input/MASTER_RESUME.txt`).

---

## File Structure

| File | Responsibility | Task |
|---|---|---|
| `README.md` | Fix env vars, add proxy step, API ref, troubleshooting | 1 |
| `settings.yaml` | Fix header comment + backslash path separator | 2 |
| `src/cli.py` | Remove `get_default_source_dir()`, make `--source` required | 3 |
| `docker-compose.yml` | Replace hardcoded Windows mount path with env-substitutable relative path | 3 |
| `src/generators/constants.py` | Add named constants for margins, fonts, bold caps | 4 |
| `src/generators/pdf_styles.py` | Import constants instead of magic numbers | 4 |
| `src/generators/pdf_renderer.py` | Import constants instead of magic numbers | 4 |
| `src/generators/resume_generator.py` | Import constants instead of magic numbers | 4 |
| `src/cli.py`, `src/config.py`, `src/generators/ats_matcher.py`, `src/converters/pdf_parser.py`, `src/generators/models.py` | Add type hints to public functions | 5 |

---

### Task 1: README fixes

**Files:**
- Modify: `README.md`

**Changes:**
1. **Add `FREELLMAPI_API_KEY` and `GRAPHRAG_API_KEY` to `.env` sample** — the current sample only shows `OPENROUTER_API_KEY` and `GEMINI_API_KEY`.
2. **Add LiteLLM proxy startup step** — insert between venv activation and UI launch in Quick Start.
3. **Add API reference section** — list all `/api/*` endpoints with method, params, response.
4. **Add troubleshooting section** — common errors (missing keys, proxy not running, port conflicts).

- [ ] **Step 1: Update `.env` sample in README**

Replace the existing env block with:

```env
# Primary LLM Provider (OpenRouter API)
OPENROUTER_API_KEY=sk-or-v1-your_openrouter_api_key_here

# Fallback LLM Provider (Google Gemini AI Studio API)
GEMINI_API_KEY=your_gemini_api_key_here

# GraphRAG Indexer (points at Gemini via LiteLLM proxy)
GRAPHRAG_API_KEY=your_gemini_api_key_here

# FreeLLMAPI (primary model in settings.yaml, routed via LiteLLM proxy)
FREELLMAPI_API_KEY=your_freellmapi_api_key_here
```

- [ ] **Step 2: Add LiteLLM proxy step to Quick Start**

Insert after "Activate Virtual Environment":

```markdown
### 2. Start LiteLLM Proxy (required for GraphRAG indexing)
```powershell
python src/cli.py proxy
```
The proxy runs on port 8002 and routes `freellmapi-chat` → OpenRouter/Gemini fallback chain.
```

Renumber subsequent steps (UI → 3, generate → 4, query → 5, index → 6, tests → 7).

- [ ] **Step 3: Add API reference section**

```markdown
## API Reference

All endpoints are available on both the local server (`src/web/app.py`, port 8000) and Vercel (`api/index.py`).

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Web UI (local only) |
| `POST` | `/api/generate` | Generate tailored resume from company + JD text |
| `POST` | `/api/render_pdf` | Render PDF from raw resume markdown |
| `POST` | `/api/save-edit` | Save edited raw resume and re-render |
| `POST` | `/api/query` | GraphRAG Q&A query |
| `POST` | `/api/chat-stream` | Streaming chatbot (SSE) |
| `GET` | `/api/default-resume` | Get default master resume content |
| `GET` | `/output/{path}` | Serve generated PDFs (local only) |
```

- [ ] **Step 4: Add troubleshooting section**

```markdown
## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `graphrag index` fails with connection error | LiteLLM proxy not running | Start it: `python src/cli.py proxy` |
| Chatbot returns raw entity dump, no LLM synthesis | Missing `OPENROUTER_API_KEY` and `GEMINI_API_KEY` | Add at least one to `.env` |
| `Address already in use: 8000` | Another process on port 8000 | Kill it or use `python src/cli.py ui --port 8001` |
| `Address already in use: 8002` | LiteLLM proxy already running | Use the existing instance |
| PDF not generated on Vercel | Read-only filesystem | Output is auto-redirected to `/tmp/output` — check Vercel function logs |
```

- [ ] **Step 5: Run both gates**

```bash
set -o pipefail
venv/Scripts/python.exe -m pytest tests/ -m "not live" --ignore=tests/e2e -q 2>&1 | tail -2
venv/Scripts/python.exe -m unittest discover tests 2>&1 | grep -E "^(Ran [0-9]+ tests|OK|FAILED|ERROR)"
```

Expected: 138 passed / 126 passed OK (docs-only change, no test impact).

- [ ] **Step 6: Commit**

```bash
git add README.md
git commit -m "docs(readme): add env vars, proxy step, API reference, troubleshooting"
```

---

### Task 2: Fix settings.yaml comments

**Files:**
- Modify: `settings.yaml`

**Changes:**
1. Fix header comment (lines 1-2): says "LLM: Google Gemini" but primary model is `freellmapi-chat` (OpenRouter via FreeLLMAPI).
2. Fix `db_uri: output\lancedb` → `output/lancedb` (backslash → forward slash for cross-platform).

- [ ] **Step 1: Fix header comment**

Replace lines 1-2:
```yaml
### GraphRAG 2.5.0 Settings — Prasad Resumes Knowledge Graph
### LLM: Google Gemini (via LiteLLM) | Input: PDFs + Markdown converted to .txt
```
With:
```yaml
### GraphRAG 2.5.0 Settings — Prasad Resumes Knowledge Graph
### LLM: FreeLLMAPI → OpenRouter (via LiteLLM proxy) with Gemini fallback | Input: PDFs + Markdown converted to .txt
```

- [ ] **Step 2: Fix db_uri path separator**

Replace line 68:
```yaml
    db_uri: output\lancedb
```
With:
```yaml
    db_uri: output/lancedb
```

- [ ] **Step 3: Run both gates**

Expected: 138 passed / 126 passed OK (comment + path-separator only).

- [ ] **Step 4: Commit**

```bash
git add settings.yaml
git commit -m "fix(settings): correct header comment, use forward-slash db_uri path"
```

---

### Task 3: Remove hardcoded Windows paths

**Files:**
- Modify: `src/cli.py`
- Modify: `docker-compose.yml`

**Changes:**
1. Remove `get_default_source_dir()` function entirely. Make `--source` required on the `convert` subcommand.
2. Replace `C:/Users/mamat/Github/freellmapi:/app` in docker-compose with `${FREELLMAPI_PATH:-./freellmapi}:/app`.

- [ ] **Step 1: Remove `get_default_source_dir()` from cli.py**

Delete the function (lines 22-30). Remove the `os` import if it becomes unused (check: `os` is only used in `get_default_source_dir` — verify before removing).

- [ ] **Step 2: Make `--source` required**

Change:
```python
    convert_parser.add_argument(
        "--source",
        type=str,
        default=str(get_default_source_dir()),
        help="Source directory containing PDFs and MD files",
    )
```
To:
```python
    convert_parser.add_argument(
        "--source",
        type=str,
        required=True,
        help="Source directory containing PDFs and MD files",
    )
```

- [ ] **Step 3: Fix docker-compose.yml**

Replace:
```yaml
      - C:/Users/mamat/Github/freellmapi:/app
```
With:
```yaml
      - ${FREELLMAPI_PATH:-./freellmapi}:/app
```

- [ ] **Step 4: Update test_cli_main.py if needed**

The `test_convert_command` test passes `--source /tmp/src` explicitly, so it should still work. Verify no test relies on the default.

- [ ] **Step 5: Run both gates**

Expected: 138 passed / 126 passed OK.

- [ ] **Step 6: Commit**

```bash
git add src/cli.py docker-compose.yml tests/test_cli_main.py
git commit -m "refactor(cli): remove hardcoded Windows fallback path, make --source required"
```

---

### Task 4: Extract magic numbers into named constants

**Files:**
- Modify: `src/generators/constants.py` (add constants)
- Modify: `src/generators/pdf_styles.py` (use constants)
- Modify: `src/generators/pdf_renderer.py` (use constants)
- Modify: `src/generators/resume_generator.py` (use constants)

**Constants to extract (narrow scope — only where explaining comments already exist):**

| Constant | Value | Source file | Comment context |
|----------|-------|-------------|-----------------|
| `MARGIN_LEFT_RIGHT` | `0.55 * inch` | `pdf_styles.py` / `pdf_renderer.py` | "0.55\" L/R" |
| `MARGIN_TOP_BOTTOM` | `0.45 * inch` | `pdf_styles.py` / `pdf_renderer.py` | "0.45\" T/B" |
| `BOLD_CAP_PCT` | `20` | `resume_generator.py` | "<20% bold cap" |
| `MAX_BOLD_PHRASES_PER_BULLET` | `3` | `resume_generator.py` | "max 3 phrases/bullet" |
| `MAX_PAGES` | `2` | `pdf_styles.py` (PageCountCanvas) | "2-page constraint" |

- [ ] **Step 1: Read current `constants.py` and add new constants**

- [ ] **Step 2: Replace magic numbers in `pdf_styles.py`**

- [ ] **Step 3: Replace magic numbers in `pdf_renderer.py`**

- [ ] **Step 4: Replace magic numbers in `resume_generator.py`**

- [ ] **Step 5: Run both gates**

Expected: 138 passed / 126 passed OK (refactor only).

- [ ] **Step 6: Commit**

```bash
git add src/generators/constants.py src/generators/pdf_styles.py src/generators/pdf_renderer.py src/generators/resume_generator.py
git commit -m "refactor(generators): extract magic numbers into named constants"
```

---

### Task 5: Add type hints to public functions (narrow scope)

**Files:**
- Modify: `src/cli.py` — `main()`, `build_parser()`
- Modify: `src/config.py` — all exports
- Modify: `src/generators/ats_matcher.py` — `extract_ats_keywords()`, `match_graphrag_stories()`
- Modify: `src/converters/pdf_parser.py` — `extract_pdf_text()`
- Modify: `src/generators/models.py` — field types already exist via Pydantic; add return types if any methods lack them

**Scope:** ~20 functions. Add parameter and return type annotations. Do NOT add `from __future__ import annotations` — keep Python 3.11 style. Use `typing.Optional`, `list`, `tuple`, `Path` as needed.

- [ ] **Step 1: Add type hints to `src/cli.py`**

- [ ] **Step 2: Add type hints to `src/config.py`**

- [ ] **Step 3: Add type hints to `src/generators/ats_matcher.py`**

- [ ] **Step 4: Add type hints to `src/converters/pdf_parser.py`**

- [ ] **Step 5: Add type hints to `src/generators/models.py` (if any methods lack them)**

- [ ] **Step 6: Run both gates**

Expected: 138 passed / 126 passed OK (hints are runtime no-ops).

- [ ] **Step 7: Commit**

```bash
git add src/cli.py src/config.py src/generators/ats_matcher.py src/converters/pdf_parser.py src/generators/models.py
git commit -m "refactor(types): add type hints to public functions in cli, config, matchers, parser"
```

---

### Task 6: Final verification

- [ ] **Step 1: Run full gate set**

```bash
set -o pipefail
venv/Scripts/python.exe -m pytest tests/ -m "not live" --ignore=tests/e2e -q 2>&1 | tail -2
```
Expected: `138 passed`.

```bash
set -o pipefail
venv/Scripts/python.exe -m unittest discover tests 2>&1 | grep -E "^(Ran [0-9]+ tests|OK|FAILED|ERROR)"
```
Expected: `Ran 126 tests` / `OK`.

```bash
set -o pipefail
venv/Scripts/python.exe scripts/run_e2e_baseline.py 2>&1 | tail -3
git checkout -- tests/e2e/screenshots
```
Expected: `16 passed, 3 deselected`, exit 0.

- [ ] **Step 2: Verify no behavior change**

```bash
git diff --stat master..HEAD
```
Expected: only `README.md`, `settings.yaml`, `src/cli.py`, `docker-compose.yml`, `src/generators/*.py` changed. No new files under `tests/` (except possibly updated `test_cli_main.py`).

- [ ] **Step 3: Verify clean tree**

```bash
git status --short
git log --oneline master..HEAD
```
Expected: only `CLAUDE.md`, `architecture_analysis.md`, `architecture_visualization.html` untracked; five phase commits (one per task 1-5).

---

## Notes

- **`MASTER_RESUME.md` vs `.txt`:** The user mentioned "MASTER_RESUME.md" in their answer, but the actual file on disk is `input/MASTER_RESUME.txt`. Keep the `.txt` extension.
- **`os` import in cli.py:** After removing `get_default_source_dir()`, check if `os` is still used elsewhere. If not, remove the import.
- **docker-compose env var:** Users can set `FREELLMAPI_PATH` in `.env` or pass it inline: `FREELLMAPI_PATH=/path/to/freellmapi docker-compose up`.
