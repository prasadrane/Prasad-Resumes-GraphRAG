# Vercel Free Tier Refactoring Track Specification

## Overview
This track defines the architectural refactoring needed to deploy the Prasad-Resumes-GraphRAG platform onto the Vercel Free Tier (Serverless Hobby plan).

---

## 3-Step Refactoring Blueprint

### Step 1: LLM Routing & Provider Adapter (Serverless-Friendly LLM Gateway)
- **Problem:** Vercel serverless functions cannot execute long-running local background processes like `scripts/run_litellm.py` listening on port `8002`.
- **Solution:** 
  - Refactor `src/generators/ats_matcher.py`, GraphRAG query interface, and LLM calls to use **OpenRouter API** directly or standard serverless LLM client adapters (`openai`/`google-genai`).
  - Configure cloud rate-limit fallback and API keys via Vercel Environment Variables (`OPENROUTER_API_KEY` / `GEMINI_API_KEY`).
  - Maintain local LiteLLM proxy capability for local dev while enabling stateless direct API calls in serverless environments.

### Step 2: Pre-computed GraphRAG Storage & Serverless Vector Querying
- **Problem:** GraphRAG indexing is computationally heavy, takes several minutes, and relies on ephemeral/read-only local file disk paths (`output/`, `cache/`) unavailable on Vercel Functions (10s execution limit).
- **Solution:**
  - Decouple indexing from serverless runtime: keep `python -m graphrag index --root .` as a local or GitHub Actions pre-build step.
  - Package pre-indexed Parquet files / LanceDB vector stores or sync them to a free tier hosted cloud store (e.g., Supabase / Pinecone / static bundled JSON artifacts).
  - Create a lightweight serverless query module in `src/verifiers/` or `src/converters/` to execute graph search against static/cloud artifacts within < 3 seconds.

### Step 3: Vercel Web Interface & API Route Handlers
- **Problem:** Gradio Web UI (`scripts/run_ui.py`) requires a persistent running Python process.
- **Solution:**
  - Add Vercel Serverless Web API endpoints using **FastAPI** (`api/index.py`) or a modern Next.js / React frontend.
  - Expose API endpoints for ATS keyword matching, tailored resume generation, and PDF streaming.
  - Perform browser verification using the Chrome DevTools MCP tools (`navigate_page`, `fill`, `click`, `take_screenshot`) at each step to visually inspect and confirm the tailored resume generation workflow with custom job descriptions.
  - Add `vercel.json` deployment manifest for seamless Vercel deployment.

