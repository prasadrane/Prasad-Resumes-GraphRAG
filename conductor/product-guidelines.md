# Product Guidelines

## Prose & Tone
- **Technical & Concise:** All CLI outputs, query results, logs, and artifacts must use direct, professional GitHub-flavored Markdown.
- **Data-Driven Precision:** Prioritize concrete metrics, technology names, role titles, and quantifiable achievements over general statements.
- **Structured Formatting:** Use headings, bullet points, table formats, and callout alerts to ensure maximum scannability.

## User Experience & CLI Design
- **Pre-Flight Diagnostics:** Always verify external dependencies (e.g. LiteLLM Proxy port 8002 readiness) before initiating long-running indexing or query tasks.
- **Actionable Diagnostics:** Provide clear, human-readable error messages and actionable suggestions when tasks or API calls fail.
- **Clean Command Output:** Format CLI search outputs with distinct visual headers and clear separators.

## Code Architecture & Standards
- **Modular Subsystem Separation:** Core logic lives under `src/`, centralized configuration under `config/`, entrypoint helpers under `scripts/`, and unit tests under `tests/`.
- **Test-Driven Development (TDD):** Every major feature, pipeline change, or query enhancement must be accompanied by automated unit tests under `tests/`.
- **Portability:** Never hardcode user-specific local file paths; rely on environment variables (`SOURCE_RESUMES_DIR`) or relative path fallbacks.
- **Error Safety:** Never swallow exceptions or hide `stderr` output; handle process failures explicitly and maintain clean LRU caching semantics.
