# Implementation Plan: Top Navigation & GraphRAG Chatbot View

## Phase 1: Backend API Query Endpoint & Unit Tests
- [ ] Task: Add `QueryRequest` model and `POST /api/query` endpoint in `src/web/app.py` integrating `src/query/search_engine.py`.
- [ ] Task: Add unit tests in `tests/test_web_ui.py` for `/api/query` endpoint.

## Phase 2: Refactor UI Architecture & HTML Layout
- [ ] Task: Update `src/web/static/index.html` to add top navigation bar and modular view sections (`#generator-view` and `#chatbot-view`).
- [ ] Task: Add quick-click sample question chips and chat input form to `#chatbot-view`.
- [ ] Task: Refactor `src/web/static/styles.css` with clean layout, navigation tabs, and chat message bubble styles.

## Phase 3: JavaScript Modular View Controllers & Chatbot Integration
- [ ] Task: Modularize `src/web/static/app.js` with view routing, tab management, generator controller, chatbot controller, and preview drawer controller.
- [ ] Task: Implement message sending, sample chip clicks, loading indicators, and markdown formatting in Chatbot controller.

## Phase 4: Chrome Browser Tool Smoke Testing & Verification
- [ ] Task: Launch local web UI server on `http://127.0.0.1:8000`.
- [ ] Task: Use Chrome DevTools tools to perform interactive smoke testing: tab switching, resume tailoring, raw editing, and GraphRAG chatbot query execution.
- [ ] Task: Run full unit test suite to verify no regression.
