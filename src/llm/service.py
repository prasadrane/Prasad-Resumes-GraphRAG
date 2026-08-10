"""
service.py — Single LLM access point for resume tailoring and story matching.

Wraps the serverless gateway behind a stable interface so generator/matcher
modules never import the gateway directly. The gateway import stays lazy
inside the call: failures surface at call time (not import time), and tests
that patch src.query.serverless_gateway.call_serverless_llm keep working.
"""


def call_llm(prompt: str, system_prompt: str = "", temperature: float = 0.3, timeout: int = 30) -> str:
    """Call the serverless LLM gateway. Raises on error; caller decides policy."""
    from src.query.serverless_gateway import call_serverless_llm
    return call_serverless_llm(prompt=prompt, system_prompt=system_prompt, temperature=temperature, timeout=timeout)


def call_llm_safe(prompt: str, system_prompt: str = "", temperature: float = 0.3, timeout: int = 30) -> str:
    """Safely call LLM with graceful fallback to empty string on error."""
    try:
        return call_llm(prompt=prompt, system_prompt=system_prompt, temperature=temperature, timeout=timeout)
    except Exception as err:
        print(f"[WARN] LLM tailoring call failed: {err}. Using base content.")
        return ""
