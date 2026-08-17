# Subsystem: `src/shared` (Continent Level)

**Responsibility:** Shared Pydantic API request/response models and common router definitions.

---

## 1. Overview & Responsibility

**[Documented]** `src/shared` defines standardized Pydantic data schemas and FastAPI route registration helpers shared across both the monolithic local FastAPI server and serverless function handlers (`api/index.py`).

**[Inferred]** Consolidating data models in `src/shared` ensures schema consistency between client requests, generator responses, and testing mocks.

---

## 2. Key Modules & Classes

| Module / Class | File | Responsibility |
|:---|:---|:---|
| [`QueryRequest`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/shared/api_models.py) | `src/shared/api_models.py` | Schema for incoming natural-language queries (query string, session_id, mode). |
| [`ResumeGenerationRequest`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/shared/api_models.py) | `src/shared/api_models.py` | Schema for resume tailoring requests (company_name, job_description, domain_override). |
| [`SaveEditRequest`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/shared/api_models.py) | `src/shared/api_models.py` | Schema for manual resume modifications and edits. |
| `api_routes.py` | `src/shared/api_routes.py` | Shared route handlers for resume generation, keyword analysis, and health checks. |

---

## 3. Dependencies

- **Inbound:** [`src/web/app.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/web/app.py), `api/index.py`, test suites.
- **Outbound:** [`src/generators`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/generators), [`src/query`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/query).
