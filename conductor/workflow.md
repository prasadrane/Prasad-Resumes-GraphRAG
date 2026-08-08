# Development Workflow

## 1. Conductor Methodology Overview
All development tasks, new features, and bug fixes follow the **Conductor Track Protocol**:
1. **Track Creation:** Define a clear track with `plan.md`, `spec.md`, and `metadata.json`.
2. **Test-Driven Development (TDD):** Write unit tests in `tests/` before or alongside feature implementation.
3. **Execution & Verification:** Run verification commands (`python -m unittest discover -s tests`) to confirm 100% test pass rates before marking tasks complete.
4. **Track Completion:** Document completion in track `index.md` and top-level `conductor/index.md`.

## 2. Iterative Task Cycle
- **Step 1: Plan** — Define task requirements, target files, and verification steps.
- **Step 2: Test First** — Create or update tests reflecting expected contract/behavior.
- **Step 3: Implement** — Write modular code in `src/` or `scripts/`.
- **Step 4: Verify** — Execute test commands and ensure zero errors or regressions.
- **Step 5: Document** — Record changes in documentation and track indices.

## 3. Environment & Proxy Protocol
- Always activate virtual environment (`.\venv\Scripts\Activate.ps1`).
- Ensure LiteLLM Proxy is running on `http://localhost:8002` before graph indexing or query execution (`python scripts/run_litellm.py` or `python src/cli.py proxy`).
