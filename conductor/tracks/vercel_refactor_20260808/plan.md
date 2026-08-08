# Vercel Free Tier Refactoring Plan

- [x] Track: Vercel Free Tier Refactoring (`vercel_refactor_20260808`)
  - [x] **Step 1: LLM Routing & Provider Adapter (Serverless Gateway)**
    - [x] Create serverless LLM client module for direct OpenRouter / Gemini API routing without LiteLLM proxy dependency.
    - [x] Update `src/generators/ats_matcher.py` to support environment-based direct API calls.
    - [x] Unit tests for serverless LLM fallback handling.
  - [x] **Step 2: Pre-computed Graph Artifacts & Fast Querying**
    - [x] Design lightweight static reader for pre-indexed Parquet/JSON graph artifacts.
    - [x] Benchmark query response time to ensure < 5s serverless execution.
    - [x] Add GitHub Action workflow template for automated pre-indexing on push.
  - [x] **Step 3: Vercel Serverless Endpoints & Deployment Manifest**
    - [x] Implement `api/index.py` serverless FastAPI router for web queries and PDF generation.
    - [x] Add `vercel.json` deployment configuration.
    - [x] Launch Web UI (`python src/cli.py ui` / `scripts/run_ui.py`).
    - [x] Perform Chrome DevTools browser verification (`chrome-devtools-mcp` / `navigate_page`, `take_screenshot`, `click`) of Web UI functionality at each step.
    - [x] Verify tailored resume generation & PDF rendering via Chrome DevTools UI automation based on a given job description.
    - [x] Verify local serverless execution via Vercel CLI (`vercel dev`) with Chrome DevTools browser verification.



