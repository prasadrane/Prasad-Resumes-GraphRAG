# Specification: Live Progress Updates + LLM-Powered Chatbot

## 1. Overview
Enhance the user experience of the resume tailor and chatbot application. Resume generation currently blocks the UI without progress feedback; we will implement a stepwise generator, SSE (Server-Sent Events) progress endpoint, and an interactive Material Design 3 progress stepper. The chatbot currently yields raw graph queries; we will implement LLM-synthesized answers using the Vercel-compatible serverless gateway, displaying responses with simulated typewriter streaming, typing indicators, and source entity chips.

## 2. Functional Requirements
### 2.1 Stepwise Resume Generator (Backend)
- Add `generate_raw_resume_stepwise()` in `src/generators/resume_generator.py` yielding 8 progress steps:
  1. `extracting_keywords` (8%)
  2. `loading_master` (15%)
  3. `selecting_summary` (25%)
  4. `tailoring_summary` (38%)
  5. `tailoring_bullets` (55%)
  6. `formatting` (72%)
  7. `rendering_pdf` (88%)
  8. `complete` (100% with final paths)
- Leave `generate_raw_resume()` intact for CLI backward compatibility.

### 2.2 SSE Streaming Endpoint (Backend)
- Add `POST /api/generate-stream` to `src/web/app.py` returning progress events via FastAPI `StreamingResponse`.
- Add `POST /api/chat-stream` to `src/web/app.py` returning chatbot responses (sources, tokens, complete).

### 2.3 MD3 Progress Stepper UI
- Add `#generation-progress` stepper container to `src/web/static/index.html`.
- Add MD3 linear progress styles, vertical stepper styles, animations for `.pending`, `.active`, `.completed`, `.typing-indicator`, and `.source-chips` in `src/web/static/styles.css`.
- Update `src/web/static/app.js` to consume POST-based SSE streams via `fetch()` and `response.body.getReader()`. Fall back to single-POST if SSE fails.

### 2.4 LLM-Powered Chatbot
- Synthesize answers in `POST /api/chat-stream` by retrieving fast context via `static_graph_reader` (<1s) and querying `call_serverless_llm()`.
- Update UI to show typing indicators, simulated typewriter rendering (simulated streaming), and source chips.
- Keep `POST /api/query` working with fallback to raw search results if LLM credentials are missing.

### 2.5 Vercel API Parity
- Add mirroring SSE routes to `api/index.py` for FastAPI Vercel serverless functions.

### 2.6 Testing
- Add `tests/test_stepwise_generator.py` verifying stepwise yields, monotonic progress, and complete payloads.
- Add/modify web UI integration tests in `tests/test_web_ui.py` covering SSE endpoints and error validation.

## 3. Non-Functional Requirements
- **Performance:** Context extraction via `static_graph_reader` must run in under 1 second.
- **Robustness:** Graceful fallback to existing single-POST endpoints if SSE fails, and to raw text dumps if LLM keys are absent.

## 4. Out of Scope
- Backend LLM token-by-token HTTP streaming (using client-side simulated streaming instead).
- Changing styling framework (retains Vanilla CSS).
