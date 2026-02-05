"""Endpoint validation for the OpenAI provider."""
from __future__ import annotations

from typing import Optional
from urllib.parse import urlparse

from ...errors import LLMError


def has_value(value: Optional[str]) -> bool:
    return bool(value and value.strip())


def validated_endpoint(
    api_endpoint: Optional[str],
    *,
    endpoint_allowlist: tuple[str, ...],
    allow_api_key_for_custom_endpoint: bool,
    has_api_key: bool,
) -> tuple[str, bool]:
    default_endpoint = "https://api.openai.com/v1"
    endpoint = (api_endpoint or default_endpoint).strip().rstrip("/")
    parsed = urlparse(endpoint)
    scheme = (parsed.scheme or "").lower()
    host = (parsed.hostname or "").lower()
    if scheme != "https":
        raise LLMError(
            "LLM api_endpoint must use https.",
            code="llm_invalid_endpoint",
        )
    if not host:
        raise LLMError(
            "LLM api_endpoint must include a valid host.",
            code="llm_invalid_endpoint",
        )
    if parsed.username or parsed.password:
        raise LLMError(
            "LLM api_endpoint must not include inline credentials.",
            code="llm_invalid_endpoint",
        )
    allowlist = {entry.strip().lower() for entry in endpoint_allowlist if entry and entry.strip()}
    if not allowlist:
        allowlist = {"api.openai.com"}
    if host not in allowlist:
        raise LLMError(
            f"LLM api_endpoint host '{host}' is not allowlisted.",
            code="llm_invalid_endpoint",
        )
    default_host = "api.openai.com"
    is_default_host = host == default_host
    if has_api_key and not is_default_host and not allow_api_key_for_custom_endpoint:
        raise LLMError(
            "Refusing to send api_key to custom api_endpoint host. "
            "Set llm.allow_api_key_for_custom_endpoint=true only for trusted endpoints.",
            code="llm_endpoint_api_key_blocked",
        )
    send_auth = has_api_key and (is_default_host or allow_api_key_for_custom_endpoint)
    return endpoint, send_auth


__all__ = ["has_value", "validated_endpoint"]
