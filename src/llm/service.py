"""
service.py — Single LLM access point for resume tailoring and story matching.

Wraps the serverless gateway behind a stable interface so generator/matcher
modules never import the gateway directly. The gateway import stays lazy
inside the call: failures surface at call time (not import time), and tests
that patch src.query.serverless_gateway.call_serverless_llm keep working.
"""


def call_llm(prompt: str, system_prompt: str = "", temperature: float = 0.3, timeout: int = 30, model: str = None) -> str:
    """Call the serverless LLM gateway. Raises on error; caller decides policy."""
    import time
    from src.query.serverless_gateway import call_serverless_llm
    start = time.time()
    kwargs = {"prompt": prompt, "system_prompt": system_prompt, "temperature": temperature, "timeout": timeout}
    if model:
        kwargs["model"] = model
    result = call_serverless_llm(**kwargs)
    elapsed = time.time() - start
    print(f"[LLM] Call completed in {elapsed:.1f}s (prompt: {len(prompt)} chars, response: {len(result)} chars)")
    return result


def call_llm_safe(prompt: str, system_prompt: str = "", temperature: float = 0.3, timeout: int = 30, model: str = None) -> str:
    """Safely call LLM with graceful fallback to empty string on error."""
    import time
    start = time.time()
    try:
        kwargs = {"prompt": prompt, "system_prompt": system_prompt, "temperature": temperature, "timeout": timeout}
        if model:
            kwargs["model"] = model
        result = call_llm(**kwargs)
        return result
    except Exception as err:
        elapsed = time.time() - start
        print(f"[WARN] LLM tailoring call failed after {elapsed:.1f}s: {err}. Using base content.")
        return ""
