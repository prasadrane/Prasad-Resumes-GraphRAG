# Phase 3 — Testing & CI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fill the remaining test-coverage gaps (models, pdf_styles, pdf_parser, cli main), upgrade smoke tests to real assertions, add shared pytest fixtures, coverage tooling, and a GitHub Actions CI workflow — all without touching application code.

**Architecture:** Tests-only phase. `tests/conftest.py` gains shared fixtures; the canonical unit gate becomes pytest (which already collects all 93 existing unittest-style tests — verified); `coverage` measures `src/` and `api/`; `.github/workflows/ci.yml` runs unit+coverage+E2E baseline on push/PR. Zero changes under `src/` or `api/`.

**Tech Stack:** Python 3.11.9, pytest (already installed), coverage (new dev dependency), unittest (kept green for backwards compatibility), Playwright E2E baseline (Phase 0), GitHub Actions.

**Base:** master @ 8e8dc41 · **Branch:** `refactor/phase-3-testing-ci`

## Gate commands (this phase)

The canonical unit gate CHANGES in this phase (Task 1). From Task 1 onward:

```bash
set -o pipefail
venv/Scripts/python.exe -m pytest tests/ -m "not live" --ignore=tests/e2e -q   # unit gate (pytest)
venv/Scripts/python.exe -m unittest discover tests 2>&1 | grep -E "^(Ran [0-9]+ tests|OK|FAILED|ERROR)"   # backwards-compat gate
venv/Scripts/python.exe scripts/run_e2e_baseline.py 2>&1 | tail -3              # E2E gate
```

After every E2E run: `git checkout -- tests/e2e/screenshots` before committing.

## Global Constraints

1. **Zero application-code changes.** No file under `src/` or `api/` may be created, modified, or deleted by any task. Phase 3 touches only `tests/`, repo-root config files (`.coveragerc`, `.gitignore`, `requirements-dev.txt`, `pytest.ini`), and `.github/`.
2. **Python is always `venv/Scripts/python.exe`** (Git Bash on Windows). Never `python` or `py` bare.
3. **Both runners stay green:** the new pytest unit gate AND the legacy `python -m unittest discover tests` must pass after every task. New pytest-style test files (function-based, fixture-using) are invisible to unittest discovery — that is expected and the counts below account for it.
4. **Expected pytest unit-gate counts** (cumulative, `--ignore=tests/e2e`): Task 1 → 95, Task 2 → 115, Task 3 → 118, Task 4 → 129, Task 5 → 137, Task 6 → 137. **Expected unittest counts:** Task 1 → 93, Task 2 → 113, Task 3 → 113, Task 4 → 124, Task 5 → 125, Task 6 → 125. E2E gate always `16 passed, 3 deselected`, exit 0.
5. **No new runtime dependencies.** The only new dependency is `coverage`, added to `requirements-dev.txt`.
6. **Never commit `.env`.** Use explicit file paths in `git add` — never `git add -A` or `git add .`. The untracked files `CLAUDE.md`, `architecture_analysis.md`, `architecture_visualization.html` must remain untracked.
7. **Shell pipelines that gate on exit codes must use `set -o pipefail`.** Never bare `| tail` for a gate.
8. **Benign expected noise** (ignore, do not "fix"): post-commit hook `cannot spawn .git/hooks/post-commit`; LF→CRLF warnings; `git pull` failing with "Repository not found" (remote is broken — local-only workflow); `[WARN] ... Falling back` lines inside passing test output; baseline runs regenerating screenshots.
9. **Mock, never call, external services.** No test may hit a real LLM API, the network, or require `.env` keys. All LLM/query/proxy interactions are mocked.
10. **Test style rule:** files whose tests need fixtures (`test_conftest_fixtures.py`, `test_pdf_parser.py`, `test_static_graph_reader.py`) are pytest-style (plain functions with fixture parameters). All other new/modified test files stay `unittest.TestCase` so both runners see them.

---

## File Structure

| File | Responsibility | Task |
|---|---|---|
| `tests/conftest.py` | Shared pytest fixtures: sample JD text, sample master-resume text | 1 |
| `tests/test_conftest_fixtures.py` | Sanity checks that fixtures are wired and well-formed | 1 |
| `.coveragerc` | Coverage config: source = src + api, report options | 1 |
| `requirements-dev.txt` | Adds `coverage` | 1 |
| `.gitignore` | Adds coverage artifacts | 1 |
| `tests/test_models.py` | Pydantic model defaults, isolation, round-trip | 2 |
| `tests/test_pdf_styles.py` | HTML conversion, heading/contact formatting, styles dict, page-count canvas | 2 |
| `tests/test_pdf_parser.py` | Real-PDF extraction: valid, too-little-text, missing file | 3 |
| `tests/test_cli_main.py` | `main()` dispatch for every subcommand, mocked side effects | 4 |
| `tests/test_static_graph_reader.py` | Rewritten: real assertions over temp dirs (replaces 2 smoke tests) | 5 |
| `tests/test_ats_matcher.py` | `match_graphrag_stories` upgraded to 4 mocked-behavior tests | 5 |
| `.github/workflows/ci.yml` | Unit+coverage+E2E baseline on push/PR | 6 |

---

### Task 1: Test infra foundation — conftest fixtures, coverage config, pytest gate

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/test_conftest_fixtures.py`
- Create: `.coveragerc`
- Modify: `requirements-dev.txt`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: nothing (foundation task)
- Produces: fixture `sample_master_resume_text` (used by Tasks 3 and 5); `.coveragerc` (used by Task 6 CI); the pytest gate command for all later tasks

- [ ] **Step 1: Create `tests/conftest.py`**

```python
"""
Shared pytest fixtures for unit tests.

These fixtures are consumed by pytest-style test functions (see
tests/test_pdf_parser.py and tests/test_static_graph_reader.py).
unittest discovery ignores this file.
"""

import pytest


@pytest.fixture
def sample_master_resume_text() -> str:
    """Minimal master-resume document shaped like input/MASTER_RESUME.txt."""
    return (
        "# Prasad Rane\n"
        "Senior Software Engineer\n"
        "\n"
        "## SUMMARY\n"
        "Engineer with cloud, AI, and distributed systems experience.\n"
        "\n"
        "## EXPERIENCE\n"
        "- Built AWS ECS Fargate microservices with Python and Kafka.\n"
        "\n"
        "## SKILLS\n"
        "Python, AWS, Docker, Terraform, SQL\n"
    )
```

- [ ] **Step 2: Create `tests/test_conftest_fixtures.py`**

```python
"""
Sanity checks that shared conftest fixtures are wired and well-formed.
Pytest-style (fixture parameters); not collected by unittest discovery.
"""


def test_sample_master_resume_text_has_sections(sample_master_resume_text):
    assert sample_master_resume_text.startswith("# Prasad Rane")
    for section in ("## SUMMARY", "## EXPERIENCE", "## SKILLS"):
        assert section in sample_master_resume_text


def test_sample_master_resume_text_has_expected_content(sample_master_resume_text):
    assert "AWS ECS Fargate" in sample_master_resume_text
    assert "Python, AWS, Docker, Terraform, SQL" in sample_master_resume_text
```

- [ ] **Step 3: Create `.coveragerc` at repo root**

```ini
# Coverage configuration (Phase 3). Run with:
#   venv/Scripts/python.exe -m coverage run -m pytest tests/ -m "not live" --ignore=tests/e2e
#   venv/Scripts/python.exe -m coverage report -m
[run]
source =
    src
    api
omit =
    tests/*
    */tests/*
    venv/*
    .venv/*
    */site-packages/*

[report]
show_missing = true
skip_covered = false
exclude_lines =
    pragma: no cover
    if __name__ == "__main__":
```

- [ ] **Step 4: Add `coverage` to `requirements-dev.txt`**

Replace the final E2E block so the file ends with:

```text
# E2E test stack (Phase 0 safety net)
pytest
pytest-playwright
httpx

# Unit coverage tooling (Phase 3)
coverage
```

- [ ] **Step 5: Add coverage artifacts to `.gitignore`**

Append at the end of `.gitignore`:

```text

# Coverage reports (Phase 3)
.coverage
coverage.xml
htmlcov/
```

- [ ] **Step 6: Install coverage and verify both gates**

```bash
set -o pipefail
venv/Scripts/python.exe -m pip install coverage 2>&1 | tail -1
venv/Scripts/python.exe -m pytest tests/ -m "not live" --ignore=tests/e2e -q 2>&1 | tail -2
```

Expected: install succeeds; `95 passed` (93 existing + 2 new fixture tests).

```bash
set -o pipefail
venv/Scripts/python.exe -m unittest discover tests 2>&1 | grep -E "^(Ran [0-9]+ tests|OK|FAILED|ERROR)"
```

Expected: `Ran 93 tests` / `OK` (fixture tests are pytest-only, by design).

- [ ] **Step 7: Verify coverage runs and reports on src/ + api/**

```bash
set -o pipefail
venv/Scripts/python.exe -m coverage run -m pytest tests/ -m "not live" --ignore=tests/e2e -q 2>&1 | tail -2
venv/Scripts/python.exe -m coverage report 2>&1 | tail -8
```

Expected: `95 passed`; the report lists `src/...` and `api/index.py` rows with a TOTAL line. Confirm the `.coverage` file is git-ignored:

```bash
git status --short
```

Expected: only modified `requirements-dev.txt`, `.gitignore`, and new untracked plan/scratch files — NO `.coverage` entry and NO `tests/` unexpected entries other than the two new files.

- [ ] **Step 8: Commit**

```bash
git add tests/conftest.py tests/test_conftest_fixtures.py .coveragerc requirements-dev.txt .gitignore
git commit -m "test(infra): shared pytest fixtures, coverage config, pytest unit gate"
```

---

### Task 2: Tests for models.py and pdf_styles.py

**Files:**
- Create: `tests/test_models.py`
- Create: `tests/test_pdf_styles.py`

**Interfaces:**
- Consumes: `src.generators.models.JobEntry` / `ResumeData` (fields as defined in `src/generators/models.py`); `src.generators.pdf_styles` functions `markdown_to_reportlab_html`, `format_job_heading`, `format_contact_paragraph`, `get_resume_styles`, `create_section_header_flowables`, class `PageCountCanvas`
- Produces: nothing (leaf test task)

- [ ] **Step 1: Create `tests/test_models.py`**

```python
"""
Unit tests for src/generators/models.py (Pydantic resume data models).
"""

import unittest
from src.generators.models import JobEntry, ResumeData


class TestJobEntry(unittest.TestCase):

    def test_defaults(self):
        job = JobEntry()
        self.assertEqual(job.heading, "")
        self.assertEqual(job.title, "")
        self.assertEqual(job.company, "")
        self.assertEqual(job.location, "")
        self.assertEqual(job.dates, "")
        self.assertEqual(job.bullets, [])
        self.assertEqual(job.bullet_stories, [])

    def test_mutable_default_isolation(self):
        first, second = JobEntry(), JobEntry()
        first.bullets.append("Did things")
        first.bullet_stories.append("Story")
        self.assertEqual(second.bullets, [])
        self.assertEqual(second.bullet_stories, [])

    def test_field_assignment(self):
        job = JobEntry(
            heading="Engineer | Co | 2020",
            title="Engineer",
            company="Co",
            location="Remote",
            dates="2020 - Present",
            bullets=["Built X"],
        )
        self.assertEqual(job.title, "Engineer")
        self.assertEqual(job.company, "Co")
        self.assertEqual(job.bullets, ["Built X"])


class TestResumeData(unittest.TestCase):

    def test_defaults(self):
        data = ResumeData()
        self.assertEqual(data.name, "")
        self.assertEqual(data.summary, "")
        self.assertEqual(data.jobs, [])
        self.assertEqual(data.skills, [])
        self.assertEqual(data.certifications, [])
        self.assertEqual(data.education, [])

    def test_jobs_list_isolation(self):
        first, second = ResumeData(), ResumeData()
        first.jobs.append(JobEntry(company="A"))
        self.assertEqual(second.jobs, [])

    def test_round_trip(self):
        original = ResumeData(
            name="Alex Smith",
            jobs=[JobEntry(title="Lead", company="Google", bullets=["Led"])],
            skills=["Python"],
        )
        dumped = original.model_dump()
        restored = ResumeData.model_validate(dumped)
        self.assertEqual(restored.name, "Alex Smith")
        self.assertEqual(restored.jobs[0].company, "Google")
        self.assertEqual(restored.skills, ["Python"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to confirm green**

```bash
set -o pipefail
venv/Scripts/python.exe -m pytest tests/test_models.py -q 2>&1 | tail -2
```

Expected: `6 passed`.

- [ ] **Step 3: Create `tests/test_pdf_styles.py`**

```python
"""
Unit tests for src/generators/pdf_styles.py (ReportLab styling and HTML helpers).
"""

import io
import unittest
from contextlib import redirect_stdout

from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import HRFlowable, Paragraph

from src.generators.models import JobEntry, ResumeData
from src.generators.pdf_styles import (
    PageCountCanvas,
    create_section_header_flowables,
    format_contact_paragraph,
    format_job_heading,
    get_resume_styles,
    markdown_to_reportlab_html,
)


class TestMarkdownToReportlabHtml(unittest.TestCase):

    def test_bold_conversion(self):
        self.assertEqual(
            markdown_to_reportlab_html("Built **Python** services"),
            "Built <b>Python</b> services",
        )

    def test_italic_conversion(self):
        self.assertEqual(
            markdown_to_reportlab_html("Worked *remotely* abroad"),
            "Worked <i>remotely</i> abroad",
        )

    def test_link_conversion(self):
        result = markdown_to_reportlab_html("See [site](https://example.com)")
        self.assertIn('<a href="https://example.com">', result)
        self.assertIn('<font color="#0f3460">site</font></a>', result)

    def test_date_range_dash_preserved(self):
        result = markdown_to_reportlab_html("Jan 2020 — Feb 2022")
        self.assertEqual(result, "Jan 2020 - Feb 2022")

    def test_standalone_em_dash_becomes_period(self):
        # replace("—", ". ") keeps the surrounding spaces: "x — y" -> "x .  y"
        result = markdown_to_reportlab_html("Led team — improved uptime")
        self.assertNotIn("—", result)
        self.assertIn("Led team .", result)

    def test_empty_text(self):
        self.assertEqual(markdown_to_reportlab_html(""), "")


class TestFormatJobHeading(unittest.TestCase):

    def test_full_heading(self):
        job = JobEntry(title="Engineer", company="Co", location="Remote", dates="2020 - Present")
        result = format_job_heading(job)
        self.assertIn("<b>Engineer</b> | <b>Co</b>", result)
        self.assertIn("<i>Remote</i>", result)
        self.assertIn("<i>2020 - Present</i>", result)

    def test_title_only(self):
        job = JobEntry(title="Engineer")
        result = format_job_heading(job)
        self.assertIn("<b>Engineer</b>", result)
        self.assertNotIn("|", result)

    def test_fallback_to_raw_heading(self):
        job = JobEntry(heading="Raw heading text")
        self.assertEqual(format_job_heading(job), "Raw heading text")


class TestFormatContactParagraph(unittest.TestCase):

    def test_full_contact_line(self):
        data = ResumeData(
            contact_location="Remote",
            contact_phone="555-0100",
            contact_email="mailto:alex@example.com",
            contact_linkedin="linkedin.com/in/alex",
        )
        result = format_contact_paragraph(data)
        self.assertIn("Remote", result)
        self.assertIn("555-0100", result)
        # mailto: prefix stripped then re-added exactly once
        self.assertIn('<a href="mailto:alex@example.com">', result)
        self.assertNotIn("mailto:mailto:", result)
        # scheme-less LinkedIn gets https:// prefix in href only
        self.assertIn('<a href="https://linkedin.com/in/alex">', result)
        self.assertIn(">linkedin.com/in/alex</font>", result)

    def test_empty_contact(self):
        self.assertEqual(format_contact_paragraph(ResumeData()), "")


class TestStyleFactories(unittest.TestCase):

    def test_get_resume_styles_keys(self):
        styles = get_resume_styles()
        expected = {
            "name", "contact", "sec_header", "job_heading", "bullet",
            "summary", "skill", "cert", "edu",
        }
        self.assertEqual(set(styles.keys()), expected)
        for style in styles.values():
            self.assertIsInstance(style, ParagraphStyle)

    def test_create_section_header_flowables(self):
        styles = get_resume_styles()
        flowables = create_section_header_flowables("EXPERIENCE", styles["sec_header"])
        self.assertEqual(len(flowables), 2)
        self.assertIsInstance(flowables[0], HRFlowable)
        self.assertIsInstance(flowables[1], Paragraph)


class TestPageCountCanvas(unittest.TestCase):

    def test_warns_when_over_two_pages(self):
        buffer = io.BytesIO()
        page_canvas = PageCountCanvas(buffer)
        for _ in range(3):
            page_canvas.showPage()
        captured = io.StringIO()
        with redirect_stdout(captured):
            page_canvas.save()
        self.assertIn("exceeded 2-page constraint", captured.getvalue())

    def test_no_warning_at_two_pages(self):
        buffer = io.BytesIO()
        page_canvas = PageCountCanvas(buffer)
        for _ in range(2):
            page_canvas.showPage()
        captured = io.StringIO()
        with redirect_stdout(captured):
            page_canvas.save()
        self.assertEqual(captured.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: Run to confirm green**

```bash
set -o pipefail
venv/Scripts/python.exe -m pytest tests/test_pdf_styles.py -q 2>&1 | tail -2
```

Expected: `14 passed`.

- [ ] **Step 5: Run both gates**

```bash
set -o pipefail
venv/Scripts/python.exe -m pytest tests/ -m "not live" --ignore=tests/e2e -q 2>&1 | tail -2
venv/Scripts/python.exe -m unittest discover tests 2>&1 | grep -E "^(Ran [0-9]+ tests|OK|FAILED|ERROR)"
```

Expected: pytest `115 passed`; unittest `Ran 113 tests` / `OK`.

- [ ] **Step 6: Commit**

```bash
git add tests/test_models.py tests/test_pdf_styles.py
git commit -m "test(generators): cover models.py and pdf_styles.py"
```

---
### Task 3: Tests for pdf_parser.py (real PDFs)

**Files:**
- Create: `tests/test_pdf_parser.py`

**Interfaces:**
- Consumes: `src.converters.pdf_parser.extract_pdf_text` (signature `(pdf_path: Path) -> Tuple[bool, str]`); fixtures from Task 1 (`sample_master_resume_text`)
- Produces: nothing (leaf test task)

Note: this file is pytest-style (uses `tmp_path` and conftest fixtures) and is therefore not collected by unittest discovery — expected per Global Constraint 10.

- [ ] **Step 1: Create `tests/test_pdf_parser.py`**

```python
"""
Unit tests for src/converters/pdf_parser.py.

Builds real PDFs with ReportLab and extracts them with PyMuPDF, so the
full parse -> clean -> structure pipeline is exercised. Pytest-style
(uses tmp_path and conftest fixtures); not collected by unittest.
"""

from pathlib import Path

from reportlab.pdfgen import canvas as rl_canvas

from src.converters.pdf_parser import extract_pdf_text


def _make_pdf(pdf_path: Path, lines: list) -> None:
    """Render the given text lines into a single-page PDF."""
    page = rl_canvas.Canvas(str(pdf_path))
    y = 750
    for line in lines:
        if line.strip():
            page.drawString(72, y, line)
            y -= 20
    page.showPage()
    page.save()


def test_extract_valid_pdf_success(tmp_path, sample_master_resume_text):
    pdf_path = tmp_path / "resume.pdf"
    _make_pdf(pdf_path, sample_master_resume_text.split("\n"))

    success, result = extract_pdf_text(pdf_path)

    assert success is True
    assert "Prasad Rane" in result


def test_extract_too_little_text(tmp_path):
    pdf_path = tmp_path / "tiny.pdf"
    _make_pdf(pdf_path, ["Hello World"])

    success, result = extract_pdf_text(pdf_path)

    assert success is False
    assert result == "Too little text extracted (possibly image-only PDF)"


def test_extract_missing_file_returns_failure(tmp_path):
    success, result = extract_pdf_text(tmp_path / "does_not_exist.pdf")

    assert success is False
    assert isinstance(result, str)
    assert len(result) > 0
```

- [ ] **Step 2: Run to confirm green**

```bash
set -o pipefail
venv/Scripts/python.exe -m pytest tests/test_pdf_parser.py -v 2>&1 | tail -5
```

Expected: `3 passed`.

- [ ] **Step 3: Run both gates**

```bash
set -o pipefail
venv/Scripts/python.exe -m pytest tests/ -m "not live" --ignore=tests/e2e -q 2>&1 | tail -2
venv/Scripts/python.exe -m unittest discover tests 2>&1 | grep -E "^(Ran [0-9]+ tests|OK|FAILED|ERROR)"
```

Expected: pytest `118 passed`; unittest `Ran 113 tests` / `OK` (unchanged — pdf_parser tests are pytest-only).

- [ ] **Step 4: Commit**

```bash
git add tests/test_pdf_parser.py
git commit -m "test(converters): cover pdf_parser with real generated PDFs"
```

---

### Task 4: Tests for cli.py main()

**Files:**
- Create: `tests/test_cli_main.py`

**Interfaces:**
- Consumes: `src.cli.main`; mocks `src.cli.convert_documents`, `src.cli.check_proxy_health`, `src.cli.start_proxy_server`, `src.cli.generate_raw_resume`, `src.cli.render_pdf_resume`, `src.cli.execute_graphrag_query`, `src.cli.subprocess.run`, `uvicorn.run` (all imported into the `src.cli` namespace — patch them THERE)
- Produces: nothing (leaf test task)

- [ ] **Step 1: Create `tests/test_cli_main.py`**

```python
"""
Unit tests for src/cli.py main() dispatch. All side effects are mocked;
no subprocess, proxy, LLM, or file outside a temp dir is touched.
"""

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import ANY, MagicMock, patch

from src.cli import main


class TestCLIMain(unittest.TestCase):

    def _run_main(self, argv):
        with patch.object(sys, "argv", ["cli.py"] + argv):
            main()

    def test_convert_command(self):
        with patch("src.cli.convert_documents", return_value={"converted": 2}) as mock_conv:
            captured = io.StringIO()
            with redirect_stdout(captured):
                self._run_main(["convert", "--source", "/tmp/src", "--force"])
        mock_conv.assert_called_once_with(Path("/tmp/src"), ANY, force=True)
        self.assertIn("[CLI] Conversion complete", captured.getvalue())

    def test_index_command_success(self):
        with patch("src.cli.check_proxy_health", return_value=True), \
             patch("src.cli.subprocess.run", return_value=MagicMock(returncode=0)) as mock_run:
            self._run_main(["index"])
        cmd = mock_run.call_args[0][0]
        self.assertIn("graphrag", cmd)
        self.assertIn("index", cmd)

    def test_index_command_failure_exits(self):
        with patch("src.cli.check_proxy_health", return_value=True), \
             patch("src.cli.subprocess.run", return_value=MagicMock(returncode=2)):
            with self.assertRaises(SystemExit) as ctx:
                self._run_main(["index"])
        self.assertEqual(ctx.exception.code, 2)

    def test_proxy_command(self):
        with patch("src.cli.start_proxy_server") as mock_start:
            self._run_main(["proxy", "--port", "8005"])
        mock_start.assert_called_once()
        self.assertEqual(mock_start.call_args[1]["port"], 8005)

    def test_generate_with_jd_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            jd_file = tmp_path / "jd.txt"
            jd_file.write_text("Need Python and AWS experience.", encoding="utf-8")
            raw_path = tmp_path / "raw_resume.txt"

            with patch("src.cli.generate_raw_resume", return_value=raw_path) as mock_gen, \
                 patch("src.cli.render_pdf_resume") as mock_render:
                self._run_main(["generate", "--company", "Google", "--jd-file", str(jd_file)])

            mock_gen.assert_called_once_with("Google", "Need Python and AWS experience.")
            mock_render.assert_called_once_with(raw_path, tmp_path / "Prasad_Rane_Resume.pdf")

    def test_generate_missing_jd_file_exits(self):
        with self.assertRaises(SystemExit) as ctx:
            self._run_main(["generate", "--company", "Google", "--jd-file", "/nonexistent/jd.txt"])
        self.assertEqual(ctx.exception.code, 1)

    def test_generate_empty_jd_exits(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            jd_file = Path(tmp_dir) / "jd.txt"
            jd_file.write_text("   \n", encoding="utf-8")
            with self.assertRaises(SystemExit) as ctx:
                self._run_main(["generate", "--company", "Google", "--jd-file", str(jd_file)])
        self.assertEqual(ctx.exception.code, 1)

    def test_query_command_success(self):
        with patch("src.cli.check_proxy_health", return_value=True), \
             patch("src.cli.execute_graphrag_query", return_value="ANSWER TEXT") as mock_query:
            captured = io.StringIO()
            with redirect_stdout(captured):
                self._run_main(["query", "--mode", "global", "Career trajectory?"])
        self.assertEqual(mock_query.call_args[0], ("Career trajectory?", "global"))
        self.assertIn("ANSWER TEXT", captured.getvalue())

    def test_query_command_failure_exits(self):
        with patch("src.cli.check_proxy_health", return_value=True), \
             patch("src.cli.execute_graphrag_query", side_effect=RuntimeError("boom")):
            with self.assertRaises(SystemExit) as ctx:
                self._run_main(["query", "anything"])
        self.assertEqual(ctx.exception.code, 1)

    def test_ui_command(self):
        with patch("uvicorn.run") as mock_run:
            self._run_main(["ui", "--port", "8123"])
        mock_run.assert_called_once_with(
            "src.web.app:app", host="127.0.0.1", port=8123, reload=False
        )

    def test_no_command_prints_help(self):
        captured = io.StringIO()
        with redirect_stdout(captured):
            self._run_main([])
        self.assertIn("usage:", captured.getvalue().lower())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to confirm green**

```bash
set -o pipefail
venv/Scripts/python.exe -m pytest tests/test_cli_main.py -q 2>&1 | tail -2
```

Expected: `11 passed`.

- [ ] **Step 3: Run both gates**

```bash
set -o pipefail
venv/Scripts/python.exe -m pytest tests/ -m "not live" --ignore=tests/e2e -q 2>&1 | tail -2
venv/Scripts/python.exe -m unittest discover tests 2>&1 | grep -E "^(Ran [0-9]+ tests|OK|FAILED|ERROR)"
```

Expected: pytest `129 passed`; unittest `Ran 124 tests` / `OK`.

- [ ] **Step 4: Commit**

```bash
git add tests/test_cli_main.py
git commit -m "test(cli): cover main() dispatch for all subcommands"
```

---
### Task 5: Upgrade smoke tests to real assertions

**Files:**
- Rewrite: `tests/test_static_graph_reader.py` (replaces 2 smoke tests with 7 real tests)
- Modify: `tests/test_ats_matcher.py` (replaces the `test_match_graphrag_stories` smoke test with 4 mocked-behavior tests; the two `extract_ats_keywords` tests stay unchanged)

**Interfaces:**
- Consumes: `src.query.static_graph_reader.read_precomputed_entities` / `search_static_graph` (module-level names `OUTPUT_DIR` and `ROOT_DIR` are imported from `src.config` — patch them on the READER module: `src.query.static_graph_reader.OUTPUT_DIR` / `src.query.static_graph_reader.ROOT_DIR`); `src.generators.ats_matcher.match_graphrag_stories` with mocks at `src.generators.ats_matcher.execute_graphrag_query` and `src.llm.service.call_llm` (the fallback import happens inside the except block, so patch the source module); Task 1 fixture `sample_master_resume_text`
- Produces: nothing (leaf test task)

Note: the rewritten `test_static_graph_reader.py` is pytest-style (uses `tmp_path` and `monkeypatch`) and is therefore not collected by unittest discovery — expected per Global Constraint 10.

- [ ] **Step 1: Rewrite `tests/test_static_graph_reader.py` entirely**

```python
"""
Unit tests for src/query/static_graph_reader.py.

All file I/O is redirected at temp directories by patching the module-level
OUTPUT_DIR / ROOT_DIR names the reader resolves at call time. Pytest-style
(uses tmp_path, monkeypatch, conftest fixtures); not collected by unittest.
"""

import json

import src.query.static_graph_reader as reader


def _patch_dirs(monkeypatch, out_dir, root_dir):
    monkeypatch.setattr(reader, "OUTPUT_DIR", out_dir)
    monkeypatch.setattr(reader, "ROOT_DIR", root_dir)


def test_reads_entities_from_json(tmp_path, monkeypatch):
    out_dir = tmp_path / "output"
    out_dir.mkdir()
    entities = [{"title": "Experience", "content": "Built AWS services"}]
    (out_dir / "graph_entities.json").write_text(json.dumps(entities), encoding="utf-8")
    _patch_dirs(monkeypatch, out_dir, tmp_path)

    assert reader.read_precomputed_entities() == entities


def test_malformed_json_falls_back_to_master_resume(
    tmp_path, monkeypatch, sample_master_resume_text
):
    out_dir = tmp_path / "output"
    out_dir.mkdir()
    (out_dir / "graph_entities.json").write_text("{ not valid json", encoding="utf-8")
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "MASTER_RESUME.txt").write_text(sample_master_resume_text, encoding="utf-8")
    _patch_dirs(monkeypatch, out_dir, tmp_path)

    entities = reader.read_precomputed_entities()

    assert len(entities) == 4
    assert entities[0]["title"] == "Prasad Rane"
    assert "AWS ECS Fargate" in entities[2]["content"]


def test_no_artifacts_returns_empty_list(tmp_path, monkeypatch):
    out_dir = tmp_path / "output"
    out_dir.mkdir()
    _patch_dirs(monkeypatch, out_dir, tmp_path)

    assert reader.read_precomputed_entities() == []


def test_search_matches_case_insensitive(tmp_path, monkeypatch):
    out_dir = tmp_path / "output"
    out_dir.mkdir()
    entities = [{"title": "Experience", "content": "Built AWS ECS Fargate services"}]
    (out_dir / "graph_entities.json").write_text(json.dumps(entities), encoding="utf-8")
    _patch_dirs(monkeypatch, out_dir, tmp_path)

    matched = reader.search_static_graph(["aws"])

    assert len(matched) == 1
    assert "Built AWS ECS Fargate services" in matched[0]


def test_search_caps_results_at_ten(tmp_path, monkeypatch):
    out_dir = tmp_path / "output"
    out_dir.mkdir()
    entities = [
        {"title": f"Job {i}", "content": "python engineering work"} for i in range(12)
    ]
    (out_dir / "graph_entities.json").write_text(json.dumps(entities), encoding="utf-8")
    _patch_dirs(monkeypatch, out_dir, tmp_path)

    matched = reader.search_static_graph(["python"])

    assert len(matched) == 10


def test_search_truncates_matches_to_300_chars(tmp_path, monkeypatch):
    out_dir = tmp_path / "output"
    out_dir.mkdir()
    entities = [{"title": "Big", "content": "aws " + "x" * 500}]
    (out_dir / "graph_entities.json").write_text(json.dumps(entities), encoding="utf-8")
    _patch_dirs(monkeypatch, out_dir, tmp_path)

    matched = reader.search_static_graph(["aws"])

    assert len(matched) == 1
    assert len(matched[0]) == 300


def test_search_empty_keywords_returns_empty(tmp_path, monkeypatch):
    out_dir = tmp_path / "output"
    out_dir.mkdir()
    entities = [{"title": "Experience", "content": "Built AWS services"}]
    (out_dir / "graph_entities.json").write_text(json.dumps(entities), encoding="utf-8")
    _patch_dirs(monkeypatch, out_dir, tmp_path)

    assert reader.search_static_graph([]) == []
```

- [ ] **Step 2: Run to confirm green**

```bash
set -o pipefail
venv/Scripts/python.exe -m pytest tests/test_static_graph_reader.py -v 2>&1 | tail -9
```

Expected: `7 passed`.

- [ ] **Step 3: Rewrite `tests/test_ats_matcher.py` entirely**

```python
"""
Unit tests for ATS keyword extraction and GraphRAG matching module.
"""

import unittest
from unittest.mock import patch

from src.generators.ats_matcher import extract_ats_keywords, match_graphrag_stories


class TestATSMatcher(unittest.TestCase):

    def test_extract_ats_keywords(self):
        jd_text = """
        We are seeking a Senior Software Engineer with strong experience in Python, AWS, GraphRAG,
        and Microservices architecture. Experience with CI/CD, Kubernetes, and SQL is required.
        """
        keywords = extract_ats_keywords(jd_text)
        self.assertIn("Python", keywords)
        self.assertIn("AWS", keywords)
        self.assertIn("GraphRAG", keywords)
        self.assertIn("Kubernetes", keywords)

    def test_extract_ats_keywords_empty(self):
        self.assertEqual(extract_ats_keywords(""), [])

    def test_match_splits_response_lines(self):
        with patch(
            "src.generators.ats_matcher.execute_graphrag_query",
            return_value="Line one\n\nLine two\n",
        ) as mock_query:
            matches = match_graphrag_stories(["AWS", "Python"])
        self.assertEqual(matches, ["Line one", "Line two"])
        mock_query.assert_called_once()

    def test_match_empty_response_returns_empty(self):
        with patch(
            "src.generators.ats_matcher.execute_graphrag_query", return_value=""
        ):
            self.assertEqual(match_graphrag_stories(["AWS"]), [])

    def test_match_falls_back_to_llm_on_query_error(self):
        with patch(
            "src.generators.ats_matcher.execute_graphrag_query",
            side_effect=RuntimeError("graph offline"),
        ), patch("src.llm.service.call_llm", return_value="Fallback line") as mock_llm:
            matches = match_graphrag_stories(["AWS"])
        self.assertEqual(matches, ["Fallback line"])
        mock_llm.assert_called_once()

    def test_match_empty_keywords_skips_query(self):
        with patch("src.generators.ats_matcher.execute_graphrag_query") as mock_query:
            self.assertEqual(match_graphrag_stories([]), [])
        mock_query.assert_not_called()


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: Run to confirm green**

```bash
set -o pipefail
venv/Scripts/python.exe -m pytest tests/test_ats_matcher.py -v 2>&1 | tail -8
```

Expected: `6 passed` (2 unchanged keyword tests + 4 upgraded matcher tests).

- [ ] **Step 5: Run both gates**

```bash
set -o pipefail
venv/Scripts/python.exe -m pytest tests/ -m "not live" --ignore=tests/e2e -q 2>&1 | tail -2
venv/Scripts/python.exe -m unittest discover tests 2>&1 | grep -E "^(Ran [0-9]+ tests|OK|FAILED|ERROR)"
```

Expected: pytest `137 passed`; unittest `Ran 125 tests` / `OK`.

- [ ] **Step 6: Commit**

```bash
git add tests/test_static_graph_reader.py tests/test_ats_matcher.py
git commit -m "test: upgrade static_graph_reader and ats_matcher smoke tests to real assertions"
```

---
### Task 6: GitHub Actions CI workflow

**Files:**
- Create: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: the Task 1 coverage commands (`coverage run -m pytest ...`, `coverage report`, `coverage xml`), `scripts/run_e2e_baseline.py`
- Produces: CI running unit + coverage + E2E baseline on every push/PR once the remote is reachable

**Known limitation (document, do not attempt to fix):** the git remote is currently broken (`git pull` fails with "Repository not found"), so this workflow cannot actually execute on GitHub yet. Verification for this task is a LOCAL simulation of the exact CI command sequence. The workflow will activate automatically once the remote is restored.

- [ ] **Step 1: Create `.github/workflows/ci.yml`**

```yaml
name: CI

on:
  push:
    branches: [master]
  pull_request:

jobs:
  unit-and-e2e:
    runs-on: ubuntu-latest
    steps:
      - name: Check out repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements-dev.txt

      - name: Install Playwright browser
        run: python -m playwright install chromium --with-deps

      - name: Unit tests with coverage
        run: |
          coverage run -m pytest tests/ -m "not live" --ignore=tests/e2e
          coverage report -m
          coverage xml

      - name: E2E baseline (deterministic, no LLM keys needed)
        run: python scripts/run_e2e_baseline.py

      - name: Upload coverage report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: coverage-report
          path: coverage.xml
```

Notes baked into this workflow (verified facts, do not re-litigate):
- No `.env` or API keys exist in CI. The app boots without them: keys are read lazily via `os.getenv` only inside LLM-calling functions (`src/query/serverless_gateway.py:32-33`), and the deterministic E2E baseline never reaches those paths. `load_dotenv()` is a no-op when `.env` is absent.
- The E2E fixture picks a free port and launches via `sys.executable` — portable to ubuntu-latest. `--with-deps` installs Chromium's system libraries.
- The screenshot-capture test regenerates screenshots inside the CI working copy; nothing is committed from CI.

- [ ] **Step 2: Validate YAML syntax**

```bash
set -o pipefail
venv/Scripts/python.exe -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml', encoding='utf-8')); print('YAML OK')"
```

Expected: `YAML OK`.

- [ ] **Step 3: Locally simulate the CI unit+coverage step**

```bash
set -o pipefail
venv/Scripts/python.exe -m coverage run -m pytest tests/ -m "not live" --ignore=tests/e2e 2>&1 | tail -2
venv/Scripts/python.exe -m coverage report 2>&1 | tail -5
venv/Scripts/python.exe -m coverage xml && ls -la coverage.xml
```

Expected: `137 passed`; report TOTAL line; `coverage.xml` created.

- [ ] **Step 4: Locally simulate the CI E2E step**

```bash
set -o pipefail
venv/Scripts/python.exe scripts/run_e2e_baseline.py 2>&1 | tail -3
git checkout -- tests/e2e/screenshots
```

Expected: `16 passed, 3 deselected`, exit 0.

- [ ] **Step 5: Confirm clean tree**

```bash
git status --short
```

Expected: only the new `.github/` files staged/untracked; NO `.coverage` or `coverage.xml` entries (both gitignored since Task 1).

- [ ] **Step 6: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: run unit tests with coverage and E2E baseline on push/PR"
```

---

## Final Verification (after all tasks, before integration)

Run the complete gate set on the finished branch:

```bash
set -o pipefail
venv/Scripts/python.exe -m pytest tests/ -m "not live" --ignore=tests/e2e -q 2>&1 | tail -2
```
Expected: `137 passed`.

```bash
set -o pipefail
venv/Scripts/python.exe -m unittest discover tests 2>&1 | grep -E "^(Ran [0-9]+ tests|OK|FAILED|ERROR)"
```
Expected: `Ran 125 tests` / `OK`.

```bash
set -o pipefail
venv/Scripts/python.exe -m coverage run -m pytest tests/ -m "not live" --ignore=tests/e2e -q 2>&1 | tail -1
venv/Scripts/python.exe -m coverage report 2>&1 | tail -3
```
Expected: `137 passed`; TOTAL coverage line over `src/` + `api/`.

```bash
set -o pipefail
venv/Scripts/python.exe scripts/run_e2e_baseline.py 2>&1 | tail -3
git checkout -- tests/e2e/screenshots
```
Expected: `16 passed, 3 deselected`, exit 0.

```bash
git status --short
git log --oneline master..HEAD
```
Expected: only `CLAUDE.md`, `architecture_analysis.md`, `architecture_visualization.html` untracked; six phase commits (one per task).

**Constraint audit:** `git diff --stat master..HEAD` must show ZERO files under `src/` or `api/`.

**For all future phases:** the canonical unit gate is now the pytest command — expected `137 passed` — with `unittest discover` (expected `Ran 125 tests` / `OK`) as the backwards-compat check, and the E2E baseline unchanged (`16 passed, 3 deselected`).
