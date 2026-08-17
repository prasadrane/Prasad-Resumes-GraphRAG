# Subsystem: `src/llm` (Continent Level)

**Responsibility:** High-level LLM client interface and application-layer prompt dispatch.

---

## 1. Overview & Responsibility

**[Documented]** `src/llm` provides a unified service abstraction (`LLMService`) for calling language models from application code, decoupling higher-level consumers from gateway provider mechanics.

**[Inferred]** Acts as an optional mediator between legacy prompt callers and the new multi-provider `src/gateway` architecture.

---

## 2. Key Modules & Classes

| Module / Class | File | Responsibility |
|:---|:---|:---|
| `service.py` | `src/llm/service.py` | High-level LLM caller wrapping prompt generation and response handling. |
| `__init__.py` | `src/llm/__init__.py` | Package initialization and export interface. |

---

## 3. Dependencies

- **Outbound:** [`src/gateway/facade.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/gateway/facade.py)
- **Inbound:** Application scripts and query pipelines.
