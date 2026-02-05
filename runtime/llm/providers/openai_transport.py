"""HTTP transport and retry for OpenAI requests."""
from __future__ import annotations

import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ...errors import LLMError


def request_with_retry(
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


__all__ = ["request_with_retry", "urlopen"]
