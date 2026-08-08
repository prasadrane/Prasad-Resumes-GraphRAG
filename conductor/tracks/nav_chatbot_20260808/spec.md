# Specification: Top Navigation & GraphRAG Chatbot View

## 1. Overview
Enhance the Web UI with top navigation tabs:
1. **Tailor Resume** (Current default view)
2. **Ask Me Questions** (Interactive GraphRAG Q&A Chatbot view)

Additionally, refactor the frontend architecture for modularity and maintainability, integrate GraphRAG search endpoints, provide quick-click sample questions, and execute Chrome browser tool smoke tests.

## 2. Functional Requirements
- **Top Navigation Bar**:
  - Two buttons: `Tailor Resume` and `Ask Me Questions`.
  - Active tab styling and view toggling without page reload.
- **Ask Me Questions Chatbot View**:
  - Chat interface with message history (User & Assistant bubbles).
  - 4 quick-click sample question chips above input:
    1. "What AWS technologies did Prasad use?"
    2. "What is Prasad's experience with Python & Microservices?"
    3. "Which companies has Prasad worked for?"
    4. "Summarize Prasad's key technical achievements."
  - Selecting a chip automatically populates/sends the question.
  - Support for `local` and `global` mode selection.
- **Backend API**:
  - Endpoint `POST /api/query` calling GraphRAG search engine (`execute_graphrag_query`).
- **Modular Frontend Architecture**:
  - Clean separation of CSS/JS modules or controller functions for Navigation, Resume Generator, Chatbot, and Preview Drawer.
- **UI Verification**:
  - Chrome DevTools automated visual and interactive smoke/regression testing.

## 3. Non-Functional Requirements & Acceptance Criteria
- Smooth tab switching without losing state.
- Clean response rendering with markdown/line-break support in chat messages.
- Full unittest suite passing for backend API endpoints.
