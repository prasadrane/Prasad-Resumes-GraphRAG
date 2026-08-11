# Python Code Style Guide

## General Principles
- **PEP 8 Compliance:** Follow standard Python PEP 8 naming and formatting conventions.
- **Type Annotations:** Use type hints (`typing.Dict`, `typing.List`, `typing.Optional`, `Path`, etc.) for function parameters and return types.
- **Docstrings:** Provide concise docstrings at module headers and public functions explaining purpose, args, and return types.

## Code Organization & Structure
- **Subsystem Isolation:** Keep operational logic in `src/` modules (`src/converters/`, `src/query/`, `src/proxy/`).
- **Clean Imports:** Order imports: standard library first, third-party packages second, internal modules third.
- **No Hardcoded Absolute Paths:** Use `Path` objects and relative path resolution; the `convert` command requires an explicit `--source` flag.

## Error Handling & Diagnostics
- **Explicit Exceptions:** Raise descriptive exceptions (`RuntimeError`, `FileNotFoundError`) instead of returning generic empty fallbacks.
- **Preserve Stderr & Logs:** Always surface diagnostic logs and subprocess `stderr` outputs on execution failure.
- **Cache Eviction on Errors:** Ensure functions wrapped with `@lru_cache` only cache successful responses.

## Testing Standards
- **Test-Driven Development (TDD):** Maintain complete unit test coverage under `tests/` using standard library `unittest` and `unittest.mock`.
