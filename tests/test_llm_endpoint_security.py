from __future__ import annotations

import json

import pytest

from sciona.runtime.errors import LLMError
from sciona.runtime.llm.adapter import LLMRequest
from sciona.runtime.llm.providers.openai import OpenAIProvider


class _Response:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        payload = {"choices": [{"message": {"content": "ok"}}]}
        return json.dumps(payload).encode("utf-8")


def _request() -> LLMRequest:
    return LLMRequest(prompt="hello", model="gpt-4.1", temperature=0.0)


def test_openai_provider_rejects_non_https_endpoint() -> None:
    provider = OpenAIProvider(api_endpoint="http://api.openai.com/v1", api_key="k")
    with pytest.raises(LLMError) as exc:
        provider.complete(_request())
    assert exc.value.code == "llm_invalid_endpoint"


def test_openai_provider_rejects_non_allowlisted_host() -> None:
    provider = OpenAIProvider(
        api_endpoint="https://evil.example/v1",
        endpoint_allowlist=("api.openai.com",),
    )
    with pytest.raises(LLMError) as exc:
        provider.complete(_request())
    assert exc.value.code == "llm_invalid_endpoint"


def test_openai_provider_blocks_api_key_to_custom_endpoint_by_default() -> None:
    provider = OpenAIProvider(
        api_endpoint="https://gateway.example/v1",
        endpoint_allowlist=("api.openai.com", "gateway.example"),
        api_key="secret",
    )
    with pytest.raises(LLMError) as exc:
        provider.complete(_request())
    assert exc.value.code == "llm_endpoint_api_key_blocked"


def test_openai_provider_custom_endpoint_without_api_key(monkeypatch) -> None:
    captured = {}

    def _fake_urlopen(req, timeout=0):
        captured["auth"] = req.headers.get("Authorization")
        return _Response()

    monkeypatch.setattr("sciona.runtime.llm.providers.openai_transport.urlopen", _fake_urlopen)
    provider = OpenAIProvider(
        api_endpoint="https://gateway.example/v1",
        endpoint_allowlist=("api.openai.com", "gateway.example"),
    )
    result = provider.complete(_request())
    assert result.text == "ok"
    assert captured["auth"] is None


def test_openai_provider_custom_endpoint_with_explicit_api_key_forward(monkeypatch) -> None:
    captured = {}

    def _fake_urlopen(req, timeout=0):
        captured["auth"] = req.headers.get("Authorization")
        return _Response()

    monkeypatch.setattr("sciona.runtime.llm.providers.openai_transport.urlopen", _fake_urlopen)
    provider = OpenAIProvider(
        api_endpoint="https://gateway.example/v1",
        endpoint_allowlist=("api.openai.com", "gateway.example"),
        allow_api_key_for_custom_endpoint=True,
        api_key="secret",
    )
    result = provider.complete(_request())
    assert result.text == "ok"
    assert captured["auth"] == "Bearer secret"
