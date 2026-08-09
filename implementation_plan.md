# Live Progress Updates + LLM-Powered Chatbot

## Problem

1. **Resume Generation freezes UI** — `GeneratorController.handleSubmit()` in [`app.js`](file:///c:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/web/static/app.js#L367-L402) makes a single blocking `POST /api/generate` call. The entire pipeline (parse master → select summary variant → LLM tailor summary → LLM tailor bullets per job → format markdown → bold keywords → render PDF) runs server-side and returns only when fully complete. The UI shows a static `"Synthesizing Tailored Resume..."` label with no progress indication.

2. **Chatbot has no LLM intelligence** — The chatbot in [`app.py`](file:///c:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/web/app.py) routes chat messages to `execute_graphrag_query()` which runs a `graphrag query` subprocess. When GraphRAG isn't indexed, it just dumps raw search engine results. There's no conversational LLM synthesis — users see entity dumps, not natural-language answers.

## Proposed Changes

---

### Component 1: Stepwise Resume Generator (Backend)

#### [MODIFY] [`resume_generator.py`](file:///c:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/generators/resume_generator.py)

Add a new `generate_raw_resume_stepwise()` generator function alongside the existing `generate_raw_resume()`:

- **Yields** `(step_id, step_label, progress_pct, detail_text)` tuples after each major stage
- **Final yield** includes the complete result: `("complete", ..., 100, {"raw_resume_path": ..., "raw_resume": ..., "pdf_path": ...})`
- Existing `generate_raw_resume()` remains untouched for CLI backward compat

| Step ID | Label | Progress | What happens |
|---------|-------|----------|-------------|
| `extracting_keywords` | Extracting ATS keywords | 8% | `extract_ats_keywords(jd_text)` |
| `loading_master` | Loading master resume | 15% | Read & parse `MASTER_RESUME.txt` |
| `selecting_summary` | Selecting best summary variant | 25% | `select_tailored_summary()` |
| `tailoring_summary` | LLM tailoring summary | 38% | LLM call for executive summary |
| `tailoring_bullets` | LLM tailoring experience bullets | 55% | LLM calls per job (this is the longest step) |
| `formatting` | Formatting & bold marking | 72% | `format_tailored_markdown()` + bold keywords |
| `rendering_pdf` | Rendering PDF | 88% | `render_pdf_resume()` |
| `complete` | Done | 100% | Final result payload |

---

### Component 2: SSE Streaming Endpoint (Backend)

#### [MODIFY] [`app.py`](file:///c:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/web/app.py)

Add a **new** `POST /api/generate-stream` endpoint using FastAPI's `StreamingResponse`:

```python
from fastapi.responses import StreamingResponse

@app.post("/api/generate-stream")
async def generate_resume_stream(req: GenerateRequest):
    """SSE stream of resume generation progress steps."""
    async def event_generator():
        for step_id, label, pct, detail in generate_raw_resume_stepwise(...):
            yield f"data: {json.dumps({...})}\n\n"
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

- Each SSE event carries `{ step, label, progress, detail }`
- The `complete` event carries the full result including `pdf_url`, `txt_url`, `raw_resume`
- Error events have `event: error` type
- The existing `POST /api/generate` endpoint stays unchanged

---

### Component 3: Material Design 3 Progress Stepper UI

#### [MODIFY] [`index.html`](file:///c:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/web/static/index.html)

Add a progress stepper container inside the `generator-view` section (between the form and preview drawer):

```html
<section id="generation-progress" class="m3-card hidden slide-up">
    <div class="progress-header">
        <h3><span class="material-symbols-outlined">rocket_launch</span> Generating Resume</h3>
        <span id="progress-pct" class="progress-pct">0%</span>
    </div>
    <div class="m3-linear-progress" id="progress-bar">
        <div class="progress-fill" id="progress-fill"></div>
    </div>
    <div class="stepper-container" id="stepper-container">
        <!-- Steps populated by JS -->
    </div>
</section>
```

#### [MODIFY] [`styles.css`](file:///c:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/web/static/styles.css)

Add Material Design 3 stepper styles:

- **`.m3-linear-progress`** — M3 linear progress indicator (gradient animated bar)
- **`.stepper-container`** — Vertical stepper with connecting lines
- **`.step-item`** with 3 states:
  - `.pending` — Muted outline circle with step number
  - `.active` — Animated pulsing primary-colored circle with ripple
  - `.completed` — Filled check-circle with scale-in animation
- **`.step-label`** and **`.step-detail`** text with fade transitions
- **`.step-elapsed`** right-aligned elapsed time badge
- Smooth height auto-animation as steps appear

#### [MODIFY] [`app.js`](file:///c:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/web/static/app.js)

Rewrite `GeneratorController.handleSubmit()` to use SSE streaming:

1. Show the progress stepper section, hide form alert
2. Use `fetch()` with `response.body.getReader()` to read SSE stream (standard `EventSource` doesn't support POST)
3. Parse each SSE `data:` line as JSON
4. For each step event:
   - Transition the step from `pending` → `active` (previous step → `completed`)
   - Animate the linear progress bar to the new percentage
   - Show elapsed time per step
5. On `complete` event: open the preview drawer with PDF, show success alert
6. On `error`: show error state, allow retry
7. **Fallback**: If SSE fails (e.g., network issue), fall back to the existing single-POST behavior

---

### Component 4: LLM-Powered Chatbot

> [IMPORTANT]
> The chatbot currently calls `execute_graphrag_query()` which runs a subprocess (`python -m graphrag query`). This works when GraphRAG is indexed but produces raw text dumps. We'll add LLM synthesis using the existing `call_serverless_llm()` from [`serverless_gateway.py`](file:///c:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/query/serverless_gateway.py) to produce natural conversational answers.

#### [MODIFY] [`app.py`](file:///c:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/web/app.py)

Add a new `POST /api/chat-stream` SSE endpoint:

1. Search `static_graph_reader` for context entities (fast, <1s)
2. Build an LLM prompt with graph context + user message + conversation system prompt
3. Call `call_serverless_llm()` (OpenRouter → Gemini fallback)
4. Stream the response via SSE:
   - `event: sources` — List of graph entities found
   - `event: token` — Streamed tokens (or full response if non-streaming)
   - `event: done` — Final complete response + source list

Also update the existing `POST /api/query` endpoint to include LLM synthesis when available (graceful fallback to raw results when LLM keys are missing).

#### [MODIFY] [`app.js`](file:///c:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/web/static/app.js)

Update `ChatbotController.handleSubmit()`:

1. Show user message bubble immediately
2. Show assistant bubble with **typing indicator** (3-dot M3 bounce animation)
3. Connect to `POST /api/chat-stream` SSE endpoint
4. On `sources` event: show a small M3 chip below the bubble: "📊 N sources found"
5. On `token` events: append text to bubble with typewriter cursor effect
6. On `done`: finalize bubble, remove cursor, show source chips
7. **Fallback**: If SSE fails, fall back to existing `POST /api/query` single-response

#### [MODIFY] [`styles.css`](file:///c:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/web/static/styles.css)

- **`.typing-indicator`** — 3-dot bounce animation inside message bubble
- **`.message-streaming`** — Blinking cursor effect during token streaming
- **`.source-chips`** — Container for source entity pill badges below messages
- **`.source-chip`** — M3 assist chip with entity icon
- Smooth bubble height transition as content grows

---

### Component 5: Vercel API Parity

#### [MODIFY] [`index.py`](file:///c:/Users/mamat/Github/Prasad-Resumes-GraphRAG/api/index.py)

Add `POST /api/generate-stream` and `POST /api/chat-stream` SSE routes to the Vercel FastAPI app, mirroring the local server behavior.

---

### Component 6: Tests (TDD)

#### [NEW] [`test_stepwise_generator.py`](file:///c:/Users/mamat/Github/Prasad-Resumes-GraphRAG/tests/test_stepwise_generator.py)

- `test_stepwise_yields_all_steps` — verify correct 8-step sequence
- `test_stepwise_progress_monotonic` — verify percentages strictly increase
- `test_stepwise_final_result_has_file` — verify complete step includes raw_resume_path
- `test_stepwise_graceful_llm_failure` — verify pipeline continues when LLM is unavailable

#### [MODIFY] [`test_web_ui.py`](file:///c:/Users/mamat/Github/Prasad-Resumes-GraphRAG/tests/test_web_ui.py)

- `test_generate_stream_returns_sse` — verify SSE content type
- `test_generate_stream_all_steps_emitted` — verify all 8 step events in order
- `test_generate_stream_validation_error` — verify 400 on empty company
- `test_chat_stream_returns_sse` — verify SSE streaming for chat
- `test_chat_stream_validation` — verify 400 on empty query

---

## Open Questions

> [IMPORTANT]
> **LLM streaming vs. single-response for chat**: The existing `call_serverless_llm()` uses `urllib.request` which returns a complete response (not streaming tokens). Should we:
> 1. **(Recommended)** Show a typing indicator → get full LLM response → render it with a fast typewriter animation (simulated streaming). This requires no changes to `serverless_gateway.py` and gives the same user experience.
> 2. Switch to the `requests` library with `stream=True` for real token-by-token streaming from OpenRouter/Gemini. More complex, requires refactoring `serverless_gateway.py`.

> [NOTE]
> **SSE via POST**: Standard `EventSource` only supports GET. For POST-based SSE (needed to send JD text in the body), we'll use `fetch()` with `response.body.getReader()` to manually parse the SSE stream. This is a well-supported pattern in all modern browsers.

---

## Verification Plan

### Automated Tests

```powershell
cd c:\Users\mamat\Github\Prasad-Resumes-GraphRAG
.\venv\Scripts\Activate.ps1
python -m pytest tests/test_stepwise_generator.py tests/test_web_ui.py tests/test_resume_generator.py -v
```

### Manual Verification

1. Launch UI: `python src/cli.py ui`
2. Open browser → navigate to "Tailor Resume" tab
3. Enter company + JD → click Generate → **verify stepper animates through all 8 steps** with progress bar and elapsed times
4. Switch to "Ask Me Questions" tab → type a question → **verify typing indicator, then streaming response with source chips**
5. Test error: Try generating with empty company → verify error state
6. Test LLM offline: Unset `OPENROUTER_API_KEY` and `GEMINI_API_KEY` → verify chatbot gracefully falls back to raw GraphRAG results
