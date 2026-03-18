"""Tests for the OpenAI-backed LLM provider and resolver."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.connectors.llm import (
    DraftGenerationProviderError,
    FakeLLMProvider,
    OpenAIDraftGenerationProvider,
    resolve_draft_generation_provider,
)
from app.connectors.llm.base import DraftGenerationRequest


def test_openai_provider_builds_expected_payload_and_uses_env_defaults() -> None:
    captured: dict[str, object] = {}
    client = _RecordingOpenAIClient(_StubOpenAIResponse('{"variants":["one","two"]}'))

    def factory(*, api_key: str, timeout_seconds: float):
        captured["api_key"] = api_key
        captured["timeout_seconds"] = timeout_seconds
        return client

    provider = OpenAIDraftGenerationProvider.from_environment(
        environment={"OPENAI_API_KEY": "sk-test"},
        client_factory=factory,
    )
    request = _build_request(variant_count=2)

    assert provider.generate_variants(request) == ("one", "two")
    assert captured == {
        "api_key": "sk-test",
        "timeout_seconds": 30.0,
    }

    payload = client.payloads[0]
    assert payload["model"] == "gpt-5.4-mini"
    assert payload["reasoning"] == {"effort": "none"}
    assert payload["instructions"] == request.system_prompt
    assert payload["input"] == request.user_prompt
    assert payload["text"]["format"]["type"] == "json_schema"
    assert payload["text"]["format"]["name"] == "draft_generation_result"
    assert payload["text"]["format"]["strict"] is True
    assert payload["text"]["format"]["schema"] == {
        "type": "object",
        "additionalProperties": False,
        "required": ["variants"],
        "properties": {
            "variants": {
                "type": "array",
                "minItems": 2,
                "maxItems": 2,
                "items": {
                    "type": "string",
                },
            }
        },
    }


def test_openai_provider_honors_explicit_env_overrides() -> None:
    captured: dict[str, object] = {}
    client = _RecordingOpenAIClient(_StubOpenAIResponse('{"variants":["one","two"]}'))

    def factory(*, api_key: str, timeout_seconds: float):
        captured["api_key"] = api_key
        captured["timeout_seconds"] = timeout_seconds
        return client

    provider = OpenAIDraftGenerationProvider.from_environment(
        environment={
            "OPENAI_API_KEY": "sk-test",
            "OPENAI_MODEL": "gpt-5.4",
            "OPENAI_REASONING_EFFORT": "medium",
            "OPENAI_TIMEOUT_SECONDS": "12.5",
        },
        client_factory=factory,
    )

    provider.generate_variants(_build_request(variant_count=2))

    payload = client.payloads[0]
    assert payload["model"] == "gpt-5.4"
    assert payload["reasoning"] == {"effort": "medium"}
    assert captured["timeout_seconds"] == 12.5


@pytest.mark.parametrize(
    ("output_text", "message"),
    [
        ("not json", "did not return valid JSON"),
        ('["one","two"]', "must be a JSON object"),
        ("{}", "missing 'variants'"),
        ('{"variants":["one"]}', "wrong number of variants"),
        ('{"variants":[1,"two"]}', "must all be strings"),
    ],
)
def test_openai_provider_rejects_malformed_structured_output(
    output_text: str,
    message: str,
) -> None:
    provider = OpenAIDraftGenerationProvider(
        client=_RecordingOpenAIClient(_StubOpenAIResponse(output_text)),
    )

    with pytest.raises(DraftGenerationProviderError, match=message):
        provider.generate_variants(_build_request(variant_count=2))


def test_openai_provider_surfaces_api_client_errors() -> None:
    provider = OpenAIDraftGenerationProvider(
        client=_RecordingOpenAIClient(RuntimeError("network down")),
    )

    with pytest.raises(DraftGenerationProviderError, match="OpenAI draft generation request failed: network down"):
        provider.generate_variants(_build_request(variant_count=2))


def test_resolver_uses_fake_provider_when_api_key_is_absent() -> None:
    provider = resolve_draft_generation_provider(environment={})

    assert isinstance(provider, FakeLLMProvider)


def test_resolver_uses_openai_provider_when_api_key_is_present() -> None:
    provider = resolve_draft_generation_provider(
        environment={"OPENAI_API_KEY": "sk-test"},
        client_factory=lambda **_: _RecordingOpenAIClient(_StubOpenAIResponse('{"variants":["one","two"]}')),
    )

    assert isinstance(provider, OpenAIDraftGenerationProvider)


def test_resolver_rejects_blank_api_key() -> None:
    with pytest.raises(DraftGenerationProviderError, match="OPENAI_API_KEY is set but empty"):
        resolve_draft_generation_provider(environment={"OPENAI_API_KEY": "   "})


@dataclass
class _StubOpenAIResponse:
    output_text: str


class _RecordingOpenAIClient:
    def __init__(self, response_or_exception: object) -> None:
        self._response_or_exception = response_or_exception
        self.payloads: list[dict[str, object]] = []

    def create_response(self, *, payload) -> object:
        self.payloads.append(payload)
        if isinstance(self._response_or_exception, Exception):
            raise self._response_or_exception
        return self._response_or_exception


def _build_request(*, variant_count: int) -> DraftGenerationRequest:
    return DraftGenerationRequest(
        channel="x",
        system_prompt="System prompt",
        user_prompt="User prompt",
        landing_url="https://example.com/post",
        max_chars=140,
        variant_count=variant_count,
        title="Useful update",
        key_points=("Useful update", "First point", "Second point"),
    )
