# Phase 1 — Deferred Findings & Follow-ups

> Persistent record created when the Phase 1 SDD workspace
> (`.superpowers/sdd/2026-08-10-phase-1-critical-fixes/`) was deleted after
> the final whole-branch review. Feed these into Phase 2+ planning.

## Phase 1 outcome (branch `refactor/phase-1-critical-fixes`)

Five commits over plan base `0b563db`:

| Commit | Change |
|---|---|
| `d5eaf02` | Reject path traversal in legacy PDF route + 2 E2E regression tests |
| `2b27132` | Fix `req.content` AttributeError in `api/index.py` (+ human-approved `except HTTPException: raise` amendment) + 2 unittest regression tests |
| `ef80dbe` | Drop unused `pdfplumber`/`pypdf` from `requirements-dev.txt` |
| `5b1cd2f` | Logged warnings instead of silent `except: pass` in `static_graph_reader.py` |
| `3a36abb` | Final-review fix: `is_relative_to` containment guards in both file-serving routes |

Final gate at HEAD: unittest 67 OK; E2E baseline 16 passed / 3 deselected / exit 0.

## Deferred to Phase 2 (from final whole-branch review, opus)

1. **Exception-message leakage** — `api/index.py` 500 handlers expose raw
   exception text via `detail=f"...{str(e)}"` (~lines 85, 109, 139). Return a
   generic message; log details server-side.
2. **`except Exception → 500` swallow pattern** in `generate_resume_endpoint`,
   `default_resume_endpoint`, and `generate-stream` (same pattern Task 2 fixed
   in `render_pdf_endpoint`). Consider a single `_safe_endpoint`-style helper.
3. **Contract divergence** between `src/web/app.py` (`SaveEditRequest` with
   `content`/rich fields) and `api/index.py` (`RenderPdfRequest` with only
   `raw_text`/`company`): the Vercel entrypoint silently drops fields the
   local server accepts. Latent mismatch even though the current frontend
   sends `raw_text`.
4. **`rglob` comment** — one-line comment in `serve_pdf_legacy` explaining the
   company dir may be nested under `output/` (review finding M-4, cosmetic).

## Carry-over from Phase 0 (its workspace was already deleted)

- `tests/e2e/conftest.py` `_free_port` TOCTOU (port may be taken between
  check and bind).
- Selector-engine consistency across E2E tests.
- Add a `tests/e2e/README.md` (how to run, what the baseline covers).
- Windows `CREATE_NEW_PROCESS_GROUP` note for subprocess teardown.

## Rulings worth remembering

- Task 2 plan conflict (2026-08-10): owner ruled the plan's stated goal (400
  on empty input) governs over its literal "one line only" step text — the
  2-line `except HTTPException: raise` amendment was kept.
- Security follow-up remains owner-deferred (spec §9): rotate leaked keys,
  scrub git history. Not done in Phase 1 by design.
