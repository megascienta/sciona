"""Placeholder OpenAI provider."""
from __future__ import annotations

from dataclasses import dataclass
import json
import time
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ..adapter import LLMRequest, LLMResponse
from ...errors import LLMError


@dataclass
class OpenAIProvider:
    api_key: Optional[str] = None
    api_endpoint: Optional[str] = None
    timeout: Optional[float] = None
    max_retries: Optional[int] = None

    def complete(self, request: LLMRequest) -> LLMResponse:
        endpoint = (self.api_endpoint or "https://api.openai.com/v1").rstrip("/")
        url = f"{endpoint}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "sciona-openai",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {
            "model": request.model,
            "temperature": request.temperature,
            "messages": [{"role": "user", "content": request.prompt}],
            "stream": False,
        }
        body = json.dumps(payload).encode("utf-8")
        http_request = Request(url, data=body, headers=headers, method="POST")
        raw = _request_with_retry(
            http_request,
            timeout=self.timeout or 120,
            max_retries=self.max_retries or 0,
        )
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
        return LLMResponse(text=text, model=request.model, provider="openai")

    def probe(self, request: LLMRequest) -> None:
        """Validate that required configuration is present for OpenAI access."""
        if not _has_value(self.api_key) and not _has_value(self.api_endpoint):
            raise LLMError(
                "OpenAI provider requires api_key or api_endpoint in config.",
                code="llm_missing_credentials",
            )
        endpoint = (self.api_endpoint or "https://api.openai.com/v1").rstrip("/")
        url = f"{endpoint}/models"
        headers = {"User-Agent": "sciona-probe"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = Request(url, headers=headers, method="GET")
        try:
            with urlopen(request, timeout=min(self.timeout or 5, 5)):
                return
        except HTTPError as exc:
            if 400 <= exc.code < 500:
                hint = None
                if exc.code in {401, 403}:
                    hint = "Check api_key or api_endpoint credentials in .sciona/config.yaml."
                raise LLMError(
                    f"OpenAI provider probe failed: {exc}",
                    code="llm_invalid_configuration",
                    hint=hint,
                ) from exc
            raise LLMError(
                f"OpenAI provider probe failed: {exc}",
                code="llm_probe_failed",
            ) from exc
        except URLError as exc:
            raise LLMError(
                f"OpenAI provider probe failed: {exc}",
                code="llm_probe_failed",
            ) from exc


def _request_with_retry(
    request: Request,
    *,
    timeout: float,
    max_retries: int,
) -> bytes:
    attempt = 0
    delay = 0.5
    while True:
        try:
            with urlopen(request, timeout=timeout) as response:
                return response.read()
        except HTTPError as exc:
            status = exc.code
            retryable = status in {408, 429} or 500 <= status < 600
            if retryable and attempt < max_retries:
                time.sleep(delay)
                attempt += 1
                delay *= 2
                continue
            detail = exc.read().decode("utf-8", errors="ignore") if exc.fp else str(exc)
            raise LLMError(
                f"OpenAI completion failed: {detail}",
                code="llm_request_failed",
            ) from exc
        except TimeoutError as exc:
            if attempt < max_retries:
                time.sleep(delay)
                attempt += 1
                delay *= 2
                continue
            raise LLMError(
                "OpenAI completion timed out.",
                code="llm_timeout",
            ) from exc
        except URLError as exc:
            if attempt < max_retries:
                time.sleep(delay)
                attempt += 1
                delay *= 2
                continue
            raise LLMError(
                f"OpenAI completion failed: {exc}",
                code="llm_request_failed",
            ) from exc


def _has_value(value: Optional[str]) -> bool:
    return bool(value and value.strip())
