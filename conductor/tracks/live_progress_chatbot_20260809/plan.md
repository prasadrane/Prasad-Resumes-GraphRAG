# Implementation Plan: Live Progress Updates + LLM-Powered Chatbot

## Phase 1: Test-Driven Development (TDD) Foundation
- [x] Task: Create Stepwise Generator & API SSE endpoint tests
    - [x] Create new test file `tests/test_stepwise_generator.py` defining generator yield tests (monotonic progress, final results)
    - [x] Modify `tests/test_web_ui.py` to add test cases for SSE stream endpoints and inputs
    - [x] Run test suite to verify new tests fail (Red stage of TDD)

## Phase 2: Stepwise Generator & Backend SSE Integration
- [x] Task: Implement Stepwise Resume Generator
    - [x] Modify `src/generators/resume_generator.py` to add `generate_raw_resume_stepwise()` yielding 8 steps
    - [x] Maintain CLI and unit test compatibility for existing `generate_raw_resume()`
- [x] Task: Implement SSE endpoints on Local Web Server
    - [x] Modify `src/web/app.py` to add `POST /api/generate-stream` via FastAPI `StreamingResponse`
    - [x] Modify `src/web/app.py` to add `POST /api/chat-stream` retrieving context and calling `call_serverless_llm`
- [x] Task: Verify Phase 2 Backend Tests
    - [x] Run backend unit tests to ensure `tests/test_stepwise_generator.py` passes (Green stage of TDD)

## Phase 3: Material Design 3 UI & Vercel API Parity
- [x] Task: Update Web Frontend Templates and CSS Styles
    - [x] Modify `src/web/static/index.html` to add `#generation-progress` and stepper layout
    - [x] Modify `src/web/static/styles.css` to add M3 styles for stepper, typing indicators, and source chips
- [x] Task: Refactor Frontend JS for SSE Streaming
    - [x] Modify `src/web/static/app.js` `GeneratorController` to read SSE chunked streams via `getReader()`
    - [x] Modify `src/web/static/app.js` `ChatbotController` to read chat SSE and handle typewriter and typing indicators
- [x] Task: Implement Vercel Gateway Parity
    - [x] Modify `api/index.py` to mirror `/api/generate-stream` and `/api/chat-stream` SSE routes
- [x] Task: Final Verification and Clean-up
    - [x] Run all automated unit and integration tests (`python -m pytest`)
    - [x] Perform manual smoke tests of the UI (stepper and chatbot)
