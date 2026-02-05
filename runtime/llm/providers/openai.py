"""OpenAI LLM provider."""
from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Optional
from urllib.request import Request

from ..adapter import LLMRequest, LLMResponse
from .openai_endpoint import has_value, validated_endpoint
from .openai_response import parse_completion_response
from .openai_transport import request_with_retry


@dataclass
class OpenAIProvider:
    api_key: Optional[str] = None
    api_endpoint: Optional[str] = None
    endpoint_allowlist: tuple[str, ...] = ("api.openai.com",)
    allow_api_key_for_custom_endpoint: bool = False
    timeout: Optional[float] = None
    max_retries: Optional[int] = None

    def complete(self, request: LLMRequest) -> LLMResponse:
        endpoint, send_auth = validated_endpoint(
            self.api_endpoint,
            endpoint_allowlist=self.endpoint_allowlist,
            allow_api_key_for_custom_endpoint=self.allow_api_key_for_custom_endpoint,
            has_api_key=has_value(self.api_key),
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
        raw = request_with_retry(
            http_request,
            timeout=self.timeout or 120,
            max_retries=self.max_retries or 0,
        )
        return parse_completion_response(raw, model=request.model)
