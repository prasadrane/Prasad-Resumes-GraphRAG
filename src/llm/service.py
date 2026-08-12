"""
service.py — Single LLM access point for resume tailoring and story matching.

Wraps the serverless gateway behind a stable interface so generator/matcher
modules never import the gateway directly. The gateway import stays lazy
inside the call: failures surface at call time (not import time), and tests
that patch src.gateway.call_serverless_llm keep working.

Provider routing is delegated to src.config.providers:
- get_model_for(use_case) → (provider_name, model_id, ProviderConfig)
- Default use_cases: "chat", "resume", "embedding"
"""

import logging
import time

logger = logging.getLogger(__name__)


def _resolve_model(model: str = None, use_case: str = "chat"):
    """Resolve explicit or default model from provider registry.

    Returns ``(explicit_or_none, resolved_default_or_none)``.
    If *model* is provided it is returned as the explicit value;
    otherwise we fetch the provider-default for *use_case*.
    """
    if model is not None:
        return model, None
    try:
        from src.config.providers import get_model_for  # noqa: local import for lazy loading
        _, model_id, _ = get_model_for(use_case)
        return None, model_id
    except Exception:
        # Registry misconfigured — caller can still pass model explicitly.
        return None, None


def _build_call_kwargs(prompt: str, system_prompt: str, temperature: float,
                       timeout: int, model: str | None, use_case: str) -> dict:
    """Build keyword arguments dict for ``call_serverless_llm``."""
    explicit, default = _resolve_model(model, use_case)
    kwargs: dict = {
        "prompt": prompt,
        "system_prompt": system_prompt,
        "temperature": temperature,
        "timeout": timeout,
    }
    if explicit:
        kwargs["model"] = explicit
    elif default:
        kwargs["model"] = default
    return kwargs


def call_llm(prompt: str, system_prompt: str = "", temperature: float = 0.3,
             timeout: int = 30, model: str = None, use_case: str = "chat") -> str:
    """Call the serverless LLM gateway. Raises on error; caller decides policy."""
    from src.gateway import call_serverless_llm

    start = time.time()
    result = call_serverless_llm(**_build_call_kwargs(
        prompt, system_prompt, temperature, timeout, model, use_case,
    ))
    elapsed = time.time() - start
    logger.info(
        "LLM call completed in %.1fs (prompt=%d chars, response=%d chars)",
        elapsed, len(prompt), len(result),
    )
    return result


def call_llm_safe(prompt: str, system_prompt: str = "", temperature: float = 0.3,
                  timeout: int = 30, model: str = None,
                  use_case: str = "chat") -> str:
    """Safely call LLM with graceful fallback to empty string on error."""
    start = time.time()
    try:
        result = call_llm(prompt, system_prompt, temperature, timeout, model, use_case)
        return result
    except Exception as err:
        elapsed = time.time() - start
        logger.warning(
            "LLM tailoring call failed after %.1fs (%s). Using base content.",
            elapsed, err,
        )
        return ""


# ── Convenience wrappers (legacy, for backward compatibility) ───────────────

def call_llm_for_resume(prompt: str, system_prompt: str = "", temperature: float = 0.3,
                        timeout: int = 30, model: str = None) -> str:
    """Convenience wrapper that resolves the resume-use-case model."""
    return call_llm(prompt, system_prompt=system_prompt, temperature=temperature,
                    timeout=timeout, model=model, use_case="resume")


def call_llm_safe_for_resume(prompt: str, system_prompt: str = "", temperature: float = 0.3,
                             timeout: int = 30, model: str = None) -> str:
    """Safe convenience wrapper for resume-use-case model resolution."""
    return call_llm_safe(prompt, system_prompt=system_prompt, temperature=temperature,
                         timeout=timeout, model=model, use_case="resume")
