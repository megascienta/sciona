"""LLM adapter that dispatches to stateless providers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .providers import load_provider


@dataclass(frozen=True)
class LLMRequest:
    prompt: str
    model: str
    temperature: float = 0.0


@dataclass(frozen=True)
class LLMResponse:
    text: str
    model: str
    provider: str


class Adapter:
    """Simple provider loader/dispatcher."""

    def __init__(
        self,
        provider_name: str,
        *,
        api_key: Optional[str] = None,
        api_endpoint: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
    ) -> None:
        self._provider = load_provider(
            provider_name,
            api_key=api_key,
            api_endpoint=api_endpoint,
            timeout=timeout,
            max_retries=max_retries,
        )

    def complete(self, prompt: str, *, model: str, temperature: float = 0.0) -> LLMResponse:
        request = LLMRequest(prompt=prompt, model=model, temperature=temperature)
        return self._provider.complete(request)

    def probe(self, *, model: str, temperature: float = 0.0) -> None:
        """Check provider connectivity by issuing a minimal request."""
        request = LLMRequest(
            prompt="SCIONA connectivity check.",
            model=model,
            temperature=temperature,
        )
        probe = getattr(self._provider, "probe", None)
        if callable(probe):
            probe(request)
            return
        self._provider.complete(request)
