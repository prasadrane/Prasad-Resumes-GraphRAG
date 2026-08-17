# Subsystem: `src/config` (Continent Level)

**Responsibility:** Provider configuration registry, environment variable resolution, and model settings management.

---

## 1. Overview & Responsibility

**[Documented]** `src/config` manages LLM and embedding provider declarations. It defines structured models (`ProviderConfig`) and maps environment variables (`CHAT_PROVIDER`, `RESUME_PROVIDER`, `EMBEDDING_PROVIDER`) to active runtime provider endpoints.

**[Inferred]** This subsystem acts as the single source of truth for provider credentials, model names, base URLs, and timeout configurations across both local development (LiteLLM proxy) and serverless deployment (direct API keys).

---

## 2. Public API & Key Classes

| Class / Function | File | Description |
|:---|:---|:---|
| [`ProviderConfig`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/config/providers.py) | `src/config/providers.py` | Dataclass / Pydantic model for provider parameters (name, base_url, api_key, model_name, timeout). |
| `get_provider_config` | `src/config/providers.py` | Factory function retrieving active provider configuration from environment or settings. |
| `PROVIDER_REGISTRY` | `src/config/providers.py` | Dictionary mapping provider identifiers (`gemini`, `alibaba`, `openrouter`) to default configs. |

---

## 3. Dependencies & Call Graph

- **Inbound Callers:**
  - [`src/gateway/facade.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/gateway/facade.py) calls `get_provider_config` to initialize provider instances.
  - [`src/cli.py`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/cli.py) reads provider config for CLI commands.
- **Outbound Dependencies:**
  - Standard library `os`, `yaml`.
