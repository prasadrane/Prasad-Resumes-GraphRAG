# Implementation Plan: Live Progress Updates + LLM-Powered Chatbot

## Phase 1: Test-Driven Development (TDD) Foundation
- [ ] Task: Create Stepwise Generator & API SSE endpoint tests
    - [ ] Create new test file `tests/test_stepwise_generator.py` defining generator yield tests (monotonic progress, final results)
    - [ ] Modify `tests/test_web_ui.py` to add test cases for SSE stream endpoints and inputs
    - [ ] Run test suite to verify new tests fail (Red stage of TDD)

## Phase 2: Stepwise Generator & Backend SSE Integration
- [ ] Task: Implement Stepwise Resume Generator
    - [ ] Modify `src/generators/resume_generator.py` to add `generate_raw_resume_stepwise()` yielding 8 steps
    - [ ] Maintain CLI and unit test compatibility for existing `generate_raw_resume()`
- [ ] Task: Implement SSE endpoints on Local Web Server
    - [ ] Modify `src/web/app.py` to add `POST /api/generate-stream` via FastAPI `StreamingResponse`
    - [ ] Modify `src/web/app.py` to add `POST /api/chat-stream` retrieving context and calling `call_serverless_llm`
- [ ] Task: Verify Phase 2 Backend Tests
    - [ ] Run backend unit tests to ensure `tests/test_stepwise_generator.py` passes (Green stage of TDD)

## Phase 3: Material Design 3 UI & Vercel API Parity
- [ ] Task: Update Web Frontend Templates and CSS Styles
    - [ ] Modify `src/web/static/index.html` to add `#generation-progress` and stepper layout
    - [ ] Modify `src/web/static/styles.css` to add M3 styles for stepper, typing indicators, and source chips
- [ ] Task: Refactor Frontend JS for SSE Streaming
    - [ ] Modify `src/web/static/app.js` `GeneratorController` to read SSE chunked streams via `getReader()`
    - [ ] Modify `src/web/static/app.js` `ChatbotController` to read chat SSE and handle typewriter and typing indicators
- [ ] Task: Implement Vercel Gateway Parity
    - [ ] Modify `api/index.py` to mirror `/api/generate-stream` and `/api/chat-stream` SSE routes
- [ ] Task: Final Verification and Clean-up
    - [ ] Run all automated unit and integration tests (`python -m pytest`)
    - [ ] Perform manual smoke tests of the UI (stepper and chatbot)
