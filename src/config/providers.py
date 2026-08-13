"""
Provider registry for flexible LLM/embedding provider configuration.

This module centralizes all provider configs (API keys, base URLs, models, timeouts)
and maps use-cases (chat, resume, embedding) to specific providers/models.

Users can switch providers via env vars without code changes:
- CHAT_PROVIDER=alibaba|openrouter|gemini
- RESUME_PROVIDER=alibaba|openrouter|gemini
- EMBEDDING_PROVIDER=openrouter|gemini

Adding a new provider:
1. Add entry to PROVIDERS dict below
2. Set env var (e.g., NEW_PROVIDER_API_KEY)
3. Set use-case to new provider (e.g., CHAT_PROVIDER=new_provider)
"""

import os
from dataclasses import dataclass
from typing import Optional, Literal


@dataclass
class ProviderConfig:
    """Configuration for an LLM/embedding provider."""
    name: str
    base_url: str
    api_key_env: str  # Name of env var holding the API key
    models: dict[str, str]  # use_case -> model_id
    timeout: int = 300  # Seconds
    response_format: str = "openai"  # "openai", "anthropic", "anthropic_with_thinking"

    def get_api_key(self) -> str:
        """Retrieve API key from environment."""
        key = os.getenv(self.api_key_env)
        if not key:
            raise ValueError(
                f"API key '{self.api_key_env}' not set. "
                f"Add it to .env or export it."
            )
        return key


# Provider registry
# To add a new provider: add entry here + set env var for API key
PROVIDERS = {
    "alibaba": ProviderConfig(
        name="alibaba",
        base_url="https://token-plan.ap-southeast-1.maas.aliyuncs.com/v1",
        api_key_env="ALIBABA_API_KEY",
        models={
            "chat": "qwen3.6-flash",
            "resume": "qwen3.7-plus",
        },
        timeout=300,
        response_format="anthropic_with_thinking",
    ),
    "openrouter": ProviderConfig(
        name="openrouter",
        base_url="https://openrouter.ai/api/v1",
        api_key_env="OPENROUTER_API_KEY",
        models={
            "chat": "anthropic/claude-opus-4.5",
            "resume": "anthropic/claude-opus-4.5",
            "embedding": "openai/text-embedding-3-small",
        },
        timeout=120,
        response_format="openai",
    ),
    "gemini": ProviderConfig(
        name="gemini",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        api_key_env="GEMINI_API_KEY",
        models={
            "chat": "gemini-2.0-flash-exp",
            "resume": "gemini-2.5-flash",
        },
        timeout=120,
        response_format="openai",
    ),
}

# Use-case → provider mapping (loaded from env vars with defaults)
USE_CASE_PROVIDERS = {
    "chat": os.getenv("CHAT_PROVIDER", "alibaba"),
    "resume": os.getenv("RESUME_PROVIDER", "alibaba"),
    "embedding": os.getenv("EMBEDDING_PROVIDER", "openrouter"),
}


def get_provider(provider_name: str) -> ProviderConfig:
    """Get provider config by name.

    Args:
        provider_name: Key in PROVIDERS dict (e.g., "alibaba", "openrouter")

    Returns:
        ProviderConfig instance

    Raises:
        ValueError: If provider not found
    """
    if provider_name not in PROVIDERS:
        available = ", ".join(PROVIDERS.keys())
        raise ValueError(
            f"Provider '{provider_name}' not found. Available: {available}"
        )
    return PROVIDERS[provider_name]


def get_model_for(use_case: str) -> tuple[str, str, ProviderConfig]:
    """Get (provider_name, model_id, provider_config) for a use-case.

    Args:
        use_case: "chat", "resume", or "embedding"

    Returns:
        Tuple of (provider_name, model_id, provider_config)

    Raises:
        ValueError: If use_case not found or provider not configured
    """
    if use_case not in USE_CASE_PROVIDERS:
        raise ValueError(
            f"Unknown use_case '{use_case}'. "
            f"Available: {', '.join(USE_CASE_PROVIDERS.keys())}"
        )

    provider_name = USE_CASE_PROVIDERS[use_case]
    provider = get_provider(provider_name)

    if use_case not in provider.models:
        raise ValueError(
            f"Provider '{provider_name}' does not support use_case '{use_case}'. "
            f"Available: {', '.join(provider.models.keys())}"
        )

    model_id = provider.models[use_case]
    return provider_name, model_id, provider


def list_providers() -> list[str]:
    """List all available provider names."""
    return list(PROVIDERS.keys())


def list_use_cases() -> dict[str, str]:
    """List all use-cases and their current provider."""
    return {
        use_case: provider_name
        for use_case, provider_name in USE_CASE_PROVIDERS.items()
    }
