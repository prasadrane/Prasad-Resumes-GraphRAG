# Vercel Deployment Issue Analysis
**Date**: 2026-08-21  
**Status**: ✅ SUPERSEDED — root cause found & fixed same day (runtime×Python 3.12 incompatibility + preset gating). App boots and serves; residual 503-degraded health items remain. **Continue in `vercel-session2-handoff.md` (same folder).**

---

## TL;DR

The app builds successfully but the Lambda fails at runtime with `FUNCTION_INVOCATION_FAILED` (500). Root cause appears to be an incompatibility between `@vercel/python@4.3.0` runtime and Python 3.12. Framework auto-detection via pyproject.toml doesn't work with `/api` directory layout.

---

## Current State

| Item | Value |
|---|---|
| Production URL | https://prasad-resumes-graphrag.vercel.app |
| Latest deployment | `prasad-resumes-graphrag-hg6glxynv` |
| Build status | ✅ Ready (30s) |
| Runtime status | ❌ 500 FUNCTION_INVOCATION_FAILED |
| Lambda source in logs | `static/external` (should be `serverless`) |
| Function size | ~70MB |
| Runtime in build | python3.12 |
| Runtime in vercel.json | @vercel/python@4.3.0 |
| PYTHON_VERSION | 3.12 |

---

## Timeline of Investigation

### 1. Initial Symptom (bs4 missing)
- All endpoints returned 500
- Error: `Runtime.ImportModuleError: Unable to import module 'vc__handler__python': No module named 'bs4'`
- Import chain: `app.py → orchestrator.py → job_parser.py → job_scraper.py → from bs4 import BeautifulSoup`
- `requirements.txt` did NOT include `beautifulsoup4`

**Fix applied**: Added `beautifulsoup4>=4.12.0` and `requests>=2.31.0` to requirements.txt (commit `f5c786b`)

### 2. After bs4 fix — NEW error
- Build: ✅ Ready (30s)
- Runtime: ❌ 500 `INTERNAL_FUNCTION_INVOCATION_FAILED`
- Log source: `static/external` (NOT `serverless`)
- Log message: `using Asynchronous Server Gateway Interface (ASGI)` — truncated, no traceback

**Key observation**: The Lambda builds and is created (70MB, python3.12), but at invocation time Vercel routes it as "static" instead of "serverless". The ASGI wrapper message appears but the function never executes.

### 3. Attempt: Remove runtime pin + bump Python
- Removed `"runtime": "@vercel/python@4.3.0"` from vercel.json
- Changed PYTHON_VERSION from 3.11 to 3.12
- **Result**: Build failed at 0ms — configuration error

### 4. Attempt: Framework auto-detection via pyproject.toml
- Created pyproject.toml with `tool.vercel.entrypoint = "api.index:app"`
- Removed routes from vercel.json
- **Result**: Build failed at 0ms — framework preset detection doesn't work with `/api` directory layout

### 5. Attempt: @vercel/python@4.8.0
- Same build failure at 0ms as above

### 6. Revert to @vercel/python@4.3.0 + PYTHON_VERSION 3.12
- Build: ✅ Ready (30s)
- Runtime: ❌ Same 500 FUNCTION_INVOCATION_FAILED

---

## Root Cause Hypothesis

**Primary**: `@vercel/python@4.3.0` is incompatible with Python 3.12. This runtime version was built for Python 3.9-3.11 era. When Python 3.11 was deprecated on Vercel (only 3.12/3.13/3.14 supported now), the old runtime produces a Lambda that can't start on current infrastructure.

Evidence:
- Lambda `runtime` field in deployment JSON shows `python3.12`
- Function builds successfully (dependencies bundled, 70MB)
- But invocation fails before Python code runs
- Log source shows `static` instead of `serverless` — the Vercel edge router doesn't recognize the Lambda as valid

**Secondary**: There may be a separate issue with the `/api` directory convention being deprecated or changed in newer Vercel platform versions.

---

## Config Comparison

### Original (broken before fix)
```json
{
  "version": 2,
  "functions": {
    "api/index.py": {
      "runtime": "@vercel/python@4.3.0",
      "maxDuration": 60,
      "includeFiles": "input/**,config/**,src/web/static/**,output/**"
    }
  },
  "routes": [{"src": "/(.*)", "dest": "api/index.py"}],
  "build": {"env": {"PYTHON_VERSION": "3.11"}},
  "env": {"OUTPUT_DIR": "/tmp/output"}
}
```

### Current (after fix, still broken)
```json
{
  "version": 2,
  "functions": {
    "api/index.py": {
      "runtime": "@vercel/python@4.3.0",
      "maxDuration": 60,
      "includeFiles": "input/**,config/**,src/web/static/**,output/**"
    }
  },
  "routes": [{"src": "/(.*)", "dest": "api/index.py"}],
  "build": {"env": {"PYTHON_VERSION": "3.12"}},
  "env": {"OUTPUT_DIR": "/tmp/output"}
}
```

---

## Available @vercel/python Versions

| Major | Versions | Latest |
|---|---|---|
| 1.x | 16 | 1.2.5-canary.1 |
| 2.x | 61 | 2.3.4 |
| 3.x | 69 | 3.1.60 |
| 4.x | 19 | 4.8.0 |
| 5.x | 11 | 5.0.10 |
| 6.x | 104 | 6.58.0 |

---

## Options for Next Session

### Option A: Try @vercel/python@5.0.10 or @6.58.0
These are newer major versions that should support Python 3.12. Risk: might have different requirements or break /api directory convention.

```json
"runtime": "@vercel/python@5.0.10"
```

### Option B: Migrate to root-level entrypoint
Move from `/api/index.py` to root `app.py` or `index.py` and let Vercel auto-detect FastAPI. This is the modern recommended approach.

Changes needed:
1. Rename/move `api/index.py` to `app.py` (or keep both)
2. Remove `routes` from vercel.json
3. Remove explicit `runtime` pin
4. Ensure `requirements.txt` has fastapi (already does)

### Option C: Use Docker (Vercel supports containerized Python)
The docs mention deploying Python via Docker. Could bypass runtime issues entirely.

### Option D: Check Vercel support/docs for known issues
Search Vercel community forum for "FUNCTION_INVOCATION_FAILED" + "@vercel/python@4.3.0" + Python 3.12.

---

## Files Modified This Session

| File | Change |
|---|---|
| `requirements.txt` | Added beautifulsoup4, requests |
| `vercel.json` | PYTHON_VERSION 3.11→3.12 (runtime still pinned 4.3.0) |
| `pyproject.toml` | Created then deleted |

**Commits**: `f5c786b`, `95f6a96`, `a7dba4b`, `caf6b09`

---

## Useful Commands for Debugging

```bash
# List recent deployments
vercel ls

# Inspect a deployment
vercel inspect <deployment-url>

# Get runtime logs
vercel logs <deployment-url> --follow

# Get error logs only
vercel logs --status-code 500 --since 1h

# Health check
curl -s https://prasad-resumes-graphrag.vercel.app/api/health
```

---

## Open Questions for User

1. Has this project ever successfully deployed to Vercel before? (Checking older deployments)
2. Is there a preference between staying with `/api` directory vs migrating to root entrypoint?
3. Are there specific Vercel features being used that require the current setup (e.g., edge functions, specific regions)?
