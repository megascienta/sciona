"""LLM provider registry."""

from __future__ import annotations

from typing import Optional


def load_provider(
    name: str,
    *,
    api_key: Optional[str],
    api_endpoint: Optional[str],
    endpoint_allowlist: tuple[str, ...] | None = None,
    allow_api_key_for_custom_endpoint: bool = False,
    timeout: Optional[float] = None,
    max_retries: Optional[int] = None,
):
    normalized = name.lower()
    if normalized == "openai":
        from .openai import OpenAIProvider

        return OpenAIProvider(
            api_key=api_key,
            api_endpoint=api_endpoint,
            endpoint_allowlist=endpoint_allowlist or ("api.openai.com",),
            allow_api_key_for_custom_endpoint=allow_api_key_for_custom_endpoint,
            timeout=timeout,
            max_retries=max_retries,
        )
    raise ValueError(f"Unknown LLM provider '{name}'.")


__all__ = ["load_provider"]
