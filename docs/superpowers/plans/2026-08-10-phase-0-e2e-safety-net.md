# Phase 0 — Playwright E2E Safety Net Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic Playwright/Chromium end-to-end baseline that records the currently working behavior of the local UI server, so Phases 1–5 can be refactored safely against it.

**Architecture:** A session-scoped pytest fixture boots `src.web.app:app` in a uvicorn subprocess on a free port and waits for health. Baseline tests then exercise only the deterministic (non-LLM) HTTP and browser flows. LLM-dependent flows live in a separate opt-in suite marked `live` and skipped by default.

**Tech Stack:** Python 3.11 (project venv `venv/Scripts/python.exe`), pytest, pytest-playwright + Chromium, httpx, uvicorn, FastAPI.

## Global Constraints

- Always use the project interpreter `venv/Scripts/python.exe`. Do NOT install into any other interpreter.
- The baseline targets the **local UI server** `src.web.app:app` (NOT `api/index.py`, which is the Vercel entrypoint).
- The baseline must not call any LLM. LLM flows go in the `live` suite and are excluded by default via pytest marker.
- The page loads external Google Fonts; UI tests must navigate with `wait_until="domcontentloaded"` so they never hang waiting on `fonts.googleapis.com`.
- No application source code under `src/` changes in Phase 0. Only test infra, config, and requirements are touched.
- Deterministic endpoint shapes for `src.web.app:app` (verified against source):
  - `GET /api/default-resume` returns `{"status","pdf_url","txt_url","raw_resume"}` where `pdf_url` is a **path URL** `/api/files/<rel>?t=<ts>` (not base64).
  - `GET /api/history` returns a **list** (may be non-empty; it scans `output/`).
  - `POST /api/render_pdf` and `POST /api/save-edit` share one handler accepting `{"txt_url","raw_text","content","company"}`; with `raw_text` set and no `txt_url` it returns a **base64** `data:application/pdf;base64,...` in `pdf_url`.
  - There is **no** `/api/keywords` on the local server (it exists only in `api/index.py`).
- Shell: commands below are POSIX (Git Bash). `venv/Scripts/python.exe` is the Windows venv interpreter and works from Git Bash.

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `requirements.txt` | Modify | Add `uvicorn` (runtime dep of `cli.py ui`, currently missing). |
| `requirements-dev.txt` | Modify | Add `pytest`, `pytest-playwright`, `httpx`, `uvicorn`. |
| `pytest.ini` | Create | Register `live` marker; exclude `live` by default via `addopts`. |
| `tests/e2e/conftest.py` | Create | `app_server` fixture (boot app subprocess, health-wait, teardown). |
| `tests/e2e/test_server_health.py` | Create | Minimal boot smoke test proving the fixture works. |
| `tests/e2e/test_baseline_api.py` | Create | Deterministic API characterization tests. |
| `tests/e2e/test_baseline_ui.py` | Create | Deterministic browser/UI characterization tests. |
| `tests/e2e/test_llm_live.py` | Create | Opt-in LLM flows (`-m live`), skipped by default. |
| `tests/e2e/test_capture_baseline_screenshots.py` | Create | Writes reference screenshots to `tests/e2e/screenshots/baseline/`. |
| `tests/e2e/screenshots/baseline/` | Create (dir) | Committed reference screenshots. |
| `scripts/run_e2e_baseline.py` | Create | One-command runner for the baseline suite. |

---

## Task 1: Dependencies and pytest configuration

**Files:**
- Modify: `requirements.txt` (add `uvicorn`)
- Modify: `requirements-dev.txt` (add test deps)
- Create: `pytest.ini`

- [ ] **Step 1: Add `uvicorn` to `requirements.txt`**

`requirements.txt` currently ends with `pyyaml`. Append a `uvicorn` line:

```
# Vercel Serverless API Production Dependencies (Lightweight <50MB bundle)
fastapi
pydantic>=2.0.0
reportlab
python-dotenv
pyyaml
uvicorn
```

- [ ] **Step 2: Add test deps to `requirements-dev.txt`**

`requirements-dev.txt` starts with `-r requirements.txt`. Append the test stack:

```
# Local Development, GraphRAG Indexing & Proxy Dependencies
-r requirements.txt
graphrag
litellm
lancedb
pdfplumber
pypdf
pymupdf

# E2E test stack (Phase 0 safety net)
pytest
pytest-playwright
httpx
```

- [ ] **Step 3: Create `pytest.ini`**

```ini
[pytest]
markers =
    live: End-to-end tests that call real LLM APIs. Opt-in with `pytest -m live`; excluded by default.
addopts = -ra -m "not live"
```

- [ ] **Step 4: Install the new dependencies**

Run: `venv/Scripts/python.exe -m pip install -r requirements-dev.txt`
Expected: succeeds; `pytest`, `pytest-playwright`, `httpx`, `uvicorn` resolve.

- [ ] **Step 5: Install the Chromium browser for Playwright**

Run: `venv/Scripts/python.exe -m playwright install chromium`
Expected: Chromium downloads/installs without error.

- [ ] **Step 6: Verify imports and marker registration**

Run: `venv/Scripts/python.exe -c "import pytest, playwright, httpx, uvicorn; print('deps ok')"`
Expected: prints `deps ok`.

Run: `venv/Scripts/python.exe -m pytest --markers | head -5`
Expected: lists the `live` marker.

- [ ] **Step 7: Commit**

```bash
git add requirements.txt requirements-dev.txt pytest.ini
git commit -m "test(phase0): add Playwright/pytest E2E dependencies and pytest config"
```

---

## Task 2: App-server fixture + boot smoke test

**Files:**
- Create: `tests/e2e/conftest.py`
- Test: `tests/e2e/test_server_health.py`

**Interfaces:**
- Produces: `app_server` fixture (session-scoped) yielding a `str` base URL like `http://127.0.0.1:<port>`. Every later E2E task depends on this exact fixture name and return type.

- [ ] **Step 1: Create `tests/e2e/conftest.py`**

```python
"""
Shared fixtures for end-to-end tests.

`app_server` boots the FastAPI app (src.web.app:app) in a uvicorn subprocess
on a free local port, waits until it responds, yields its base URL, and tears
it down afterward. The baseline suite exercises only deterministic (non-LLM)
endpoints, so no LiteLLM proxy or API keys are required.
"""

import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent.parent


def _free_port() -> int:
    """Return an OS-assigned free TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_until_healthy(base_url: str, timeout_s: float = 60.0) -> None:
    """Poll GET / until it returns HTTP 200 or the timeout expires."""
    deadline = time.monotonic() + timeout_s
    last_error = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(base_url + "/", timeout=2) as resp:
                if resp.status == 200:
                    return
        except Exception as exc:  # retry until deadline
            last_error = exc
        time.sleep(0.5)
    raise RuntimeError(
        f"App at {base_url} did not become healthy within {timeout_s}s: {last_error}"
    )


@pytest.fixture(scope="session")
def app_server():
    """Boot the local UI app in a subprocess and yield its base URL."""
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn", "src.web.app:app",
            "--host", "127.0.0.1", "--port", str(port),
        ],
        cwd=str(ROOT_DIR),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    try:
        _wait_until_healthy(base_url)
        yield base_url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
```

- [ ] **Step 2: Write the boot smoke test `tests/e2e/test_server_health.py`**

```python
"""Smoke test proving the app_server fixture boots the app cleanly."""

import urllib.request


def test_app_boots_and_serves_root(app_server):
    with urllib.request.urlopen(app_server + "/", timeout=10) as resp:
        assert resp.status == 200
```

- [ ] **Step 3: Run the smoke test**

Run: `venv/Scripts/python.exe -m pytest tests/e2e/test_server_health.py -v`
Expected: PASS. The fixture boots uvicorn, the health-wait succeeds, `/` returns 200.

- [ ] **Step 4: If it fails, diagnose before proceeding**

A failure here means the app does not boot standalone (e.g. an import-time side effect). Read the captured subprocess output, fix the environment issue, and re-run until green. Do NOT move to Task 3 until this passes — the whole safety net depends on it.

- [ ] **Step 5: Commit**

```bash
git add tests/e2e/conftest.py tests/e2e/test_server_health.py
git commit -m "test(phase0): add app_server fixture and boot smoke test"
```

---

## Task 3: Deterministic API baseline tests

**Files:**
- Create: `tests/e2e/test_baseline_api.py`

**Interfaces:**
- Consumes: `app_server` fixture from Task 2 (str base URL).
- Produces: a green API baseline covering `/`, `/api/history`, `/api/default-resume`, and `/api/render_pdf`.

- [ ] **Step 1: Write `tests/e2e/test_baseline_api.py`**

```python
"""
Baseline characterization tests for the deterministic (non-LLM) API surface
of the local UI server (src.web.app:app).

These tests record the currently working behavior. They must pass before any
refactoring begins and after every change, acting as the safety net.
"""

import base64

import httpx


def test_root_serves_ui(app_server):
    resp = httpx.get(f"{app_server}/", timeout=30.0)
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")


def test_history_returns_list(app_server):
    resp = httpx.get(f"{app_server}/api/history", timeout=30.0)
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    for item in body:
        assert "company" in item
        assert "pdf_url" in item


def test_default_resume_returns_pdf(app_server):
    resp = httpx.get(f"{app_server}/api/default-resume", timeout=90.0)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert len(body["raw_resume"]) > 0
    # Local server returns a path URL, not a data URI. Follow it to get bytes.
    pdf_url = body["pdf_url"]
    assert pdf_url.startswith("/api/files/")
    pdf_resp = httpx.get(app_server + pdf_url, timeout=60.0)
    assert pdf_resp.status_code == 200
    assert pdf_resp.content[:4] == b"%PDF"


def test_render_pdf_from_raw_text(app_server):
    raw_text = (
        "PRASAD RANE\n"
        "Contact: prasad@example.com | https://linkedin.com/in/prasad\n\n"
        "EXECUTIVE SUMMARY\n"
        "Experienced software engineer building cloud platforms.\n\n"
        "TECHNICAL SKILLS\n"
        "Languages: Python, SQL\n\n"
        "EXPERIENCE\n"
        "Senior Engineer, Acme Corp | Jan 2020 - Present\n"
        "- Built distributed systems in Python and AWS\n"
    )
    resp = httpx.post(
        f"{app_server}/api/render_pdf",
        json={"raw_text": raw_text, "company": "Baseline"},
        timeout=90.0,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    pdf_url = body["pdf_url"]
    assert pdf_url.startswith("data:application/pdf;base64,")
    pdf_bytes = base64.b64decode(pdf_url.split(",", 1)[1])
    assert pdf_bytes[:4] == b"%PDF"
```

- [ ] **Step 2: Run the API baseline**

Run: `venv/Scripts/python.exe -m pytest tests/e2e/test_baseline_api.py -v`
Expected: all 4 tests PASS.

- [ ] **Step 3: If a test fails, determine whether it is a real regression or a test bug**

Because these characterize existing behavior, a failure means either the app is not actually working that way (investigate app code) or the test made a wrong assumption (fix the test). Resolve before committing.

- [ ] **Step 4: Commit**

```bash
git add tests/e2e/test_baseline_api.py
git commit -m "test(phase0): add deterministic API baseline characterization tests"
```

---

## Task 4: Deterministic UI baseline tests

**Files:**
- Create: `tests/e2e/test_baseline_ui.py`

**Interfaces:**
- Consumes: `app_server` fixture (Task 2) and the pytest-playwright `page` fixture.

- [ ] **Step 1: Write `tests/e2e/test_baseline_ui.py`**

```python
"""
Baseline characterization tests for the browser UI of the local server.

Uses Playwright (via pytest-playwright). Navigates with
`wait_until="domcontentloaded"` so tests never hang on external Google Fonts.
"""

import re

from playwright.sync_api import expect

PAGE_TITLE = "Prasad Resumes — GraphRAG Knowledge Graph & Tailored Resume Engine"
HIDDEN_RE = re.compile("hidden")


def _goto(page, base_url):
    page.goto(base_url, wait_until="domcontentloaded")


def test_page_loads_with_title(page, app_server):
    _goto(page, app_server)
    assert page.title() == PAGE_TITLE


def test_default_tab_active_and_resume_loads(page, app_server):
    _goto(page, app_server)
    default_btn = page.locator("#nav-default-btn")
    expect(default_btn).to_have_attribute("aria-selected", "true", timeout=10000)
    # The default view fetches /api/default-resume and fills the textarea.
    page.wait_for_function(
        "document.querySelector('#default-raw-textarea').value.length > 0",
        timeout=60000,
    )
    textarea_value = page.locator("#default-raw-textarea").input_value()
    assert len(textarea_value) > 0
    assert not textarea_value.startswith("Error loading default resume")


def test_tab_switching(page, app_server):
    _goto(page, app_server)

    page.click("#nav-tailor-btn")
    expect(page.locator("#generator-view")).not_to_have_class(HIDDEN_RE, timeout=10000)

    page.click("#nav-chat-btn")
    expect(page.locator("#chatbot-view")).not_to_have_class(HIDDEN_RE, timeout=10000)

    page.click("#nav-default-btn")
    expect(page.locator("#default-view")).not_to_have_class(HIDDEN_RE, timeout=10000)


def test_tailor_form_elements_present(page, app_server):
    _goto(page, app_server)
    page.click("#nav-tailor-btn")
    expect(page.locator("#company-input")).to_be_visible(timeout=10000)
    expect(page.locator("#jd-input")).to_be_visible(timeout=10000)
    expect(page.locator("#generate-btn")).to_be_visible(timeout=10000)


def test_chat_elements_present(page, app_server):
    _goto(page, app_server)
    page.click("#nav-chat-btn")
    expect(page.locator("#chatbot-view")).not_to_have_class(HIDDEN_RE, timeout=10000)
    expect(page.locator('.m3-mode-btn[data-mode="local"]')).to_be_visible(timeout=10000)
    expect(page.locator('.m3-mode-btn[data-mode="global"]')).to_be_visible(timeout=10000)
    expect(page.locator("#clear-chat-btn")).to_be_visible(timeout=10000)


def test_system_status_badge_present(page, app_server):
    _goto(page, app_server)
    expect(page.locator("#system-status")).to_be_visible(timeout=10000)
```

- [ ] **Step 2: Run the UI baseline headless**

Run: `venv/Scripts/python.exe -m pytest tests/e2e/test_baseline_ui.py -v`
Expected: all 6 tests PASS (Chromium runs headless by default).

- [ ] **Step 3: If a locator fails, verify the selector against `src/web/static/index.html`**

Element IDs used above were verified against the current markup: `nav-default-btn`, `nav-tailor-btn`, `nav-chat-btn`, `default-view`, `generator-view`, `chatbot-view`, `company-input`, `jd-input`, `generate-btn`, `system-status`, `default-raw-textarea`, `.m3-mode-btn[data-mode=...]`, `clear-chat-btn`. If markup changed, update the selector and re-run.

- [ ] **Step 4: Commit**

```bash
git add tests/e2e/test_baseline_ui.py
git commit -m "test(phase0): add deterministic UI baseline characterization tests"
```

---

## Task 5: Opt-in live LLM suite

**Files:**
- Create: `tests/e2e/test_llm_live.py`

**Interfaces:**
- Consumes: `app_server` fixture (Task 2).

- [ ] **Step 1: Write `tests/e2e/test_llm_live.py`**

```python
"""
Live LLM end-to-end tests. These call real LLM APIs (via the serverless
gateway) and therefore cost credits and can be slow/flaky. They are marked
`live` and excluded by default (see pytest.ini addopts `-m "not live"`).

Run explicitly with:  pytest tests/e2e/ -m live
"""

import pytest

pytestmark = pytest.mark.live


def test_query_returns_response(app_server):
    import httpx

    resp = httpx.post(
        f"{app_server}/api/query",
        json={"query": "What AWS technologies did Prasad use?", "mode": "local"},
        timeout=180.0,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert len(body["response"]) > 0


def test_generate_returns_resume(app_server):
    import httpx

    jd_text = (
        "Looking for a senior engineer with Python, AWS, Kubernetes, and "
        "experience building LLM-powered platform tooling."
    )
    resp = httpx.post(
        f"{app_server}/api/generate",
        json={"company": "LiveTestCo", "jd_text": jd_text},
        timeout=600.0,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert len(body["raw_resume"]) > 0


def test_chat_stream_emits_done(app_server):
    import httpx

    with httpx.stream(
        "POST",
        f"{app_server}/api/chat-stream",
        json={"query": "Summarize Prasad's career.", "mode": "local"},
        timeout=300.0,
    ) as resp:
        assert resp.status_code == 200
        chunks = "".join(resp.iter_text())
    assert "event: done" in chunks or "event: error" in chunks
```

- [ ] **Step 2: Confirm live tests are excluded by default**

Run: `venv/Scripts/python.exe -m pytest tests/e2e/ -v`
Expected: the live tests show as **deselected** (they do not run); the deterministic tests run.

- [ ] **Step 3: Confirm live tests are collectible when opted in**

Run: `venv/Scripts/python.exe -m pytest tests/e2e/test_llm_live.py -m live --collect-only`
Expected: 3 tests collected (no import errors). Do NOT actually run them unless you intend to spend LLM credits.

- [ ] **Step 4: Commit**

```bash
git add tests/e2e/test_llm_live.py
git commit -m "test(phase0): add opt-in live LLM E2E suite (marked live)"
```

---

## Task 6: Baseline screenshot capture

**Files:**
- Create: `tests/e2e/test_capture_baseline_screenshots.py`
- Create: `tests/e2e/screenshots/baseline/` (populated by running the test)

- [ ] **Step 1: Write `tests/e2e/test_capture_baseline_screenshots.py`**

```python
"""
Captures baseline reference screenshots of the three main UI tabs.

Screenshots are written to tests/e2e/screenshots/baseline/ and committed as
reference images for human review. They are NOT used for pixel-diff
assertions (structural assertions in test_baseline_ui.py are the safety net).
"""

from pathlib import Path

SCREENSHOT_DIR = Path(__file__).resolve().parent / "screenshots" / "baseline"


def _goto(page, base_url):
    page.goto(base_url, wait_until="domcontentloaded")


def test_capture_default_tab(page, app_server):
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    _goto(page, app_server)
    page.wait_for_function(
        "document.querySelector('#default-raw-textarea').value.length > 0",
        timeout=60000,
    )
    page.screenshot(path=str(SCREENSHOT_DIR / "tab-default.png"), full_page=True)


def test_capture_tailor_tab(page, app_server):
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    _goto(page, app_server)
    page.click("#nav-tailor-btn")
    page.wait_for_selector("#generator-view:not(.hidden)", timeout=10000)
    page.screenshot(path=str(SCREENSHOT_DIR / "tab-tailor.png"), full_page=True)


def test_capture_chat_tab(page, app_server):
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    _goto(page, app_server)
    page.click("#nav-chat-btn")
    page.wait_for_selector("#chatbot-view:not(.hidden)", timeout=10000)
    page.screenshot(path=str(SCREENSHOT_DIR / "tab-chat.png"), full_page=True)
```

- [ ] **Step 2: Run the screenshot capture**

Run: `venv/Scripts/python.exe -m pytest tests/e2e/test_capture_baseline_screenshots.py -v`
Expected: all 3 tests PASS.

- [ ] **Step 3: Verify the screenshots exist and look correct**

Run: `ls -la tests/e2e/screenshots/baseline/`
Expected: `tab-default.png`, `tab-tailor.png`, `tab-chat.png` exist and are non-trivial in size. Open them to confirm the UI rendered (default shows the resume, tailor shows the form, chat shows the chat panel).

- [ ] **Step 4: Commit**

```bash
git add tests/e2e/test_capture_baseline_screenshots.py tests/e2e/screenshots/baseline/
git commit -m "test(phase0): capture baseline UI screenshots for the three tabs"
```

---

## Task 7: Convenience runner + full green gate

**Files:**
- Create: `scripts/run_e2e_baseline.py`

- [ ] **Step 1: Write `scripts/run_e2e_baseline.py`**

```python
"""
run_e2e_baseline.py — One-command runner for the Phase 0 E2E safety net.

Runs the deterministic Playwright baseline against the local UI server.
Exits non-zero if any baseline test fails, making it usable as a gate.

Usage:
    python scripts/run_e2e_baseline.py           # deterministic baseline
    python scripts/run_e2e_baseline.py --live     # also run live LLM tests
"""

import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent


def main() -> int:
    live = "--live" in sys.argv
    marker = "live or not live" if live else "not live"
    cmd = [
        sys.executable, "-m", "pytest", "tests/e2e/",
        "-v", "-m", marker,
    ]
    print(f"[E2E] Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(ROOT_DIR))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run the full baseline via the runner**

Run: `venv/Scripts/python.exe scripts/run_e2e_baseline.py`
Expected: all deterministic tests PASS, live tests deselected, exit code 0.

- [ ] **Step 3: Confirm the Phase 0 exit criteria**

Verify all of the following before declaring Phase 0 complete:
- App boots cleanly under the fixture (Task 2 green).
- All deterministic API tests pass (Task 3 green).
- All deterministic UI tests pass (Task 4 green).
- Live tests are excluded by default (Task 5 verified).
- Baseline screenshots captured for all three tabs (Task 6 verified).
- `scripts/run_e2e_baseline.py` exits 0.

- [ ] **Step 4: Commit**

```bash
git add scripts/run_e2e_baseline.py
git commit -m "test(phase0): add E2E baseline runner and complete safety net"
```

---

## Phase 0 Complete

At this point the safety net is in place and committed. The deterministic baseline (`scripts/run_e2e_baseline.py`) must be run after every subsequent change in Phases 1–5; any failure is a hard stop and revert. The next planning step is the Phase 1 (critical fixes) plan, written once Phase 0 is verified green.
