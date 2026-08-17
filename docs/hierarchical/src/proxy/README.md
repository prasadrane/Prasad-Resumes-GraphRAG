# Subsystem: `src/proxy` (Continent Level)

**Responsibility:** Local LiteLLM proxy process management and port 8002 execution.

---

## 1. Overview & Responsibility

**[Documented]** `src/proxy` provides tools to spawn, monitor, and manage a local LiteLLM proxy server configured via `config/litellm-config.yaml`.

**[Inferred]** This subsystem is utilized during local GraphRAG indexing runs (`python -m graphrag index`) to expose OpenAI-compatible endpoints that route under the hood to Gemini and OpenRouter models with rate limit handling.

---

## 2. Key Modules & Classes

| Module / Class | File | Responsibility |
|:---|:---|:---|
| `litellm_runner.py` | `src/proxy/litellm_runner.py` | Launches `litellm --config config/litellm-config.yaml --port 8002` as a managed subprocess. |
| `__init__.py` | `src/proxy/__init__.py` | Module initialization. |

---

## 3. Dependencies

- **Configuration:** [`config/litellm-config.yaml`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/config/litellm-config.yaml)
- **Callers:** [`scripts/run_litellm.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/scripts/run_litellm.py), [`src/cli.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/cli.py)
