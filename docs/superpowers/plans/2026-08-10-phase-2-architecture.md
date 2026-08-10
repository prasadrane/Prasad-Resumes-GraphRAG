# Phase 2 — Architecture Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Break the resume_generator↔pdf_renderer import cycle, centralize path configuration, introduce an LLM-service facade, deduplicate the LLM tailoring logic in `resume_generator.py`, and unify the two FastAPI apps (`src/web/app.py`, `api/index.py`) on shared request models and a shared router — while keeping every existing test green and the E2E baseline untouched.

**Architecture:** Seven incremental tasks, each independently shippable: (1) a `src/config.py` single source of truth for repo paths; (2) extract markdown-parsing into `src/generators/resume_parser.py` so `pdf_renderer` no longer imports `resume_generator` (the real cycle); (3) an `src/llm/` service facade so generator/matcher modules stop importing the gateway directly; (4) collapse the duplicated summary/bullets LLM logic in `llm_tailor_resume` and `generate_raw_resume_stepwise` into shared helpers; (5) unified Pydantic request models in `src/shared/api_models.py` consumed by both apps; (6) a shared `APIRouter` for the identical `/api/query` and `/api/chat-stream` handlers; (7) security/robustness wrap-up folded from Phase 1 deferred findings (sanitized 500 details, `except HTTPException: raise`, `is_relative_to` in save-edit, rglob comment).

**Tech Stack:** Python 3.11.9 (venv at `venv/`), FastAPI, Pydantic, ReportLab, unittest, Playwright E2E baseline.

**Plan base:** master @ `dad5b2b`. Branch: `refactor/phase-2-architecture`.

**Import-graph findings that shape this plan (from exploration):**
- There is NO cycle between `ats_matcher` and `search_engine` — that edge is one-way (`ats_matcher → search_engine`; `serverless_gateway` imports nothing from `src/`). The spec's "circular import" manifests instead as `resume_generator ↔ pdf_renderer`: `pdf_renderer.py:30` imports `parse_resume_markdown` from `resume_generator`, while `generate_raw_resume_stepwise` needs `render_pdf_resume` and currently avoids the cycle with a lazy import at `resume_generator.py:787`.
- `search_engine.py` has mid-file imports at lines 36-37 (moved to top in Task 3).
- `ROOT_DIR` is recomputed from `__file__` in five modules (`app.py:15`, `resume_generator.py:44`, `ats_matcher.py:94`, `search_engine.py:13`, `static_graph_reader.py:14`) plus two bootstrap sites (`cli.py:13`, `api/index.py:13`).

## Global Constraints

These bind every task. Copy them verbatim into every task review.

1. **Python:** ALWAYS `venv/Scripts/python.exe` (Python 3.11.9). Shell is Git Bash on Windows. Never system python, never `py`.
2. **Full gate after EVERY task** — both commands must pass before committing:
   - Unit tests (pipefail-safe; never trust a bare `| tail` pipeline):
     ```bash
     set -o pipefail
     venv/Scripts/python.exe -m unittest discover tests 2>&1 | grep -E "^(Ran [0-9]+ tests|OK|FAILED|ERROR)"
     ```
     Expected: `Ran <N> tests` (N starts at 67 and grows as tasks add tests) and `OK`. Any `FAILED`/`ERROR` blocks the task.
   - E2E baseline:
     ```bash
     set -o pipefail
     venv/Scripts/python.exe scripts/run_e2e_baseline.py 2>&1 | tail -15
     ```
     Expected: `16 passed, 3 deselected` and exit code 0. The 3 deselected are LLM-dependent and must stay deselected.
3. **Screenshot drift:** every E2E run regenerates `tests/e2e/screenshots/baseline/*.png`. Before EVERY commit run `git checkout -- tests/e2e/screenshots` and confirm `git status` shows only intended files.
4. **Pinned patch targets — these exact dotted paths must keep working** (existing tests patch them):
   - `src.generators.resume_generator._call_llm_safe`
   - `src.query.search_engine.call_serverless_llm`
   - `src.query.serverless_gateway.call_serverless_llm`
   - `src.web.app.execute_graphrag_query` (until Task 6 moves the handler; Task 6 updates the test to `src.shared.api_routes.execute_graphrag_query`)
   - `src.web.app.ROOT_DIR` must remain importable (`tests/test_web_ui.py:10`)
5. **Pinned behaviors:** stepwise 8-step sequence `extracting_keywords(8) → loading_master(15) → selecting_summary(25) → tailoring_summary(38) → tailoring_bullets(55) → formatting(72) → rendering_pdf(88) → complete(100)` with strictly increasing percents and `complete` detail keys `raw_resume_path`/`raw_resume`/`pdf_path`; `llm_tailor_resume(parsed, master_content, company_name, jd_text, keywords)` signature; `execute_graphrag_query(query=..., mode=..., root_dir=...)` keyword call from the query handler; `/api/render_pdf` with `{"raw_text": ""}` → 400 on the Vercel app; app.py validation tests accept 400 OR 422 (this plan intentionally shifts several from 422 to 400 — within the pinned tolerance).
6. **Intentional, documented behavior changes** (reviewers: these are plan-mandated, not defects):
   - Empty-query/empty-company responses on app.py shift 422 → 400 (handler checks; tests accept both).
   - `api/index.py` `/api/render_pdf` + `/api/save-edit` accept the `content` alias field (parity with app.py).
   - `api/index.py` `/api/generate` + `/api/generate-stream` reject empty/whitespace company with 400 (parity with app.py).
   - `api/index.py` `/api/keywords` no longer 422s when `jd_text` is omitted (returns empty keyword list).
   - app.py `/api/save-edit` with a traversal `txt_url` returns 403 instead of a masked 500.
   - 500 responses no longer embed raw exception text (Task 7).
7. **Repo hygiene:** untracked files `CLAUDE.md`, `architecture_analysis.md`, `architecture_visualization.html` must STAY untracked — use explicit file paths in `git add`, never `git add -A` / `git add .`. Never touch `.env`, never rotate or print API keys, no git history rewriting.
8. **Expected noise (ignore):** `[WARN] ... Falling back` / `Using base content` lines in test output; post-commit hook warning `cannot spawn .git/hooks/post-commit`; LF→CRLF warnings; `git pull` failing with "Repository not found" (remote is broken; integration is local-merge only).
9. **No new dependencies.** No LLM calls in unit tests (everything mocked). No changes to `input/`, `output/`, GraphRAG artifacts, or the Playwright baseline scripts.
10. If plan text conflicts with a pinned behavior above, STOP and report the conflict rather than silently choosing.

---

### Task 1: Centralized configuration module (`src/config.py`)

**Files:**
- Create: `src/config.py`
- Create: `tests/test_config.py`
- Modify: `src/web/app.py` (lines 15-17, 87)
- Modify: `src/generators/resume_generator.py` (line 44, lines 759, 799)
- Modify: `src/query/search_engine.py` (line 13)
- Modify: `src/query/static_graph_reader.py` (lines 14-15)
- Modify: `src/generators/ats_matcher.py` (line 7 imports, line 94)
- Modify: `api/index.py` (line 30, line 57)

**Interfaces:**
- Produces: `src.config.ROOT_DIR` (Path, repo root), `src.config.INPUT_DIR`, `src.config.OUTPUT_DIR`, `src.config.MASTER_RESUME_PATH`, `src.config.WEB_STATIC_DIR`. Later tasks import these; `src/web/app.py` must keep names `ROOT_DIR`, `OUTPUT_DIR`, `STATIC_DIR` bound at module level.
- Bootstrap exceptions (deliberate, documented): `api/index.py:13-15` and `src/cli.py:13-15` compute their own `ROOT_DIR` because they must insert it into `sys.path` BEFORE any `src.*` import is possible. Do not change those lines.

- [ ] **Step 1: Write the failing test** — create `tests/test_config.py`:

```python
"""
Unit tests for centralized path configuration.
"""

import unittest

from src.config import ROOT_DIR, INPUT_DIR, OUTPUT_DIR, MASTER_RESUME_PATH, WEB_STATIC_DIR


class TestConfig(unittest.TestCase):

    def test_root_dir_is_repo_root(self):
        self.assertTrue((ROOT_DIR / "settings.yaml").exists())
        self.assertTrue((ROOT_DIR / "src").is_dir())

    def test_derived_paths(self):
        self.assertEqual(INPUT_DIR, ROOT_DIR / "input")
        self.assertEqual(OUTPUT_DIR, ROOT_DIR / "output")
        self.assertEqual(MASTER_RESUME_PATH, ROOT_DIR / "input" / "MASTER_RESUME.txt")
        self.assertEqual(WEB_STATIC_DIR, ROOT_DIR / "src" / "web" / "static")

    def test_web_app_root_dir_matches_config(self):
        from src.web.app import ROOT_DIR as APP_ROOT_DIR
        self.assertEqual(APP_ROOT_DIR, ROOT_DIR)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
venv/Scripts/python.exe -m unittest tests.test_config -v
```
Expected: FAIL/ERROR with `ModuleNotFoundError: No module named 'src.config'`.

- [ ] **Step 3: Create `src/config.py`**

```python
"""
config.py — Centralized path configuration for Prasad Resumes GraphRAG.

Single source of truth for repository-root-relative paths, replacing the
scattered per-module recomputation of ROOT_DIR from __file__.

Bootstrap exceptions: api/index.py and src/cli.py compute their own ROOT_DIR
before any src.* import, because they need it on sys.path first.
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
INPUT_DIR = ROOT_DIR / "input"
OUTPUT_DIR = ROOT_DIR / "output"
MASTER_RESUME_PATH = INPUT_DIR / "MASTER_RESUME.txt"
WEB_STATIC_DIR = ROOT_DIR / "src" / "web" / "static"
```

(`src/config.py` → `parent` = `src/`, `parent.parent` = repo root.)

- [ ] **Step 4: Switch `src/web/app.py` to config** — replace lines 15-17:

```python
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = ROOT_DIR / "output"
STATIC_DIR = Path(__file__).resolve().parent / "static"
```

with:

```python
from src.config import ROOT_DIR, OUTPUT_DIR, WEB_STATIC_DIR as STATIC_DIR
```

Keep `from pathlib import Path` (still used). In `get_default_resume_endpoint`, replace:

```python
    master_path = ROOT_DIR / "input" / "MASTER_RESUME.txt"
```

with:

```python
    from src.config import MASTER_RESUME_PATH
    master_path = MASTER_RESUME_PATH
```

(Put the `MASTER_RESUME_PATH` import with the other top imports instead of inline if preferred — but it must be at module top, not inside the handler. Use module-top: extend the Step-4 first import line to `from src.config import ROOT_DIR, OUTPUT_DIR, MASTER_RESUME_PATH, WEB_STATIC_DIR as STATIC_DIR`.)

- [ ] **Step 5: Switch `src/generators/resume_generator.py` to config** — replace line 44:

```python
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
```

with:

```python
from src.config import MASTER_RESUME_PATH, ROOT_DIR
```

Then replace BOTH occurrences of `master_path = ROOT_DIR / "input" / "MASTER_RESUME.txt"` (in `generate_raw_resume` ~line 759 and `generate_raw_resume_stepwise` ~line 799) with:

```python
    master_path = MASTER_RESUME_PATH
```

- [ ] **Step 6: Switch `src/query/search_engine.py` to config** — replace line 13:

```python
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
```

with:

```python
from src.config import ROOT_DIR
```

(Note: `execute_graphrag_query`'s default argument `root_dir: Path = ROOT_DIR` keeps working — the name is bound before the def.)

- [ ] **Step 7: Switch `src/query/static_graph_reader.py` to config** — replace lines 14-15:

```python
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = ROOT_DIR / "output"
```

with:

```python
from src.config import OUTPUT_DIR, ROOT_DIR
```

- [ ] **Step 8: Switch `src/generators/ats_matcher.py` to config** — change the import block (lines 5-9) to add the config import:

```python
import re
from typing import List
from pathlib import Path
from src.config import ROOT_DIR
from src.query.search_engine import execute_graphrag_query
from .constants import COMMON_ATS_KEYWORDS
```

and in `match_graphrag_stories` replace:

```python
        if root_dir is None:
            root_dir = Path(__file__).resolve().parent.parent.parent
```

with:

```python
        if root_dir is None:
            root_dir = ROOT_DIR
```

- [ ] **Step 9: Switch `api/index.py` static dir and master path to config** — after the existing `from src.generators...` imports (lines 17-20), add:

```python
from src.config import MASTER_RESUME_PATH, WEB_STATIC_DIR
```

Replace line 30:

```python
STATIC_DIR = ROOT_DIR / "src" / "web" / "static"
```

with:

```python
STATIC_DIR = WEB_STATIC_DIR
```

and in `get_default_resume_endpoint` replace:

```python
    master_path = ROOT_DIR / "input" / "MASTER_RESUME.txt"
```

with:

```python
    master_path = MASTER_RESUME_PATH
```

Leave the bootstrap `ROOT_DIR` at lines 13-15 untouched.

- [ ] **Step 10: Run new test to verify it passes**

```bash
venv/Scripts/python.exe -m unittest tests.test_config -v
```
Expected: 3 tests PASS.

- [ ] **Step 11: Run the full gate** (Global Constraints #2). Expected: unit tests `Ran 70 tests` / `OK`; E2E `16 passed, 3 deselected`.

- [ ] **Step 12: Restore screenshots and commit**

```bash
git checkout -- tests/e2e/screenshots
git add src/config.py tests/test_config.py src/web/app.py src/generators/resume_generator.py src/generators/ats_matcher.py src/query/search_engine.py src/query/static_graph_reader.py api/index.py
git status --short   # verify ONLY these files (+ nothing untracked) are staged
git commit -m "refactor(config): centralize path constants in src/config.py"
```

---

### Task 2: Extract `resume_parser` module — break the resume_generator↔pdf_renderer cycle

**Files:**
- Create: `src/generators/resume_parser.py`
- Create: `tests/test_resume_parser.py`
- Modify: `src/generators/resume_generator.py` (remove moved function bodies, add re-export imports, drop now-unused constants, hoist the lazy `render_pdf_resume` import)
- Modify: `src/generators/pdf_renderer.py` (line 30)

**Interfaces:**
- Consumes: `src/generators/constants.py` keys (`DEFAULT_CANDIDATE_NAME`, `DEFAULT_CANDIDATE_TITLE`, `MARKDOWN_BULLET_PREFIX`, `MARKDOWN_H1_PREFIX`, `MARKDOWN_H2_PREFIX`, `MARKDOWN_H3_PREFIX`, `MARKDOWN_H4_PREFIX`, `SECTION_CERTIFICATIONS`, `SECTION_EDUCATION`, `SECTION_EXPERIENCE`, `SECTION_SKILLS`, `SECTION_SKIP`, `SECTION_SKIP_SUMMARY_VARIANTS`, `SECTION_SUMMARY`), `src/generators/models.py` (`JobEntry`, `ResumeData`).
- Produces: `src.generators.resume_parser` with `clean_em_dashes`, `clean_link_url`, `parse_job_heading_components`, `create_job_entry`, `_parse_contact_line`, `extract_summary_variants`, `parse_resume_markdown`, `parse_master_resume` (alias). `src.generators.resume_generator` re-exports ALL of these names (tests and both web apps import several of them from `resume_generator`). `src.generators.pdf_renderer` imports `parse_resume_markdown` from `resume_parser` and keeps its `parse_raw_resume` alias. After this task, `pdf_renderer` imports NOTHING from `resume_generator`, and `resume_generator` imports `render_pdf_resume` at module top (no lazy import).

- [ ] **Step 1: Write the failing test** — create `tests/test_resume_parser.py`:

```python
"""
Unit tests for the extracted resume_parser module and the broken
resume_generator <-> pdf_renderer import cycle.
"""

import inspect
import unittest

from src.generators.resume_parser import (
    clean_em_dashes,
    extract_summary_variants,
    parse_resume_markdown,
)
from src.generators import resume_generator

SAMPLE = """# PRASAD RANE — MASTER RESUME
**Contact:** Chicago, IL | 555-0100 | prasad@example.com | [LinkedIn](https://linkedin.com/in/prasad)

## SUMMARY
### Canonical Summary
Software Engineer with 10+ years experience.

## EXPERIENCE
### Senior Software Engineer | Rocket Mortgage | Chicago, IL | Jan 2020 - Present
- Built microservices reducing latency by 40%.

## SKILLS
- Backend: Python, C#
"""


class TestResumeParser(unittest.TestCase):

    def test_parse_fields(self):
        data = parse_resume_markdown(SAMPLE)
        self.assertEqual(data.name, "PRASAD RANE")
        self.assertEqual(data.contact_location, "Chicago, IL")
        self.assertEqual(data.contact_phone, "555-0100")
        self.assertEqual(data.contact_email, "prasad@example.com")
        self.assertEqual(data.contact_linkedin, "https://linkedin.com/in/prasad")
        self.assertEqual(len(data.jobs), 1)
        self.assertEqual(data.jobs[0].company, "Rocket Mortgage")
        self.assertEqual(data.jobs[0].bullets, ["Built microservices reducing latency by 40%."])
        self.assertIn("Backend: Python, C#", data.skills)

    def test_extract_summary_variants(self):
        variants = extract_summary_variants(SAMPLE)
        self.assertIn("Canonical", variants)
        self.assertIn("Software Engineer with 10+ years experience.", variants["Canonical"])

    def test_clean_em_dashes_via_parser(self):
        self.assertNotIn("—", clean_em_dashes("Reduced alerts — improved response."))

    def test_resume_generator_reexports_are_identical(self):
        self.assertIs(resume_generator.parse_resume_markdown, parse_resume_markdown)
        self.assertIs(resume_generator.parse_master_resume, parse_resume_markdown)
        self.assertIs(resume_generator.clean_em_dashes, clean_em_dashes)

    def test_pdf_renderer_does_not_import_resume_generator(self):
        import src.generators.pdf_renderer as pr
        source = inspect.getsource(pr)
        self.assertNotIn("from .resume_generator import", source)
        self.assertIn("from .resume_parser import parse_resume_markdown", source)

    def test_pdf_renderer_alias_still_exported(self):
        from src.generators.pdf_renderer import parse_raw_resume
        self.assertIs(parse_raw_resume, parse_resume_markdown)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
venv/Scripts/python.exe -m unittest tests.test_resume_parser -v
```
Expected: FAIL/ERROR with `ModuleNotFoundError: No module named 'src.generators.resume_parser'`.

- [ ] **Step 3: Create `src/generators/resume_parser.py`** — move the following functions VERBATIM (byte-for-byte, no reformatting, no logic changes) out of `src/generators/resume_generator.py`, in this order: `clean_em_dashes`, `clean_link_url`, `parse_job_heading_components`, `create_job_entry`, `_parse_contact_line`, `extract_summary_variants`, `parse_resume_markdown`, and the alias line `parse_master_resume = parse_resume_markdown`. Identify each by its `def` line (line numbers can shift after Task 1 — trust the function names, not numbers). New file header and imports:

```python
"""
resume_parser.py — Markdown resume parsing into the ResumeData Pydantic model.

Extracted from resume_generator.py so that pdf_renderer.py can parse resumes
without importing the generator (breaking the generator <-> renderer import
cycle). Parsing only — no LLM, no tailoring, no I/O.
"""

import re
from typing import Dict, List

from .constants import (
    DEFAULT_CANDIDATE_NAME,
    DEFAULT_CANDIDATE_TITLE,
    MARKDOWN_BULLET_PREFIX,
    MARKDOWN_H1_PREFIX,
    MARKDOWN_H2_PREFIX,
    MARKDOWN_H3_PREFIX,
    MARKDOWN_H4_PREFIX,
    SECTION_CERTIFICATIONS,
    SECTION_EDUCATION,
    SECTION_EXPERIENCE,
    SECTION_SKILLS,
    SECTION_SKIP,
    SECTION_SKIP_SUMMARY_VARIANTS,
    SECTION_SUMMARY,
)
from .models import JobEntry, ResumeData
```

- [ ] **Step 4: Update `src/generators/resume_generator.py`** —
  (a) Remove the function bodies moved in Step 3 (including the `parse_master_resume = parse_resume_markdown` alias line).
  (b) Add this re-export import block where the old `from .models import JobEntry, ResumeData` line sits (keep that models import too — `ResumeData` is still used directly in this file):

```python
from .models import JobEntry, ResumeData
from .resume_parser import (
    _parse_contact_line,
    clean_em_dashes,
    clean_link_url,
    create_job_entry,
    extract_summary_variants,
    parse_job_heading_components,
    parse_master_resume,
    parse_resume_markdown,
)
```

  (c) In the `from .constants import (...)` block, remove `MARKDOWN_H4_PREFIX`, `SECTION_SKIP`, `SECTION_SKIP_SUMMARY_VARIANTS` (only the moved parser used them). All other names in that block stay.
  (d) Delete the lazy import inside `generate_raw_resume_stepwise` (the line `from .pdf_renderer import render_pdf_resume  # dynamic import to avoid circular dependency`) and add at module top, after the `.resume_parser` import block:

```python
from .pdf_renderer import render_pdf_resume
```

- [ ] **Step 5: Update `src/generators/pdf_renderer.py`** — replace line 30:

```python
from .resume_generator import parse_resume_markdown
```

with:

```python
from .resume_parser import parse_resume_markdown
```

Leave line 33 (`parse_raw_resume = parse_resume_markdown`) and its comment unchanged. `src/generators/__init__.py` needs NO changes.

- [ ] **Step 6: Run test to verify it passes**

```bash
venv/Scripts/python.exe -m unittest tests.test_resume_parser -v
```
Expected: 6 tests PASS.

- [ ] **Step 7: Run the full gate** (Global Constraints #2). Expected: unit tests `Ran 76 tests` / `OK`; E2E `16 passed, 3 deselected`.

- [ ] **Step 8: Restore screenshots and commit**

```bash
git checkout -- tests/e2e/screenshots
git add src/generators/resume_parser.py src/generators/resume_generator.py src/generators/pdf_renderer.py tests/test_resume_parser.py
git status --short
git commit -m "refactor(generators): extract resume_parser module, break renderer/generator import cycle"
```

---
### Task 3: LLM service facade + import hygiene

**Files:**
- Create: `src/llm/__init__.py`
- Create: `src/llm/service.py`
- Create: `tests/test_llm_service.py`
- Modify: `src/generators/resume_generator.py` (replace the `_call_llm_safe` function definition with an aliased import)
- Modify: `src/generators/ats_matcher.py` (fallback in `match_graphrag_stories`)
- Modify: `src/query/search_engine.py` (hoist mid-file imports at lines 36-37 to the top)

**Interfaces:**
- Produces: `src.llm.service.call_llm(prompt, system_prompt="", temperature=0.3, timeout=30) -> str` (raises on error) and `src.llm.service.call_llm_safe(...) -> str` (returns `""` on error, prints `[WARN] LLM tailoring call failed: {err}. Using base content.`). `src.generators.resume_generator._call_llm_safe` remains a patchable module attribute (aliased to `call_llm_safe`).
- The gateway import stays LAZY inside `call_llm` so (a) import-time failures don't move, and (b) existing tests that patch `src.query.serverless_gateway.call_serverless_llm` keep intercepting.
- `src.query.search_engine` keeps the name `call_serverless_llm` bound in its own namespace (tests patch `src.query.search_engine.call_serverless_llm`).

- [ ] **Step 1: Write the failing test** — create `tests/test_llm_service.py`:

```python
"""
Unit tests for the LLM service facade.
"""

import unittest
from unittest.mock import patch


class TestLLMService(unittest.TestCase):

    def test_call_llm_delegates_to_gateway(self):
        from src.llm.service import call_llm
        with patch("src.query.serverless_gateway.call_serverless_llm", return_value="ok") as mock_gateway:
            result = call_llm("hello prompt", system_prompt="hello system")
        self.assertEqual(result, "ok")
        mock_gateway.assert_called_once_with(
            prompt="hello prompt", system_prompt="hello system", temperature=0.3, timeout=30
        )

    def test_call_llm_safe_returns_empty_on_error(self):
        from src.llm.service import call_llm_safe
        with patch("src.query.serverless_gateway.call_serverless_llm", side_effect=RuntimeError("gateway down")):
            self.assertEqual(call_llm_safe("p", "s"), "")

    def test_call_llm_safe_passes_through_success(self):
        from src.llm.service import call_llm_safe
        with patch("src.query.serverless_gateway.call_serverless_llm", return_value="result text"):
            self.assertEqual(call_llm_safe("p", "s"), "result text")

    def test_resume_generator_safe_call_is_facade(self):
        from src.generators import resume_generator
        from src.llm.service import call_llm_safe
        self.assertIs(resume_generator._call_llm_safe, call_llm_safe)

    def test_ats_matcher_fallback_uses_facade(self):
        from src.generators import ats_matcher
        with patch("src.generators.ats_matcher.execute_graphrag_query", side_effect=RuntimeError("graphrag down")):
            with patch("src.query.serverless_gateway.call_serverless_llm", return_value="line one\nline two") as mock_gateway:
                result = ats_matcher.match_graphrag_stories(["Python"])
        self.assertEqual(result, ["line one", "line two"])
        self.assertTrue(mock_gateway.called)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
venv/Scripts/python.exe -m unittest tests.test_llm_service -v
```
Expected: FAIL/ERROR with `ModuleNotFoundError: No module named 'src.llm'`.

- [ ] **Step 3: Create `src/llm/__init__.py`**

```python
"""
llm package — Single LLM access facade for tailoring and matching modules.
"""

from .service import call_llm, call_llm_safe
```

- [ ] **Step 4: Create `src/llm/service.py`**

```python
"""
service.py — Single LLM access point for resume tailoring and story matching.

Wraps the serverless gateway behind a stable interface so generator/matcher
modules never import the gateway directly. The gateway import stays lazy
inside the call: failures surface at call time (not import time), and tests
that patch src.query.serverless_gateway.call_serverless_llm keep working.
"""


def call_llm(prompt: str, system_prompt: str = "", temperature: float = 0.3, timeout: int = 30) -> str:
    """Call the serverless LLM gateway. Raises on error; caller decides policy."""
    from src.query.serverless_gateway import call_serverless_llm
    return call_serverless_llm(prompt=prompt, system_prompt=system_prompt, temperature=temperature, timeout=timeout)


def call_llm_safe(prompt: str, system_prompt: str = "", temperature: float = 0.3, timeout: int = 30) -> str:
    """Safely call LLM with graceful fallback to empty string on error."""
    try:
        return call_llm(prompt=prompt, system_prompt=system_prompt, temperature=temperature, timeout=timeout)
    except Exception as err:
        print(f"[WARN] LLM tailoring call failed: {err}. Using base content.")
        return ""
```

- [ ] **Step 5: Rewire `src/generators/resume_generator.py`** — delete the entire `_call_llm_safe` function definition (the `def _call_llm_safe(...)` block that lazily imports the gateway and prints the `[WARN] LLM tailoring call failed` message) and put this import in its place (same location in the file, after `from .ats_matcher import extract_ats_keywords`):

```python
from src.llm.service import call_llm_safe as _call_llm_safe
```

Do not change any call sites — they already call `_call_llm_safe(prompt, system_prompt)` with two positional arguments, which keeps the pinned patch target and calling convention intact.

- [ ] **Step 6: Rewire `src/generators/ats_matcher.py` fallback** — in `match_graphrag_stories`, replace:

```python
        try:
            from src.query.serverless_gateway import call_serverless_llm
            res = call_serverless_llm(query_str, system_prompt="You are an ATS resume matcher. Extract matching resume bullets for the given keywords.")
```

with:

```python
        try:
            from src.llm.service import call_llm
            res = call_llm(query_str, system_prompt="You are an ATS resume matcher. Extract matching resume bullets for the given keywords.")
```

Leave the surrounding `except` blocks and `[WARN]` prints unchanged.

- [ ] **Step 7: Hoist `src/query/search_engine.py` mid-file imports** — delete these two lines from their mid-file position (currently lines 36-37, just above `@lru_cache`):

```python
from src.query.serverless_gateway import call_serverless_llm
from src.query.static_graph_reader import read_precomputed_entities, search_static_resume
```

and add the same two lines at the top of the file, immediately after `from typing import Callable, Optional` (and after the `from src.config import ROOT_DIR` line added in Task 1). No other changes — the names remain bound in the `src.query.search_engine` namespace.

- [ ] **Step 8: Run test to verify it passes**

```bash
venv/Scripts/python.exe -m unittest tests.test_llm_service -v
```
Expected: 5 tests PASS.

- [ ] **Step 9: Run the full gate** (Global Constraints #2). Expected: unit tests `Ran 81 tests` / `OK`; E2E `16 passed, 3 deselected`.

- [ ] **Step 10: Restore screenshots and commit**

```bash
git checkout -- tests/e2e/screenshots
git add src/llm/__init__.py src/llm/service.py tests/test_llm_service.py src/generators/resume_generator.py src/generators/ats_matcher.py src/query/search_engine.py
git status --short
git commit -m "refactor(llm): introduce llm.service facade; hoist search_engine imports"
```

---

### Task 4: Deduplicate LLM tailoring in `resume_generator.py`

**Files:**
- Create: `tests/test_tailoring_dedupe.py`
- Modify: `src/generators/resume_generator.py`

**Interfaces:**
- Consumes: `_call_llm_safe` (module attribute from Task 3), `_get_graphrag_context`, `_extract_gap_framing`, `_extract_top_metrics` (unchanged private helpers in the same file).
- Produces: module constants `SUMMARY_SYSTEM_PROMPT`, `BULLETS_SYSTEM_PROMPT`; functions `tailor_summary_with_llm(parsed, company_name, jd_text, graphrag_context, gap_framing, top_metrics) -> ResumeData` and `tailor_bullets_with_llm(parsed, company_name, jd_text, graphrag_context, gap_framing) -> ResumeData`. `llm_tailor_resume(parsed, master_content, company_name, jd_text, keywords)` keeps its exact signature. `generate_raw_resume_stepwise` keeps its exact 8-step yield contract.
- This is a pure refactor: the characterization test is written FIRST and must pass both before and after the change.

- [ ] **Step 1: Write the characterization test** — create `tests/test_tailoring_dedupe.py`:

```python
"""
Characterization test: the batch path (generate_raw_resume / llm_tailor_resume)
and the stepwise path (generate_raw_resume_stepwise) must produce byte-identical
raw resume text for identical inputs and identical mocked LLM responses.
This is the regression net for the tailoring dedupe.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.generators.resume_generator import generate_raw_resume, generate_raw_resume_stepwise

MOCK_LLM_RESPONSE = "Mocked tailoring content shared across both generation paths for dedupe verification."
JD_TEXT = "Senior engineer with Python, AWS, Kubernetes and Kafka experience."


class TestTailoringDedupe(unittest.TestCase):

    def _run_both_paths(self):
        with tempfile.TemporaryDirectory() as tmp_batch, tempfile.TemporaryDirectory() as tmp_step:
            with patch(
                "src.generators.resume_generator._call_llm_safe",
                return_value=MOCK_LLM_RESPONSE,
            ):
                batch_path = generate_raw_resume("DedupeCo", JD_TEXT, base_output_dir=Path(tmp_batch))
                batch_text = batch_path.read_text(encoding="utf-8")
                steps = list(generate_raw_resume_stepwise("DedupeCo", JD_TEXT, base_output_dir=Path(tmp_step)))
        return batch_text, steps

    def test_batch_and_stepwise_raw_resume_are_identical(self):
        batch_text, steps = self._run_both_paths()
        self.assertEqual(steps[-1][0], "complete")
        self.assertEqual(steps[-1][3]["raw_resume"], batch_text)

    def test_llm_called_with_two_positional_args(self):
        calls = []

        def spy(prompt, system_prompt):
            calls.append((prompt, system_prompt))
            return MOCK_LLM_RESPONSE

        with tempfile.TemporaryDirectory() as tmp:
            with patch("src.generators.resume_generator._call_llm_safe", side_effect=spy):
                generate_raw_resume("DedupeCo", JD_TEXT, base_output_dir=Path(tmp))

        self.assertGreaterEqual(len(calls), 1)
        self.assertIn("## Target Role", calls[0][0])
        self.assertIn("elite technical resume strategist", calls[0][1])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the characterization test — it must PASS against the current code** (green baseline before refactoring):

```bash
venv/Scripts/python.exe -m unittest tests.test_tailoring_dedupe -v
```
Expected: 2 tests PASS. If either fails here, STOP and report — the refactor must not start from a red baseline.

- [ ] **Step 3: Add shared constants and helpers to `src/generators/resume_generator.py`** — insert this block immediately BEFORE `def llm_tailor_resume(...)`. The two prompt constants are the EXACT strings currently built inline inside `llm_tailor_resume` (`summary_system = (...)` and `bullets_system = (...)`); copy them verbatim:

```python
# ── Shared LLM tailoring prompts (used by both batch and stepwise paths) ─────

SUMMARY_SYSTEM_PROMPT = (
    "You are an elite technical resume strategist who has placed 500+ senior engineers "
    "at top-tier technology companies. You specialize in transforming generic professional "
    "summaries into compelling, role-specific executive narratives that make hiring managers "
    "immediately see the candidate as the ideal hire.\n\n"
    "Your approach:\n"
    "- Lead with the candidate's single strongest quantified achievement relevant to THIS specific role\n"
    "- Mirror the job description's seniority language and domain terminology naturally\n"
    "- Weave in 2-3 specific metrics that demonstrate impact at the scale this role requires\n"
    "- Position the candidate as someone who has ALREADY solved the problems this role will face\n"
    "- Write in a confident, executive tone — not a mechanical skills inventory\n\n"
    "Strict rules:\n"
    "- Do NOT invent any facts, experiences, metrics, or technologies not in the source material\n"
    "- Do NOT produce a mechanical list of skills or technologies — write a compelling narrative\n"
    "- Do NOT use clichés: 'Results-driven', 'Highly motivated', 'Passionate about', 'Detail-oriented', "
    "'Proven track record of excellence'\n"
    "- Do NOT start with an adjective — start with the role title and years of experience\n"
    "- Preserve the exact career level and year count from the original\n"
    "- Keep length to 2-4 sentences (match the original summary length)\n"
    "- Return ONLY the rewritten summary paragraph — no labels, headers, quotes, or explanations\n"
)

BULLETS_SYSTEM_PROMPT = (
    "You are an elite technical resume strategist specializing in rewriting experience bullets "
    "to maximize relevance for a specific job description while preserving complete authenticity.\n\n"
    "Your approach:\n"
    "- Reorder bullets so the most JD-relevant achievements appear FIRST\n"
    "- Reframe each bullet to emphasize the aspects most relevant to the target role\n"
    "- Use the JD's exact technical terminology and domain language where the candidate has matching experience\n"
    "- Every bullet MUST follow: Strong Action Verb → Technical Context → Measurable Impact\n\n"
    "CRITICAL rules — violations will produce a rejected resume:\n"
    "- NEVER change, drop, round, or omit any number, percentage, time duration, or dollar amount\n"
    "  (e.g., '99.95%' must stay '99.95%', '40%' must stay '40%', '70% reduction' must stay '70% reduction')\n"
    "- NEVER invent new experiences, technologies, projects, or outcomes not in the originals\n"
    "- NEVER genericize specific technologies (e.g., do NOT turn 'DynamoDB' into 'NoSQL database', "
    "do NOT turn 'SemaphoreSlim' into 'concurrency control')\n"
    "- NEVER drop the problem statement or context — the reader needs to understand WHAT was broken/needed\n"
    "- Keep the EXACT same number of bullets as provided\n"
    "- Each bullet must start with a past-tense action verb (Led, Architected, Designed, Built, Diagnosed, etc.)\n"
    "- Return ONLY the rewritten bullets as plain text, one per line\n"
    "- No dashes, no numbering, no headers, no explanations\n"
)


def tailor_summary_with_llm(parsed: "ResumeData", company_name: str, jd_text: str,
                            graphrag_context: str, gap_framing: str, top_metrics: str) -> "ResumeData":
    """Re-word the executive summary via LLM. Mutates and returns parsed."""
    summary_prompt_parts = [
        f"## Target Role\nCompany: {company_name}\n",
        f"## Full Job Description\n{jd_text}\n",
        f"## Original Summary\n{parsed.summary}\n",
    ]

    if top_metrics:
        summary_prompt_parts.append(
            f"## Candidate's Strongest Impact Metrics (choose the most relevant for this role)\n{top_metrics}\n"
        )

    if graphrag_context:
        summary_prompt_parts.append(
            f"## Relevant Candidate Achievements (from Knowledge Graph)\n{graphrag_context}\n"
        )

    if gap_framing:
        summary_prompt_parts.append(
            f"## Skill Bridging Notes\n"
            f"For skills the JD requires that the candidate doesn't directly have, use these framing strategies:\n"
            f"{gap_framing}\n"
        )

    summary_prompt_parts.append(
        "Rewrite the summary to position this candidate as the ideal hire for this specific role. "
        "Return only the rewritten summary paragraph."
    )

    summary_prompt = "\n".join(summary_prompt_parts)
    llm_summary = _call_llm_safe(summary_prompt, SUMMARY_SYSTEM_PROMPT).strip()
    # Strip any wrapping quotes or markdown the LLM might add
    llm_summary = re.sub(r'^["\']|["\']$', '', llm_summary).strip()
    llm_summary = re.sub(r'^#+\s+.*\n', '', llm_summary).strip()
    if llm_summary and len(llm_summary) > 50:
        parsed.summary = llm_summary
    return parsed


def tailor_bullets_with_llm(parsed: "ResumeData", company_name: str, jd_text: str,
                            graphrag_context: str, gap_framing: str) -> "ResumeData":
    """Re-word and re-order experience bullets per job via LLM. Mutates and returns parsed."""
    for job in parsed.jobs:
        if not job.bullets:
            continue

        # Build story-grouped bullets text for richer context
        bullets_with_context = []
        current_story = ""
        for i, b in enumerate(job.bullets):
            story = job.bullet_stories[i] if i < len(job.bullet_stories) else ""
            if story and story != current_story:
                bullets_with_context.append(f"\n[Story Context: {story}]")
                current_story = story
            bullets_with_context.append(f"- {b}")

        bullets_text = "\n".join(bullets_with_context)

        bullets_prompt_parts = [
            f"## Target Role\nCompany: {company_name}\n",
            f"## Full Job Description\n{jd_text}\n",
            f"## Role Being Rewritten\n{job.title} at {job.company} ({job.dates})\n",
            f"## Original Bullets (with story context for your understanding — do not include story labels in output)\n{bullets_text}\n",
        ]

        if graphrag_context:
            bullets_prompt_parts.append(
                f"## Relevant Candidate Achievements (from Knowledge Graph)\n{graphrag_context}\n"
            )

        if gap_framing:
            bullets_prompt_parts.append(
                f"## Skill Bridging Notes\n{gap_framing}\n"
            )

        bullets_prompt_parts.append(
            f"Rewrite and reorder these {len(job.bullets)} bullets to maximize relevance for this JD. "
            f"Return exactly {len(job.bullets)} plain bullet lines (no dashes, no numbering)."
        )

        bullets_prompt = "\n".join(bullets_prompt_parts)
        llm_bullets_raw = _call_llm_safe(bullets_prompt, BULLETS_SYSTEM_PROMPT).strip()
        if llm_bullets_raw:
            # Parse LLM output lines, stripping leading dashes/bullets
            new_bullets = []
            for line in llm_bullets_raw.split("\n"):
                cleaned = re.sub(r"^[\s\-\*\•\·\d\.]+", "", line).strip()
                if cleaned:
                    new_bullets.append(cleaned)
            # Only apply if we got back a reasonable number of bullets
            if len(new_bullets) >= max(1, len(job.bullets) - 2):
                job.bullets = new_bullets[:len(job.bullets) + 2]  # Allow slight expansion, then PDF will trim

    return parsed
```

- [ ] **Step 4: Slim down `llm_tailor_resume`** — keep its docstring and signature exactly. Replace its entire body after the docstring with:

```python
    # ── Compute shared context (once, reused across all LLM calls) ──
    graphrag_context = _get_graphrag_context(jd_text, keywords)
    gap_framing = _extract_gap_framing(master_content, jd_text)
    top_metrics = _extract_top_metrics(parsed)

    # ── 1. LLM-Tailored Executive Summary ──
    parsed = tailor_summary_with_llm(parsed, company_name, jd_text, graphrag_context, gap_framing, top_metrics)

    # ── 2. LLM-Tailored Experience Bullets (per job) ──
    parsed = tailor_bullets_with_llm(parsed, company_name, jd_text, graphrag_context, gap_framing)

    return parsed
```

- [ ] **Step 5: Slim down `generate_raw_resume_stepwise`** — do NOT touch steps 1-3 (`extracting_keywords`, `loading_master`, `selecting_summary`), step 6 (`formatting`), step 7 (`rendering_pdf`), or step 8 (`complete`). Replace the bodies of step 4 and step 5 (everything between their `yield` lines and the next step's comment, i.e. remove the duplicated inline prompts and LLM logic) with:

```python
    # Step 4: tailoring_summary (38%)
    yield ("tailoring_summary", "LLM tailoring summary", 38, "LLM tailoring of executive summary to match target role...")
    if master_content:
        graphrag_context = _get_graphrag_context(jd_text, keywords)
        gap_framing = _extract_gap_framing(master_content, jd_text)
        top_metrics = _extract_top_metrics(parsed)
        parsed = tailor_summary_with_llm(parsed, company_name, jd_text, graphrag_context, gap_framing, top_metrics)
    else:
        graphrag_context = ""
        gap_framing = ""

    # Step 5: tailoring_bullets (55%)
    yield ("tailoring_bullets", "LLM tailoring experience bullets", 55, "LLM tailoring of experience bullets per job...")
    if master_content:
        parsed = tailor_bullets_with_llm(parsed, company_name, jd_text, graphrag_context, gap_framing)
```

- [ ] **Step 6: Re-run the characterization test — must still PASS**

```bash
venv/Scripts/python.exe -m unittest tests.test_tailoring_dedupe -v
```
Expected: 2 tests PASS.

- [ ] **Step 7: Run the full gate** (Global Constraints #2). Expected: unit tests `Ran 83 tests` / `OK`; E2E `16 passed, 3 deselected`. This verifies the pinned `tests/test_stepwise_generator.py` and `tests/test_resume_generator.py` suites (including the 5-JD distinctness test) against the deduped code.

- [ ] **Step 8: Restore screenshots and commit**

```bash
git checkout -- tests/e2e/screenshots
git add src/generators/resume_generator.py tests/test_tailoring_dedupe.py
git status --short
git commit -m "refactor(generators): deduplicate LLM tailoring into shared helpers"
```

---
### Task 5: Shared request models (`src/shared/api_models.py`)

**Files:**
- Create: `src/shared/__init__.py`
- Create: `src/shared/api_models.py`
- Create: `tests/test_api_models.py`
- Modify: `src/web/app.py` (drop local model classes, import shared ones)
- Modify: `api/index.py` (drop local model classes, import shared ones, add empty-company checks)

**Interfaces:**
- Produces: `src.shared.api_models.QueryRequest` (`query: str`, `mode: Optional[str] = "local"`), `src.shared.api_models.ResumeGenerationRequest` (`company: str`, `jd_text: str = ""`), `src.shared.api_models.SaveEditRequest` (`txt_url`, `raw_text`, `content`, `company` — all optional, `company` defaults to `"Tailored"`). Both apps consume these as their single API contract.
- Behavior changes are those listed in Global Constraints #6 (422→400 shifts on app.py; `content` alias and empty-company 400 on the Vercel app; `/api/keywords` accepts omitted `jd_text`).

- [ ] **Step 1: Write the failing test** — create `tests/test_api_models.py`:

```python
"""
Unit tests for the shared API request models and the unified Vercel contract.
"""

import unittest

from fastapi.testclient import TestClient

from src.shared.api_models import QueryRequest, ResumeGenerationRequest, SaveEditRequest


class TestSharedApiModels(unittest.TestCase):

    def test_query_request_defaults(self):
        req = QueryRequest(query="hello")
        self.assertEqual(req.mode, "local")

    def test_generation_request_defaults(self):
        req = ResumeGenerationRequest(company="Acme")
        self.assertEqual(req.jd_text, "")

    def test_save_edit_request_fields_optional(self):
        req = SaveEditRequest()
        self.assertIsNone(req.raw_text)
        self.assertIsNone(req.content)
        self.assertIsNone(req.txt_url)
        self.assertEqual(req.company, "Tailored")

    def test_vercel_render_pdf_accepts_content_alias(self):
        from api.index import app
        client = TestClient(app)
        raw = "# Prasad Rane\n\n## Professional Summary\nAlias field test.\n"
        response = client.post("/api/render_pdf", json={"content": raw})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["pdf_url"].startswith("data:application/pdf;base64,"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
venv/Scripts/python.exe -m unittest tests.test_api_models -v
```
Expected: FAIL/ERROR with `ModuleNotFoundError: No module named 'src.shared'`.

- [ ] **Step 3: Create `src/shared/__init__.py`**

```python
"""
shared package — Code shared by both FastAPI apps (src/web/app.py and api/index.py).
"""
```

- [ ] **Step 4: Create `src/shared/api_models.py`**

```python
"""
api_models.py — Shared Pydantic request models for both FastAPI apps.

Consumed by src/web/app.py (local UI server) and api/index.py (Vercel
serverless entrypoint) so the two apps expose one API contract. Handler
behavior stays environment-appropriate: the local app can write files via
txt_url, the serverless app renders from raw text only.
"""

from typing import Optional

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    query: str = Field(..., description="Question for GraphRAG knowledge graph")
    mode: Optional[str] = Field(default="local", description="Query mode: 'local' or 'global'")


class ResumeGenerationRequest(BaseModel):
    company: str = Field(..., description="Target company name")
    jd_text: str = Field(default="", description="Job description text")


class SaveEditRequest(BaseModel):
    txt_url: Optional[str] = Field(default=None, description="Relative URL or path to text file")
    raw_text: Optional[str] = Field(default=None, description="Updated raw resume text content")
    content: Optional[str] = Field(default=None, description="Updated raw resume text content (alias)")
    company: Optional[str] = Field(default="Tailored", description="Company name")
```

- [ ] **Step 5: Rewire `src/web/app.py`** —
  (a) Delete the local class definitions `class QueryRequest(BaseModel)`, `class GenerateRequest(BaseModel)`, and `class SaveEditRequest(BaseModel)` (keep `class ResumeHistoryItem` — it is app-specific).
  (b) Add with the top imports:

```python
from src.shared.api_models import QueryRequest, ResumeGenerationRequest, SaveEditRequest
```

  (c) Change `from pydantic import BaseModel, Field` to `from pydantic import BaseModel` (`Field` is no longer used in this file after the deletions).
  (d) In `generate_resume_endpoint` and `generate_resume_stream_endpoint`, change the parameter type `req: GenerateRequest` to `req: ResumeGenerationRequest`. No other handler changes — the existing explicit empty-company checks and `req.jd_text or ""` usages stay.
  (e) `query_endpoint`, `chat_stream_endpoint`, and `save_edit_endpoint` keep their bodies; only their request-model annotations now resolve to the shared classes (names are identical).

- [ ] **Step 6: Rewire `api/index.py`** —
  (a) Delete `class ResumeGenerationRequest(BaseModel)`, `class RenderPdfRequest(BaseModel)`, and `class QueryRequest(BaseModel)`.
  (b) Add with the top imports (after the existing `src.*` imports):

```python
from src.shared.api_models import QueryRequest, ResumeGenerationRequest, SaveEditRequest
```

  (c) In `render_pdf_endpoint`, change `req: RenderPdfRequest` to `req: SaveEditRequest` and replace:

```python
        text_content = req.raw_text or ""
```

with:

```python
        text_content = req.raw_text or req.content or ""
```

Leave the 400 check, `except HTTPException: raise`, and the rest of the handler unchanged.
  (d) In `generate_resume_endpoint`, add the empty-company guard and use the cleaned name:

```python
@app.post("/api/generate")
def generate_resume_endpoint(req: ResumeGenerationRequest):
    company_clean = req.company.strip()
    if not company_clean:
        raise HTTPException(status_code=400, detail="Company name cannot be empty.")
    try:
        temp_out_dir = Path(tempfile.gettempdir()) / "output"
        raw_path = generate_raw_resume(company_clean, req.jd_text, base_output_dir=temp_out_dir)
        pdf_target = raw_path.parent / "Prasad_Rane_Resume.pdf"
        render_pdf_resume(raw_path, pdf_target)

        pdf_bytes = pdf_target.read_bytes()
        b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
        pdf_data_uri = f"data:application/pdf;base64,{b64_pdf}"

        return {
            "status": "success",
            "pdf_url": pdf_data_uri,
            "raw_resume": raw_path.read_text(encoding="utf-8")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")
```

  (e) In `generate_resume_stream_endpoint`, add the same guard and use the cleaned name:

```python
@app.post("/api/generate-stream")
def generate_resume_stream_endpoint(req: ResumeGenerationRequest):
    import json
    import tempfile
    import base64
    company_clean = req.company.strip()
    if not company_clean:
        raise HTTPException(status_code=400, detail="Company name cannot be empty.")
    try:
        temp_out_dir = Path(tempfile.gettempdir()) / "output"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to resolve temp dir: {str(e)}")

    def event_generator():
        try:
            for step_id, label, pct, detail in generate_raw_resume_stepwise(
                company_name=company_clean, 
                jd_text=req.jd_text, 
                base_output_dir=temp_out_dir
            ):
                if step_id == "complete" and isinstance(detail, dict):
                    pdf_path = Path(detail["pdf_path"])
                    pdf_bytes = pdf_path.read_bytes()
                    b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
                    pdf_data_uri = f"data:application/pdf;base64,{b64_pdf}"
                    
                    complete_payload = {
                        "status": "success",
                        "company": company_clean,
                        "pdf_url": pdf_data_uri,
                        "txt_url": "",
                        "raw_resume": detail["raw_resume"]
                    }
                    yield f"data: {json.dumps({'step': step_id, 'label': label, 'progress': pct, 'detail': complete_payload})}\n\n"
                else:
                    yield f"data: {json.dumps({'step': step_id, 'label': label, 'progress': pct, 'detail': detail})}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'detail': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

  (f) `get_keywords` keeps its body (`req: ResumeGenerationRequest` annotation unchanged).

- [ ] **Step 7: Run test to verify it passes**

```bash
venv/Scripts/python.exe -m unittest tests.test_api_models -v
```
Expected: 4 tests PASS.

- [ ] **Step 8: Run the full gate** (Global Constraints #2). Expected: unit tests `Ran 87 tests` / `OK`; E2E `16 passed, 3 deselected`.

- [ ] **Step 9: Restore screenshots and commit**

```bash
git checkout -- tests/e2e/screenshots
git add src/shared/__init__.py src/shared/api_models.py tests/test_api_models.py src/web/app.py api/index.py
git status --short
git commit -m "refactor(api): unify request models in src/shared/api_models.py"
```

---

### Task 6: Shared router for `/api/query` and `/api/chat-stream`

**Files:**
- Create: `src/shared/api_routes.py`
- Create: `tests/test_shared_routes.py`
- Modify: `src/web/app.py` (delete the two handlers + now-unused imports, include router)
- Modify: `api/index.py` (delete the trailing block: imports, `QueryRequest`, both handlers; include router)
- Modify: `tests/test_web_ui.py` (one patch target update)

**Interfaces:**
- Produces: `src.shared.api_routes.shared_router` (APIRouter) exposing `POST /api/query` and `POST /api/chat-stream`, both implemented once. Handlers call `execute_graphrag_query(query=..., mode=..., root_dir=ROOT_DIR)` with `ROOT_DIR` from `src.config` (same Path value the apps already used).
- Test patch target moves: `/api/query` handler lives in `src.shared.api_routes`, so the patch target becomes `src.shared.api_routes.execute_graphrag_query`.

- [ ] **Step 1: Write the failing test** — create `tests/test_shared_routes.py`:

```python
"""
Unit tests that both FastAPI apps serve /api/query and /api/chat-stream from
the single shared router.
"""

import unittest


class TestSharedRoutes(unittest.TestCase):

    def _route_paths(self, app):
        return {getattr(r, "path", None) for r in app.routes}

    def test_local_app_exposes_shared_routes(self):
        from src.web.app import app
        paths = self._route_paths(app)
        self.assertIn("/api/query", paths)
        self.assertIn("/api/chat-stream", paths)

    def test_vercel_app_exposes_shared_routes(self):
        from api.index import app
        paths = self._route_paths(app)
        self.assertIn("/api/query", paths)
        self.assertIn("/api/chat-stream", paths)

    def test_both_apps_use_the_same_handler(self):
        from src.web.app import app as local_app
        from api.index import app as vercel_app
        from src.shared.api_routes import query_endpoint
        for app in (local_app, vercel_app):
            handlers = [r.endpoint for r in app.routes if getattr(r, "path", None) == "/api/query"]
            self.assertIn(query_endpoint, handlers)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
venv/Scripts/python.exe -m unittest tests.test_shared_routes -v
```
Expected: FAIL/ERROR with `ModuleNotFoundError: No module named 'src.shared.api_routes'`.

- [ ] **Step 3: Create `src/shared/api_routes.py`** — the handler bodies are the CURRENT index.py versions (None-safe `mode` handling); copy behavior exactly:

```python
"""
api_routes.py — Shared FastAPI router for endpoints identical across both apps.

Hosts /api/query and /api/chat-stream, previously duplicated verbatim in
src/web/app.py and api/index.py. Both apps include this router.
"""

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from src.config import ROOT_DIR
from src.query.search_engine import execute_graphrag_query
from src.query.static_graph_reader import read_precomputed_entities
from src.shared.api_models import QueryRequest

shared_router = APIRouter()


@shared_router.post("/api/query")
def query_endpoint(req: QueryRequest):
    """Execute GraphRAG query against Prasad's resumes knowledge graph."""
    query_clean = req.query.strip()
    if not query_clean:
        raise HTTPException(status_code=400, detail="Query string cannot be empty.")

    mode_clean = req.mode.lower().strip() if req.mode else "local"
    if mode_clean not in ["local", "global"]:
        mode_clean = "local"

    try:
        response_text = execute_graphrag_query(query=query_clean, mode=mode_clean, root_dir=ROOT_DIR)
        return {
            "status": "success",
            "query": query_clean,
            "mode": mode_clean,
            "response": response_text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@shared_router.post("/api/chat-stream")
def chat_stream_endpoint(req: QueryRequest):
    """Chat stream endpoint yielding sources and responses via SSE."""
    query_clean = req.query.strip()
    if not query_clean:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    mode_clean = req.mode.lower().strip() if req.mode else "local"
    if mode_clean not in ["local", "global"]:
        mode_clean = "local"

    def event_generator():
        try:
            # 1. Search sources
            keywords = [w.strip("?,.()\"'") for w in query_clean.lower().split() if len(w) > 3]
            entities = read_precomputed_entities()
            sources = []
            if entities and keywords:
                for entity in entities:
                    title = entity.get("title", "")
                    content = entity.get("content", "")
                    text = (title + " " + content).lower()
                    if any(kw in text for kw in keywords):
                        sources.append(title)
            sources = list(set(sources))[:5]

            # Emit sources
            yield f"event: sources\ndata: {json.dumps({'sources': sources})}\n\n"

            # 2. Get LLM response
            response_text = execute_graphrag_query(query=query_clean, mode=mode_clean, root_dir=ROOT_DIR)

            # Emit token/response
            yield f"event: token\ndata: {json.dumps({'token': response_text})}\n\n"

            # Emit done
            yield f"event: done\ndata: {json.dumps({'response': response_text, 'sources': sources})}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'detail': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

- [ ] **Step 4: Rewire `src/web/app.py`** —
  (a) Delete the `query_endpoint` function and the `chat_stream_endpoint` function entirely.
  (b) Delete the now-unused imports `from src.query.search_engine import execute_graphrag_query` and `from src.query.static_graph_reader import read_precomputed_entities`.
  (c) Add with the top imports: `from src.shared.api_routes import shared_router` and immediately after `app = FastAPI(...)` add:

```python
app.include_router(shared_router)
```

  (d) Keep everything else — static mount, `/`, `/api/default-resume`, `/api/history`, file-serving routes, `/api/generate`, `/api/generate-stream`, `/api/save-edit` + `/api/render_pdf`.

- [ ] **Step 5: Rewire `api/index.py`** —
  (a) Delete the trailing block: the `from src.query.search_engine import execute_graphrag_query` and `from src.query.static_graph_reader import read_precomputed_entities` imports, the `class QueryRequest(BaseModel)` definition, `chat_stream_endpoint`, and `query_endpoint`.
  (b) Add with the top imports: `from src.shared.api_routes import shared_router` and immediately after `app = FastAPI(...)` add:

```python
app.include_router(shared_router)
```

  (c) Clean now-unused imports: delete `from pydantic import BaseModel` and change `from typing import Optional, List` — after this task no code in `api/index.py` references `BaseModel`, `Optional`, or `List`, so remove both import lines entirely. Verify nothing else in the file uses them before removing.

- [ ] **Step 6: Update the patch target in `tests/test_web_ui.py`** — change:

```python
    @patch("src.web.app.execute_graphrag_query")
```

to:

```python
    @patch("src.shared.api_routes.execute_graphrag_query")
```

Make no other changes to this test file. The `root_dir=ROOT_DIR` assertion still holds because `src.web.app.ROOT_DIR` and `src.config.ROOT_DIR` are the same Path (Task 1), and `from src.web.app import app, ROOT_DIR` at line 10 keeps working.

- [ ] **Step 7: Run tests to verify they pass**

```bash
venv/Scripts/python.exe -m unittest tests.test_shared_routes tests.test_web_ui tests.test_vercel_api -v
```
Expected: all PASS (shared routes 3, web UI 13, vercel API 7).

- [ ] **Step 8: Run the full gate** (Global Constraints #2). Expected: unit tests `Ran 90 tests` / `OK`; E2E `16 passed, 3 deselected`.

- [ ] **Step 9: Restore screenshots and commit**

```bash
git checkout -- tests/e2e/screenshots
git add src/shared/api_routes.py tests/test_shared_routes.py src/web/app.py api/index.py tests/test_web_ui.py
git status --short
git commit -m "refactor(api): share /api/query and /api/chat-stream via shared_router"
```

---

### Task 7: Security & robustness wrap-up (Phase 1 deferred findings)

**Files:**
- Create: `tests/test_error_sanitization.py`
- Modify: `src/shared/api_routes.py` (sanitize the two handlers moved in Task 6)
- Modify: `src/web/app.py` (sanitize 500s, log server-side, `except HTTPException: raise` in save-edit, `is_relative_to` in save-edit, rglob comment)
- Modify: `api/index.py` (sanitize 500s, log server-side)
- Modify: `docs/superpowers/notes/phase-1-deferred-findings.md` (append resolution record)

**Interfaces:**
- Consumes: handlers at their final Task-6 locations.
- Produces: no raw exception text in any HTTP 500 `detail` or SSE `error` event of either app; server-side `logger.exception` records; 403 from the save-edit traversal guard surfaces as 403 (previously masked as 500); Phase 1 deferred findings 1-4 recorded as resolved.

- [ ] **Step 1: Write the failing test** — create `tests/test_error_sanitization.py`:

```python
"""
Regression tests: 500 responses and SSE error events must not leak raw
exception text, and the save-edit traversal guard must surface 403.
"""

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient


class TestErrorSanitization(unittest.TestCase):

    def test_local_query_500_does_not_leak_exception_text(self):
        from src.web.app import app
        client = TestClient(app)
        with patch(
            "src.shared.api_routes.execute_graphrag_query",
            side_effect=RuntimeError("SECRET_DB_PASSWORD"),
        ):
            response = client.post("/api/query", json={"query": "anything", "mode": "local"})
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("SECRET_DB_PASSWORD", response.json()["detail"])

    def test_vercel_generate_500_does_not_leak_exception_text(self):
        from api.index import app
        client = TestClient(app)
        with patch("api.index.generate_raw_resume", side_effect=RuntimeError("SECRET_API_KEY")):
            response = client.post("/api/generate", json={"company": "LeakCo", "jd_text": "Python"})
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("SECRET_API_KEY", response.json()["detail"])

    def test_save_edit_traversal_txt_url_returns_403_not_masked_500(self):
        from src.web.app import app
        client = TestClient(app)
        response = client.post("/api/save-edit", json={
            "txt_url": "/api/files/../../../../../../etc/passwd",
            "content": "malicious",
        })
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Access denied.")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
venv/Scripts/python.exe -m unittest tests.test_error_sanitization -v
```
Expected: the two leak tests FAIL (details currently embed exception text) and/or the traversal test FAILs (currently 500).

- [ ] **Step 3: Sanitize `src/shared/api_routes.py`** — add at the top:

```python
import logging

logger = logging.getLogger(__name__)
```

In `query_endpoint`, replace:

```python
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")
```

with:

```python
    except Exception:
        logger.exception("GraphRAG query failed")
        raise HTTPException(status_code=500, detail="Query failed. Please try again later.")
```

In `chat_stream_endpoint`'s `event_generator`, replace:

```python
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'detail': str(e)})}\n\n"
```

with:

```python
        except Exception:
            logger.exception("Chat stream failed")
            yield f"event: error\ndata: {json.dumps({'detail': 'Chat query failed. Please try again later.'})}\n\n"
```

- [ ] **Step 4: Sanitize `src/web/app.py`** — add at the top:

```python
import logging

logger = logging.getLogger(__name__)
```

(Place `import logging` with the stdlib imports and the `logger = ...` line after the imports.) Then:
  (a) `get_default_resume_endpoint`: replace `except Exception as e: raise HTTPException(status_code=500, detail=f"Failed to load default resume: {str(e)}")` with:

```python
    except Exception:
        logger.exception("Failed to load default resume")
        raise HTTPException(status_code=500, detail="Failed to load default resume.")
```

  (b) `generate_resume_endpoint`: replace the `except Exception` tail with:

```python
    except Exception:
        logger.exception("Resume generation failed")
        raise HTTPException(status_code=500, detail="Generation failed. Please try again later.")
```

  (c) `generate_resume_stream_endpoint`'s `event_generator`: replace `except Exception as e: yield f"event: error\ndata: {json.dumps({'detail': str(e)})}\n\n"` with:

```python
        except Exception:
            logger.exception("Resume generation stream failed")
            yield f"event: error\ndata: {json.dumps({'detail': 'Generation failed. Please try again later.'})}\n\n"
```

  (d) `save_edit_endpoint`: first replace the containment guard

```python
            if not str(target_txt).startswith(str(OUTPUT_DIR.resolve())):
                raise HTTPException(status_code=403, detail="Access denied.")
```

with:

```python
            if not target_txt.is_relative_to(OUTPUT_DIR.resolve()):
                raise HTTPException(status_code=403, detail="Access denied.")
```

then replace the final exception handler

```python
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update resume: {str(e)}")
```

with:

```python
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to update resume")
        raise HTTPException(status_code=500, detail="Failed to update resume.")
```

  (e) In `serve_pdf_legacy`, add this comment directly above the `matches = list(OUTPUT_DIR.rglob(...))` line:

```python
    # Company folders are nested under output/<date>/<company>/, so rglob is
    # required to locate the requested PDF at any nesting depth.
```

- [ ] **Step 5: Sanitize `api/index.py`** — add at the top with the imports:

```python
import logging
```

and after the imports:

```python
logger = logging.getLogger(__name__)
```

Then apply the same pattern to every remaining 500 handler:
  (a) `get_default_resume_endpoint`:

```python
    except Exception:
        logger.exception("Failed to load default resume")
        raise HTTPException(status_code=500, detail="Failed to load default resume.")
```

  (b) `generate_resume_endpoint`:

```python
    except Exception:
        logger.exception("Resume generation failed")
        raise HTTPException(status_code=500, detail="Generation failed. Please try again later.")
```

  (c) `render_pdf_endpoint` — keep the existing 400 detail and `except HTTPException: raise`; replace only the final handler:

```python
    except Exception:
        logger.exception("PDF rendering failed")
        raise HTTPException(status_code=500, detail="PDF rendering failed.")
```

  (d) `generate_resume_stream_endpoint` temp-dir guard:

```python
    except Exception:
        logger.exception("Failed to resolve temp dir")
        raise HTTPException(status_code=500, detail="Failed to resolve temp dir.")
```

  (e) `generate_resume_stream_endpoint`'s `event_generator`:

```python
        except Exception:
            logger.exception("Resume generation stream failed")
            yield f"event: error\ndata: {json.dumps({'detail': 'Generation failed. Please try again later.'})}\n\n"
```

- [ ] **Step 6: Run test to verify it passes**

```bash
venv/Scripts/python.exe -m unittest tests.test_error_sanitization -v
```
Expected: 3 tests PASS.

- [ ] **Step 7: Update the deferred-findings record** — append to `docs/superpowers/notes/phase-1-deferred-findings.md`:

```markdown

## Resolved in Phase 2 (branch refactor/phase-2-architecture, Task 7)

1. Exception-message leakage — all 500 handlers in both apps and the shared
   router now return generic details; exceptions are logged server-side via
   logger.exception.
2. `except Exception → 500` swallow — app.py `save_edit_endpoint` now
   re-raises HTTPException (its inner 403 guard previously got masked as 500).
3. Contract divergence — unified `SaveEditRequest` / `ResumeGenerationRequest`
   / `QueryRequest` in `src/shared/api_models.py`, consumed by both apps
   (Task 5); Vercel entrypoint accepts the `content` alias.
4. `rglob` comment — added to `serve_pdf_legacy`.
```

- [ ] **Step 8: Run the full gate** (Global Constraints #2). Expected: unit tests `Ran 93 tests` / `OK`; E2E `16 passed, 3 deselected`.

- [ ] **Step 9: Restore screenshots and commit**

```bash
git checkout -- tests/e2e/screenshots
git add tests/test_error_sanitization.py src/shared/api_routes.py src/web/app.py api/index.py docs/superpowers/notes/phase-1-deferred-findings.md
git status --short
git commit -m "fix(api): sanitize 500 details, re-raise HTTPException in save-edit, is_relative_to guard"
```

---

## Final Verification (after Task 7, before final review)

- [ ] Full unit gate from a clean shell: `Ran 93 tests` / `OK`.
- [ ] E2E baseline: `16 passed, 3 deselected`, exit 0.
- [ ] `git log --oneline dad5b2b..HEAD` shows exactly 7 task commits.
- [ ] `git status --short` clean except the deliberately untracked `CLAUDE.md`, `architecture_analysis.md`, `architecture_visualization.html`.
- [ ] Manual smoke (optional but recommended): `venv/Scripts/python.exe src/cli.py ui`, open http://127.0.0.1:8000, verify the Tailor tab loads, Default Resume preview renders, and the chat tab responds — matching the Phase 0/1 manual verification.
