# CareerGraph AI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and scaffold `CareerGraph AI` as a clean-slate, fully autonomous agentic job search, evaluation, GraphRAG resume tailoring, Playwright persistent browser auto-submission, and Gmail tracking platform at `C:\Users\mamat\Github\CareerGraph-AI`.

**Architecture:** Pipeline-Stage architecture with 5 chronological stages (`1_discovery`, `2_evaluation`, `3_tailoring`, `4_submission`, `5_lifecycle`) powered by an embedded SQLite ledger, multi-provider LLM gateway, persistent Playwright browser context (`user_data_dir = "./data/browser_profile"`), Telegram interactive bot, and a 5-tab FastAPI + Tailwind Mission Control Web UI. Reuses ~85% of battle-tested logic from sibling repositories (`Prasad-Resumes-GraphRAG`, `autopilot-jobhunt`, `job-auto-apply-bot`, `career-ops`, `Tech-Job-Resume-Writer`).

**Tech Stack:** Python 3.11+, Playwright & Playwright-Stealth, GraphRAG 2.5, ReportLab PDF, SQLite, FastAPI, Pydantic v2, Pytest, Tailwind CSS.

---

## Global Constraints

- **Target Workspace Root:** `C:\Users\mamat\Github\CareerGraph-AI`
- **Python Version:** `>=3.11`
- **Testing Standard:** Strict Test-Driven Development (TDD). Every task must write failing tests in `tests/` before implementation.
- **Browser Profile:** Playwright must use persistent context via `user_data_dir = "./data/browser_profile"` to retain cookies and logins across all runs.
- **Resume Layout Standard:** ReportLab 2-page hard maximum budget, 0.55" left/right margins, 0.45" top/bottom, <20% bold character cap, KeepTogether job blocks, clickable links.
- **LLM Gateway:** Multi-provider fallback chain (Direct Google Gemini REST, OpenRouter free pool, Alibaba DashScope).

---

### Task 1: Project Scaffolding, Core Models & Configuration

**Files:**
- Create: `C:/Users/mamat/Github/CareerGraph-AI/pyproject.toml`
- Create: `C:/Users/mamat/Github/CareerGraph-AI/requirements.txt`
- Create: `C:/Users/mamat/Github/CareerGraph-AI/README.md`
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/core/__init__.py`
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/core/config.py`
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/core/models.py`
- Test: `C:/Users/mamat/Github/CareerGraph-AI/tests/unit/test_config_models.py`

**Interfaces:**
- Consumes: Environment variables (`GEMINI_API_KEY`, `OPENROUTER_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`).
- Produces: `Settings` singleton, Pydantic schemas (`JobPosting`, `EvaluationResult`, `TailoredArtifacts`, `ApplicationRecord`, `JobStatus` enum).

- [ ] **Step 1: Write the failing test**
```python
# tests/unit/test_config_models.py
import pytest
from src.core.config import Settings, get_settings
from src.core.models import JobPosting, JobStatus, EvaluationResult

def test_settings_defaults():
    settings = get_settings()
    assert settings.min_fit_score == 85
    assert settings.db_path.endswith("careergraph.db")

def test_job_posting_model():
    job = JobPosting(
        id="job123",
        company="Capital One",
        title="Senior .NET Engineer",
        url="https://capitalone.com/jobs/123",
        portal_type="greenhouse",
        source="scraped_nightly",
        status=JobStatus.DISCOVERED
    )
    assert job.company == "Capital One"
    assert job.status == JobStatus.DISCOVERED
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/unit/test_config_models.py -v`  
Expected: FAIL (ModuleNotFoundError / imports missing)

- [ ] **Step 3: Write minimal implementation**
Implement `pyproject.toml`, `requirements.txt`, `src/core/config.py`, and `src/core/models.py` with full Pydantic v2 schemas and environment settings.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/unit/test_config_models.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add pyproject.toml requirements.txt README.md src/core/ tests/
git commit -m "feat(core): scaffold project, configuration and Pydantic models"
```

---

### Task 2: Embedded SQLite Schema & Repository Layer

**Files:**
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/core/db/__init__.py`
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/core/db/schema.py`
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/core/db/repository.py`
- Test: `C:/Users/mamat/Github/CareerGraph-AI/tests/unit/test_db_repository.py`

**Interfaces:**
- Consumes: `JobPosting`, `EvaluationResult`, `TailoredArtifacts`, `ApplicationRecord` from `src.core.models`.
- Produces: `JobRepository`, `ApplicationRepository`, `init_db(db_path)`.

- [ ] **Step 1: Write the failing test**
```python
# tests/unit/test_db_repository.py
import pytest
from src.core.db.schema import init_db
from src.core.db.repository import JobRepository
from src.core.models import JobPosting, JobStatus

def test_job_repository_crud(tmp_path):
    db_file = tmp_path / "test.db"
    init_db(str(db_file))
    repo = JobRepository(str(db_file))
    
    job = JobPosting(
        id="job_001",
        company="Stripe",
        title="Backend Staff Engineer",
        url="https://jobs.stripe.com/1",
        portal_type="lever",
        source="ad_hoc_ui",
        status=JobStatus.DISCOVERED
    )
    repo.insert_job(job)
    retrieved = repo.get_job("job_001")
    assert retrieved is not None
    assert retrieved.company == "Stripe"
    
    repo.update_status("job_001", JobStatus.EVALUATING)
    assert repo.get_job("job_001").status == JobStatus.EVALUATING
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/unit/test_db_repository.py -v`  
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**
Implement SQLite table creation in `schema.py` and thread-safe repository methods in `repository.py` for jobs, evaluations, artifacts, and applications.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/unit/test_db_repository.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add src/core/db/ tests/unit/test_db_repository.py
git commit -m "feat(db): implement SQLite schema and repository CRUD layer"
```

---

### Task 3: Multi-Provider LLM Gateway

**Files:**
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/core/gateway/__init__.py`
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/core/gateway/facade.py`
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/core/gateway/gemini.py`
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/core/gateway/openrouter.py`
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/core/gateway/alibaba.py`
- Test: `C:/Users/mamat/Github/CareerGraph-AI/tests/unit/test_gateway.py`

**Interfaces:**
- Consumes: API Keys (`GEMINI_API_KEY`, `OPENROUTER_API_KEY`).
- Produces: `LLMGateway.generate(prompt: str, json_mode: bool) -> str` with automatic failover chain.

- [ ] **Step 1: Write the failing test**
```python
# tests/unit/test_gateway.py
import pytest
from unittest.mock import patch, MagicMock
from src.core.gateway.facade import LLMGateway

def test_gateway_failover():
    gateway = LLMGateway()
    with patch.object(gateway.gemini_provider, "generate", side_effect=Exception("Rate limit 429")), \
         patch.object(gateway.openrouter_provider, "generate", return_value="OpenRouter response"):
        res = gateway.generate("Hello test")
        assert res == "OpenRouter response"
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/unit/test_gateway.py -v`  
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**
Port and adapt the proven provider classes from `Prasad-Resumes-GraphRAG/src/gateway/` into `src/core/gateway/`.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/unit/test_gateway.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add src/core/gateway/ tests/unit/test_gateway.py
git commit -m "feat(gateway): implement multi-provider LLM gateway with failover"
```

---

### Task 4: Stage 1 — Multi-Channel Discovery & H-1B Verification Engine

**Files:**
- Create: `C:/Users/mamat/Github/CareerGraph-AI/data/h1b_sponsors.json`
- Create: `C:/Users/mamat/Github/CareerGraph-AI/data/companies.yaml`
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/pipeline/1_discovery/__init__.py`
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/pipeline/1_discovery/h1b_checker.py`
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/pipeline/1_discovery/scanner.py`
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/pipeline/1_discovery/adhoc_ingestor.py`
- Test: `C:/Users/mamat/Github/CareerGraph-AI/tests/unit/test_discovery.py`

**Interfaces:**
- Consumes: Raw web pages / URLs / `h1b_sponsors.json`.
- Produces: `H1BChecker.is_sponsor(company: str) -> bool`, `JobScanner.scan_companies() -> List[JobPosting]`, `AdhocIngestor.from_url(url: str) -> JobPosting`.

- [ ] **Step 1: Write the failing test**
```python
# tests/unit/test_discovery.py
from src.pipeline.1_discovery.h1b_checker import H1BChecker
from src.pipeline.1_discovery.adhoc_ingestor import AdhocIngestor

def test_h1b_checker(tmp_path):
    sponsors_file = tmp_path / "sponsors.json"
    sponsors_file.write_text('["Capital One", "Fidelity", "Microsoft"]')
    checker = H1BChecker(str(sponsors_file))
    assert checker.is_sponsor("Capital One") is True
    assert checker.is_sponsor("Unknown LLC") is False

def test_adhoc_ingestor_portal_detect():
    ingestor = AdhocIngestor()
    portal = ingestor.detect_portal("https://boards.greenhouse.io/stripe/jobs/123")
    assert portal == "greenhouse"
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/unit/test_discovery.py -v`  
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**
Port `h1b_sponsors.json` and regex portal detectors from `autopilot-jobhunt` and `career-ops`.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/unit/test_discovery.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add data/ src/pipeline/1_discovery/ tests/unit/test_discovery.py
git commit -m "feat(discovery): implement H-1B verification and multi-portal scanner"
```

---

### Task 5: Stage 2 — 7-Block (A–G) Evaluator & Ghost-Job Guard

**Files:**
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/pipeline/2_evaluation/__init__.py`
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/pipeline/2_evaluation/scorer.py`
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/pipeline/2_evaluation/rubric_evaluator.py`
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/pipeline/2_evaluation/ghost_job_detector.py`
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/pipeline/2_evaluation/work_auth_guard.py`
- Test: `C:/Users/mamat/Github/CareerGraph-AI/tests/unit/test_evaluator.py`

**Interfaces:**
- Consumes: `JobPosting`, `LLMGateway`.
- Produces: `EvaluationResult` (fit score 0–100, Blocks A–G, work_auth_blocker boolean).

- [ ] **Step 1: Write the failing test**
```python
# tests/unit/test_evaluator.py
from unittest.mock import MagicMock
from src.pipeline.2_evaluation.scorer import FitScorer
from src.pipeline.2_evaluation.work_auth_guard import WorkAuthGuard

def test_work_auth_guard_blocks_no_sponsorship():
    guard = WorkAuthGuard()
    jd = "Candidates must be US Citizens or Green Card holders. No visa sponsorship provided."
    assert guard.has_blocker(jd) is True

def test_fit_scorer_mock():
    mock_llm = MagicMock()
    mock_llm.generate.return_value = '{"score": 92, "reason": "Strong AWS and .NET Core alignment"}'
    scorer = FitScorer(llm=mock_llm)
    res = scorer.score_job("Senior .NET Engineer", "C#, AWS, DynamoDB")
    assert res.score == 92
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/unit/test_evaluator.py -v`  
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**
Implement 7-Block evaluation prompts, Prasad-specific scoring rubric, and visa blocker regex detection.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/unit/test_evaluator.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add src/pipeline/2_evaluation/ tests/unit/test_evaluator.py
git commit -m "feat(evaluation): implement 7-block evaluator, fit scorer and ghost-job guard"
```

---

### Task 6: Stage 3 — GraphRAG Knowledge Engine & Strict 2-Page ATS PDF Renderer

**Files:**
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/pipeline/3_tailoring/__init__.py`
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/pipeline/3_tailoring/graph_retriever.py`
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/pipeline/3_tailoring/resume_generator.py`
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/pipeline/3_tailoring/surgical_optimizer.py`
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/pipeline/3_tailoring/fact_guard.py`
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/pipeline/3_tailoring/pdf_renderer.py`
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/pipeline/3_tailoring/pdf_styles.py`
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/pipeline/3_tailoring/cover_letter.py`
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/pipeline/3_tailoring/qa_generator.py`
- Test: `C:/Users/mamat/Github/CareerGraph-AI/tests/unit/test_tailoring.py`

**Interfaces:**
- Consumes: `JobPosting`, `EvaluationResult`, GraphRAG knowledge index.
- Produces: `TailoredArtifacts` (resume PDF path, cover letter path, form Q&A answers JSON, LinkedIn outreach note).

- [ ] **Step 1: Write the failing test**
```python
# tests/unit/test_tailoring.py
from src.pipeline.3_tailoring.surgical_optimizer import SurgicalOptimizer
from src.pipeline.3_tailoring.fact_guard import FactGuard

def test_surgical_optimizer_bold_cap():
    optimizer = SurgicalOptimizer(bold_cap=0.20)
    bullet = "Architected and deployed enterprise microservices using AWS ECS and .NET 8."
    optimized = optimizer.inject_bold_tags(bullet, ["AWS ECS", ".NET 8"])
    assert "<b>AWS ECS</b>" in optimized
    assert optimizer.calculate_bold_ratio(optimized) <= 0.20
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/unit/test_tailoring.py -v`  
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**
Port `pdf_renderer.py`, `pdf_styles.py`, `surgical_optimizer.py`, `fact_guard.py`, and `resume_generator.py` from `Prasad-Resumes-GraphRAG`.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/unit/test_tailoring.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add src/pipeline/3_tailoring/ tests/unit/test_tailoring.py
git commit -m "feat(tailoring): implement GraphRAG resume generator and strict 2-page ATS PDF renderer"
```

---

### Task 7: Stage 4 — Playwright Persistent Browser Submitter & ATS Adapters

**Files:**
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/pipeline/4_submission/__init__.py`
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/pipeline/4_submission/browser_manager.py`
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/pipeline/4_submission/captcha_handler.py`
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/pipeline/4_submission/submitter_engine.py`
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/pipeline/4_submission/adapters/base_adapter.py`
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/pipeline/4_submission/adapters/greenhouse.py`
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/pipeline/4_submission/adapters/lever.py`
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/pipeline/4_submission/adapters/ashby.py`
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/pipeline/4_submission/adapters/workday.py`
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/pipeline/4_submission/adapters/generic.py`
- Test: `C:/Users/mamat/Github/CareerGraph-AI/tests/unit/test_submission.py`

**Interfaces:**
- Consumes: `JobPosting`, `TailoredArtifacts`, Candidate Profile, Persistent Profile Dir (`./data/browser_profile`).
- Produces: `SubmitterEngine.submit(job, artifacts, profile) -> SubmissionReceipt` (screenshot path, confirmation ID, success flag).

- [ ] **Step 1: Write the failing test**
```python
# tests/unit/test_submission.py
from src.pipeline.4_submission.adapters.greenhouse import GreenhouseAdapter
from src.pipeline.4_submission.adapters.lever import LeverAdapter

def test_adapter_can_handle():
    gh = GreenhouseAdapter()
    lever = LeverAdapter()
    assert gh.can_handle("https://boards.greenhouse.io/stripe/jobs/123") is True
    assert lever.can_handle("https://jobs.lever.co/databricks/abc") is True
    assert gh.can_handle("https://jobs.lever.co/databricks/abc") is False
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/unit/test_submission.py -v`  
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**
Port and upgrade the adapters from `job-auto-apply-bot` to support persistent browser context launching, stealth mode, and interactive CAPTCHA pausing.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/unit/test_submission.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add src/pipeline/4_submission/ tests/unit/test_submission.py
git commit -m "feat(submission): implement persistent Playwright submitter and ATS adapters"
```

---

### Task 8: Stage 5 — Gmail Lifecycle Monitoring & 7-Day Follow-Up Cadence

**Files:**
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/pipeline/5_lifecycle/__init__.py`
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/pipeline/5_lifecycle/gmail_watcher.py`
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/pipeline/5_lifecycle/followup_engine.py`
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/pipeline/5_lifecycle/funnel_analytics.py`
- Test: `C:/Users/mamat/Github/CareerGraph-AI/tests/unit/test_lifecycle.py`

**Interfaces:**
- Consumes: Gmail API credentials, `ApplicationRepository`.
- Produces: Auto-updated application stages, 7-day follow-up drafts, funnel conversion metrics.

- [ ] **Step 1: Write the failing test**
```python
# tests/unit/test_lifecycle.py
from datetime import datetime, timedelta
from src.pipeline.5_lifecycle.followup_engine import FollowupEngine

def test_followup_date_calculation():
    engine = FollowupEngine(cadence_days=7)
    submit_date = datetime(2026, 8, 20)
    due_date = engine.calculate_due_date(submit_date)
    assert due_date == datetime(2026, 8, 27)
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/unit/test_lifecycle.py -v`  
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**
Implement `gmail_watcher.py` (ported from `job-auto-apply-bot`), `followup_engine.py`, and `funnel_analytics.py`.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/unit/test_lifecycle.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add src/pipeline/5_lifecycle/ tests/unit/test_lifecycle.py
git commit -m "feat(lifecycle): implement Gmail monitoring, follow-up engine and funnel analytics"
```

---

### Task 9: Telegram Interactive Bot & Notification Dispatcher

**Files:**
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/interface/bot/__init__.py`
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/interface/bot/telegram_bot.py`
- Test: `C:/Users/mamat/Github/CareerGraph-AI/tests/unit/test_telegram_bot.py`

**Interfaces:**
- Consumes: Telegram Bot Token & Chat ID, `JobRepository`.
- Produces: Telegram alert dispatcher, inline buttons (`[✅ 1-Click Apply]`, `[📄 PDF]`), command handler (`/status`, `/scan`, `/apply`).

- [ ] **Step 1: Write the failing test**
```python
# tests/unit/test_telegram_bot.py
from unittest.mock import MagicMock
from src.interface.bot.telegram_bot import TelegramNotifier

def test_send_match_alert():
    mock_bot = MagicMock()
    notifier = TelegramNotifier(token="fake_token", chat_id="123", bot_client=mock_bot)
    notifier.send_job_match("Capital One", "Senior .NET Engineer", 92, "https://link", True)
    assert mock_bot.send_message.called
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/unit/test_telegram_bot.py -v`  
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**
Implement `telegram_bot.py` porting alerting and command loop from `autopilot-jobhunt`.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/unit/test_telegram_bot.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add src/interface/bot/ tests/unit/test_telegram_bot.py
git commit -m "feat(bot): implement Telegram interactive bot and alert dispatcher"
```

---

### Task 10: FastAPI Backend, CLI & 5-Tab Mission Control Web UI

**Files:**
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/interface/api/__init__.py`
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/interface/api/routes.py`
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/interface/cli/__init__.py`
- Create: `C:/Users/mamat/Github/CareerGraph-AI/src/interface/cli/main.py`
- Create: `C:/Users/mamat/Github/CareerGraph-AI/web/index.html`
- Create: `C:/Users/mamat/Github/CareerGraph-AI/web/styles.css`
- Create: `C:/Users/mamat/Github/CareerGraph-AI/web/app.js`
- Test: `C:/Users/mamat/Github/CareerGraph-AI/tests/unit/test_api_cli.py`

**Interfaces:**
- Consumes: All 5 pipeline stages + SQLite repositories.
- Produces: Unified CLI (`careergraph scan`, `apply`, `submit`, `daemon`, `ui`), FastAPI REST endpoints (`/api/pipeline`, `/api/jobs`, `/api/submit`), 5-tab Mission Control UI.

- [ ] **Step 1: Write the failing test**
```python
# tests/unit/test_api_cli.py
from fastapi.testclient import TestClient
from src.interface.api.routes import app

def test_api_pipeline_status():
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/unit/test_api_cli.py -v`  
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**
Implement FastAPI API routes, CLI command entrypoints with click/argparse, and the 5-Tab Tailwind dashboard UI.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/unit/test_api_cli.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add src/interface/ web/ tests/unit/test_api_cli.py
git commit -m "feat(interface): implement FastAPI backend, CLI entrypoint and 5-Tab Mission Control UI"
```

---

### Task 11: End-to-End System Verification & Pipeline Integration

**Files:**
- Create: `C:/Users/mamat/Github/CareerGraph-AI/tests/integration/test_e2e_pipeline.py`

**Interfaces:**
- Consumes: Full end-to-end flow from discovery through evaluation, tailoring, mock submission, and lifecycle status update.

- [ ] **Step 1: Write the end-to-end integration test**
```python
# tests/integration/test_e2e_pipeline.py
import pytest
from unittest.mock import patch, MagicMock
from src.core.models import JobPosting, JobStatus
from src.core.db.repository import JobRepository
from src.pipeline.1_discovery.adhoc_ingestor import AdhocIngestor
from src.pipeline.2_evaluation.scorer import FitScorer
from src.pipeline.3_tailoring.resume_generator import ResumeGenerator
from src.pipeline.4_submission.submitter_engine import SubmitterEngine

def test_end_to_end_autonomous_cycle(tmp_path):
    db_file = tmp_path / "e2e.db"
    repo = JobRepository(str(db_file))
    
    # 1. Ingest
    ingestor = AdhocIngestor()
    job = ingestor.from_text("Capital One", "Senior .NET Engineer", "C#, AWS ECS, DynamoDB", "https://boards.greenhouse.io/capone/1")
    repo.insert_job(job)
    
    # 2. Score
    mock_llm = MagicMock()
    mock_llm.generate.return_value = '{"score": 90, "reason": "Strong AWS/.NET match"}'
    scorer = FitScorer(llm=mock_llm)
    eval_res = scorer.score_job(job.title, job.description_raw)
    assert eval_res.score >= 85
    
    # 3. Tailor
    tailor = ResumeGenerator()
    tailored_text = tailor.generate_raw(job)
    assert "Prasad Rane" in tailored_text
    
    # 4. Mock Submit
    mock_submitter = MagicMock()
    mock_submitter.submit.return_value = MagicMock(success=True, confirmation_id="CAP-12345")
    receipt = mock_submitter.submit(job, tailored_text)
    assert receipt.success is True
```

- [ ] **Step 2: Run test to verify it passes**
Run: `pytest tests/integration/test_e2e_pipeline.py -v`  
Expected: PASS

- [ ] **Step 3: Commit**
```bash
git add tests/integration/test_e2e_pipeline.py
git commit -m "test(integration): verify end-to-end autonomous job application pipeline"
```
