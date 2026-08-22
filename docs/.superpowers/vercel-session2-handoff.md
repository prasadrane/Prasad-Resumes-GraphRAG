# Vercel Deployment — Session 2 Handoff
**Date**: 2026-08-21 (afternoon session)
**Status**: 🟡 FUNCTION RESTORED — app boots and serves; health endpoint returns 503 "degraded" for two explicit, fixable reasons (see §4)

Supersedes: `vercel-deployment-analysis.md` (same folder, morning session).

---

## 1. TL;DR — Current State

| Item | State |
|---|---|
| Production URL | https://prasad-resumes-graphrag.vercel.app |
| Live deployment | `prasad-resumes-graphrag-imxurk2z4…` (master @ `2dfbdad`) |
| Function boot | ✅ Python 3.12.13, app imports in **1.5s**, serves requests |
| `/` (Material Design 3 UI) | ✅ HTTP 200, 49KB HTML |
| `/api/health` | ⚠️ HTTP 503 `{"status":"degraded"}` — see §4 |
| `llm_gateway` check | ✅ ok (alibaba provider, qwen3.6-flash) |
| `graphrag` check | ❌ degraded — parquet/LanceDB artifacts missing from bundle |
| `database` check | ❌ down — code bug: relative path `output` vs `$OUTPUT_DIR` |

The morning session's silent `FUNCTION_INVOCATION_FAILED` is **dead**. Root cause
was a stack of four problems (§3). What remains is data-bundling + one path bug,
both clearly diagnosed with visible errors now.

---

## 2. What Was Fixed This Session (all on master)

| Commit | Change |
|---|---|
| `9a41aa2` | `pyproject.toml` created: `[tool.vercel] entrypoint`; `.python-version` 3.11→3.12; `vercel.json` dropped runtime pin + legacy `routes` |
| `d179e36` | Dependencies mirrored into `pyproject.toml [project] dependencies` (required for preset detection) |
| `220be24` | Empty commit — build retrigger after **server-side framework preset set to `fastapi` via Vercel API** (the actual unlock; see §3.4) |
| `2dfbdad` | `vercel_entry.py` diagnostic entrypoint; entrypoint + `functions` key retargeted to it. Merged to master → auto production deploy |

**Files now governing deployment:**
- `pyproject.toml` — `[project]` metadata + dependencies (keep in sync with `requirements.txt`) + `[tool.vercel] entrypoint = "vercel_entry:app"`
- `vercel.json` — only `functions["vercel_entry.py"]` (`maxDuration` 60, `includeFiles`) + `env.OUTPUT_DIR=/tmp/output`. No `runtime`, no `routes`, no `PYTHON_VERSION` build env.
- `.python-version` — `3.12`
- `vercel_entry.py` — boots `src.web.app:app` with logging; on import failure serves the traceback as HTTP 500 (keep — it's what made this session's diagnosis possible)
- `api/index.py` — **no longer used** (preset mode ignores `/api`). Still in tree; delete or keep-as-docs is a next-session decision.

**Server-side change (NOT in git):** project framework preset patched to `"fastapi"`
via `PATCH /v9/projects/{projectId}` body `{"framework":"fastapi"}`. Without this,
existing projects imported as "Other" never auto-switch and builds fall back to
legacy `/api` mode. Reverting it = set body `{"framework":null}`.

---

## 3. Root Cause Chain (four layers, verified with evidence)

### 3.1 `@vercel/python@4.3.0` handler × Python 3.12
Old handler uses `Queue(loop=…)` — removed in Python 3.10+ → ASGI bootstrap crash
(vercel/vercel#11545, closed/fixed in later runtimes). Symptom: `◇ static/external`
log marker, single truncated line `using Asynchronous Server Gateway Interface (ASGI)`,
zero Python output.

### 3.2 Python 3.11 removed from Vercel
Only 3.12/3.13/3.14 exist now. `PYTHON_VERSION: 3.11` or `.python-version: 3.11`
silently falls back to 3.12 — so even "3.11 builds" landed on the broken handler.
There was no rollback path; only forward (modern runtime).

### 3.3 Morning fix attempts were confounded
- The "0ms build failures" (attempts 3–5 in the morning doc) were config-validation
  errors, NOT runtime failures: legacy `routes` colliding with preset mode, and
  `tool.vercel.entrypoint` pointing into `/api`. The newer runtime was never cleanly tested.
- Even the 2-day-old "Ready" deployments were broken at runtime (verified by curling
  immutable deployment URLs) — production likely **never** served successfully.

### 3.4 Framework preset detection gated on project setting
Even with correct `pyproject.toml` + deps, builds fell back to legacy mode with:
`Error: The pattern "src/web/app.py" defined in 'functions' doesn't match any Serverless Functions inside the 'api' directory.`
Fix: set project `framework` to `fastapi` via API (§2). Detection is gated on this
server-side setting for pre-existing projects.

### 3.5 (Bonus finding) CLI upload path is broken on this machine
`vercel deploy` fails mid-upload with TLS `bad record mac` at ~7–18MB (small API
calls work fine). Likely AV/proxy SSL inspection. Git-push deploys are unaffected —
use those. Worth investigating separately if CLI deploys are ever needed.

---

## 4. Residual Issues (the actual work for next session)

### 4.1 `graphrag` check: artifacts missing from the bundle
Health reports missing: `/var/task/output/lancedb`, `entities.parquet`,
`relationships.parquet`, `community_reports.parquet`, `text_units.parquet`.
**Why**: `output/` is (a) git-untracked (0 files) so git-triggered builds never have
it, and (b) listed in `.vercelignore` so CLI uploads would exclude it too.
`includeFiles: "output/**"` can only include files that were uploaded — it cannot
recover excluded/untracked ones. `output/` is 35MB local (bundle limit: 500MB — fits).
**Options for next session:**
1. Track the needed artifacts in git (`output/*.parquet` + possibly `lancedb/`;
   adds ~35MB to repo) and remove `output/` from `.vercelignore`.
2. Keep artifacts out of the bundle; accept degraded GraphRAG query endpoints
   (app already falls back to `static_graph_reader`/graphify JSON — verify that
   fallback actually serves `/api/query` acceptably).
3. Ship artifacts via external storage (Vercel Blob/S3) fetched at cold start.
   Heavier; only if 1–2 are unacceptable.

### 4.2 `database` check: `[Errno 30] Read-only file system: 'output'`
Something (likely the health check's DB probe and/or `conversation_store` init)
uses the **relative** path `output` (cwd-resolved → `/var/task/output`) instead of
`OUTPUT_DIR_PATH` (which honors `OUTPUT_DIR=/tmp/output`, handled by commit `5f3e41d`
for other paths). Fix: route all runtime-writable paths through `src/config.py`
`OUTPUT_DIR_PATH`. Find offenders: `grep -rn "['\"]output['\"]" src/web/app.py src/query/conversation_store.py`.

### 4.3 `/api/health` returns 503 until 4.1+4.2 resolved
The 503 is honest reporting, not a crash. Once artifacts + path bug are fixed it
should go 200/ok (or decide degraded-but-serving is acceptable and adjust status logic).

### 4.4 Open mystery — worth fresh eyes
The deployment with entrypoint **directly** at `src.web.app:app` (commit `220be24`,
deployment `qs5dbs5p8`) died silently (~5.8s, zero Python output, `INTERNAL_FUNCTION_INVOCATION_FAILED`),
while `vercel_entry.py` wrapping **the same import** boots in 1.5s. The only
difference is the wrapper module. Possible angles: preset loader's module-loading
mechanism vs plain import; app-object inspection by the bridge; cold-start budget
on first invocation. Low priority (workaround is in place and permanent) but
understanding it would validate the whole mental model.

### 4.5 Minor observations
- Serverless boot logs **19 routes** vs 30 locally — likely conditional route
  registration based on missing artifacts/env; verify nothing user-facing is absent.
- Two identical health responses (same timestamp) → response caching somewhere
  (edge or in-function). Check before adding time-sensitive endpoints.
- `api/index.py` is now dead code in preset mode — remove or document.
- `.vercelignore` also excludes `tests/`, `cache/`, `logs/` — fine, just remember
  it when wondering why `includeFiles` seems ignored.

---

## 5. Environment & Ops Notes

- **Vercel CLI**: v54.6.1, auth as `prasadrane`; team `prasad-ranes-projects`
  (`team_QyV2TH8ibxOAvw0eyxEcrlc1`), project `prj_YivF2AGrIauSlgSZF2mAErJF3DU5`.
- **CLI auth token file** (for API calls): `%APPDATA%\xdg.data\com.vercel.cli\auth.json` → `token`.
- **Deploys**: push to `master` → auto production; other branches → preview.
  ⚠️ **Preview deployments are SSO-gated** (`ssoProtection: {"deploymentType":"preview"}`)
  — cannot curl them without Vercel login. Test via production (already broken-pre-fix,
  so low-risk) or disable protection in Team Settings.
- **Useful commands**:
  ```bash
  vercel ls prasad-resumes-graphrag                      # recent deployment URLs
  vercel inspect <deployment-url> --logs                 # full BUILD logs (great for 0ms failures)
  vercel logs <deployment-url> --expand --since 15m      # runtime logs ([boot] lines visible)
  gh api repos/prasadrane/Prasad-Resumes-GraphRAG/commits/<sha>/status   # build status + deploy id
  curl -sS https://prasad-resumes-graphrag.vercel.app/api/health | python -m json.tool
  ```
- **Local Python is 3.11.9 only** — `vercel dev`/local `vercel build` with modern
  tooling won't run (needs ≥3.12). Local smoke test that works:
  `python -c "from src.web.app import app; print(len(app.routes))"` (expect 30).
- **Full unittest suite hangs/timeouts locally** (>5min; pre-existing, likely
  network-dependent tests). Fast subset: `python -m unittest tests.test_ats_matcher` (9 tests, OK).
- Repo has a broken `.git/hooks/post-commit` (spawn error on every commit — harmless).
- `src/cli.py` has pre-existing unstaged local modifications (not from this work).

---

## 6. Suggested Next-Session Plan

1. Fix 4.2 first (pure code bug, small): route DB/conversation-store paths through
   `OUTPUT_DIR_PATH`; test locally + push; health `database` check should go ok.
2. Decide 4.1 strategy (git-track artifacts is the simplest; confirm bundle size
   stays healthy — was 66MB before artifacts).
3. Re-check `/api/health` → target 200; smoke-test `/api/query`, `/api/chat-stream`,
   Graph Explorer tab, and a resume generation end-to-end.
4. Resolve 4.4 mystery if curious; otherwise document the wrapper as load-bearing.
5. Hygiene: remove/keep `api/index.py`; commit `docs/.superpowers/`; update
   `CLAUDE.md` ("Unified Deployment Architecture" section still describes the old
   `api/index.py` entrypoint — now `pyproject.toml` + `vercel_entry.py`) and README.
6. Optional: investigate CLI TLS upload failure (§3.5); delete merged branch
   `fix/vercel-python-runtime`.

---

## 7. Verification Evidence Snapshot (2026-08-21 ~16:53 UTC)

```text
[boot] vercel_entry loading on python 3.12.13
[boot] app imported OK in 1.5s (19 routes)

GET /            → 200, 49,236B (Material Design 3 UI HTML)
GET /api/health  → 503 {"status":"degraded",
                     "checks":{"api":"ok",
                               "llm_gateway":{"status":"ok","provider":"alibaba","model":"qwen3.6-flash"},
                               "graphrag":{"status":"degraded","missing":["/var/task/output/lancedb","…parquet ×4"]},
                               "database":{"status":"down","error":"[Errno 30] Read-only file system: 'output'"}}}
```
