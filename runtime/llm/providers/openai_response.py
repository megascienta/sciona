"""Response parsing helpers for OpenAI payloads."""

from __future__ import annotations

import json

from ..adapter import LLMResponse
from ...errors import LLMError


def parse_completion_response(raw: bytes, *, model: str) -> LLMResponse:
    try:
        data = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise LLMError(
            "OpenAI completion returned invalid JSON.",
            code="llm_invalid_response",
        ) from exc
    choices = data.get("choices") or []
    if not choices:
        raise LLMError(
            "OpenAI completion returned no choices.",
            code="llm_empty_response",
        )
    message = choices[0].get("message") or {}
    text = message.get("content")
    if not isinstance(text, str):
        raise LLMError(
            "OpenAI completion returned empty content.",
            code="llm_empty_response",
        )
    return LLMResponse(text=text, model=model, provider="openai")


__all__ = ["parse_completion_response"]
