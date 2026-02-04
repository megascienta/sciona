"""Placeholder OpenAI provider."""
from __future__ import annotations

from dataclasses import dataclass
import json
import time
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from ..adapter import LLMRequest, LLMResponse
from ...errors import LLMError


@dataclass
class OpenAIProvider:
    api_key: Optional[str] = None
    api_endpoint: Optional[str] = None
    endpoint_allowlist: tuple[str, ...] = ("api.openai.com",)
    allow_api_key_for_custom_endpoint: bool = False
    timeout: Optional[float] = None
    max_retries: Optional[int] = None

    def complete(self, request: LLMRequest) -> LLMResponse:
        endpoint, send_auth = _validated_endpoint(
            self.api_endpoint,
            endpoint_allowlist=self.endpoint_allowlist,
            allow_api_key_for_custom_endpoint=self.allow_api_key_for_custom_endpoint,
            has_api_key=_has_value(self.api_key),
        )
        url = f"{endpoint}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "sciona-openai",
        }
        if send_auth and self.api_key:
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
        endpoint, send_auth = _validated_endpoint(
            self.api_endpoint,
            endpoint_allowlist=self.endpoint_allowlist,
            allow_api_key_for_custom_endpoint=self.allow_api_key_for_custom_endpoint,
            has_api_key=_has_value(self.api_key),
        )
        url = f"{endpoint}/models"
        headers = {"User-Agent": "sciona-probe"}
        if send_auth and self.api_key:
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


def _validated_endpoint(
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
