# Subsystem: `src/config` (Continent Level)

**Responsibility:** Provider configuration registry, environment variable resolution, shared LLM constants, and model settings management.

---

## 1. Overview & Responsibility

**[Documented]** `src/config` manages LLM and embedding provider declarations and shared LLM constants. It defines structured models (`ProviderConfig`), maps environment variables (`CHAT_PROVIDER`, `RESUME_PROVIDER`, `EMBEDDING_PROVIDER`) to active runtime provider endpoints, and centralizes LLM parameters (`EMBEDDING_DIM`, `LLM_MAX_TOKENS`, `LLM_DEFAULT_TIMEOUT`, `RATE_LIMIT_TAGS`).

**[Inferred]** This subsystem acts as the single source of truth for provider credentials, model names, base URLs, and timeout configurations across both local development (LiteLLM proxy) and serverless deployment (direct API keys), strictly satisfying the Dependency Inversion Principle (DIP).

---

## 2. Public API & Key Classes

| Class / Function | File | Description |
|:---|:---|:---|
| [`ProviderConfig`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/config/providers.py) | `src/config/providers.py` | Dataclass / Pydantic model for provider parameters (name, base_url, api_key, model_name, timeout). |
| `get_provider_config` | `src/config/providers.py` | Factory function retrieving active provider configuration from environment or settings. |
| `llm_constants` | `src/config/llm_constants.py` | Centralized LLM constants: `EMBEDDING_DIM` (1536), `LLM_MAX_TOKENS`, `LLM_DEFAULT_TIMEOUT` (120s), `GRAPHRAG_STORY_CAP`, `RATE_LIMIT_TAGS`. |
| `PROVIDER_REGISTRY` | `src/config/providers.py` | Dictionary mapping provider identifiers (`gemini`, `alibaba`, `openrouter`) to default configs. |

---

## 3. Dependencies & Call Graph

- **Inbound Callers:**
  - [`src/gateway/base.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/gateway/base.py) imports constants from `src.config.llm_constants`.
  - [`src/gateway/facade.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/gateway/facade.py) calls `get_provider_config` to initialize provider instances.
  - [`src/cli.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/cli.py) reads provider config for CLI commands.
- **Outbound Dependencies:**
  - Standard library `os`, `yaml`.
