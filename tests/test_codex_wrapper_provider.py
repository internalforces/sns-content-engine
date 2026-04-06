"""Tests for the Codex-Wrapper-backed draft generation provider."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.connectors.llm import (
    CodexWrapperDraftGenerationProvider,
    DraftGenerationProviderError,
)
from app.connectors.llm.base import DraftGenerationRequest


def test_codex_wrapper_provider_builds_expected_payload_and_uses_env_defaults() -> None:
    captured: dict[str, object] = {}
    client = _RecordingCodexWrapperClient(
        _StubChatCompletionResponse('{"variants":["one","two"]}')
    )

    def factory(*, api_key: str, base_url: str, timeout_seconds: float):
        captured["api_key"] = api_key
        captured["base_url"] = base_url
        captured["timeout_seconds"] = timeout_seconds
        return client

    provider = CodexWrapperDraftGenerationProvider.from_environment(
        environment={
            "CODEX_WRAPPER_BASE_URL": "https://wrapper.example.com/v1/",
            "CODEX_WRAPPER_API_KEY": "cw-test",
        },
        client_factory=factory,
    )
    request = _build_request(variant_count=2)

    assert provider.generate_variants(request) == ("one", "two")
    assert captured == {
        "api_key": "cw-test",
        "base_url": "https://wrapper.example.com/v1",
        "timeout_seconds": 30.0,
    }

    payload = client.payloads[0]
    assert payload["model"] == "gpt-5.4-mini"
    assert payload["response_format"] == {"type": "json_object"}
    assert payload["messages"][1] == {"role": "user", "content": request.user_prompt}
    assert "reasoning_effort" not in payload

    system_prompt = payload["messages"][0]["content"]
    assert system_prompt.startswith(request.system_prompt)
    assert "single valid JSON object" in system_prompt
    assert '"minItems": 2' in system_prompt
    assert '"maxItems": 2' in system_prompt


def test_codex_wrapper_provider_honors_explicit_env_overrides() -> None:
    captured: dict[str, object] = {}
    client = _RecordingCodexWrapperClient(
        _StubChatCompletionResponse('{"variants":["one","two"]}')
    )

    def factory(*, api_key: str, base_url: str, timeout_seconds: float):
        captured["api_key"] = api_key
        captured["base_url"] = base_url
        captured["timeout_seconds"] = timeout_seconds
        return client

    provider = CodexWrapperDraftGenerationProvider.from_environment(
        environment={
            "CODEX_WRAPPER_BASE_URL": "https://wrapper.example.com/v1",
            "CODEX_WRAPPER_API_KEY": "cw-test",
            "CODEX_WRAPPER_MODEL": "gpt-5.4",
            "CODEX_WRAPPER_TIMEOUT_SECONDS": "12.5",
            "CODEX_WRAPPER_REASONING_EFFORT": "medium",
        },
        client_factory=factory,
    )

    provider.generate_variants(_build_request(variant_count=2))

    payload = client.payloads[0]
    assert payload["model"] == "gpt-5.4"
    assert payload["reasoning_effort"] == "medium"
    assert captured == {
        "api_key": "cw-test",
        "base_url": "https://wrapper.example.com/v1",
        "timeout_seconds": 12.5,
    }


@pytest.mark.parametrize(
    ("environment", "message"),
    [
        (
            {
                "CODEX_WRAPPER_BASE_URL": "https://wrapper.example.com/v1",
                "CODEX_WRAPPER_API_KEY": "cw-test",
                "CODEX_WRAPPER_REASONING_EFFORT": "invalid",
            },
            "CODEX_WRAPPER_REASONING_EFFORT must be one of",
        ),
        (
            {
                "CODEX_WRAPPER_BASE_URL": "https://wrapper.example.com/v1",
                "CODEX_WRAPPER_API_KEY": "cw-test",
                "CODEX_WRAPPER_REASONING_EFFORT": "   ",
            },
            "CODEX_WRAPPER_REASONING_EFFORT is set but empty",
        ),
    ],
)
def test_codex_wrapper_provider_validates_reasoning_effort(
    environment: dict[str, str],
    message: str,
) -> None:
    with pytest.raises(DraftGenerationProviderError, match=message):
        CodexWrapperDraftGenerationProvider.from_environment(environment=environment)


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
def test_codex_wrapper_provider_rejects_malformed_structured_output(
    output_text: str,
    message: str,
) -> None:
    provider = CodexWrapperDraftGenerationProvider(
        client=_RecordingCodexWrapperClient(_StubChatCompletionResponse(output_text)),
    )

    with pytest.raises(DraftGenerationProviderError, match=message):
        provider.generate_variants(_build_request(variant_count=2))


def test_codex_wrapper_provider_surfaces_api_client_errors() -> None:
    provider = CodexWrapperDraftGenerationProvider(
        client=_RecordingCodexWrapperClient(RuntimeError("network down")),
    )

    with pytest.raises(
        DraftGenerationProviderError,
        match="Codex-Wrapper draft generation request failed: network down",
    ):
        provider.generate_variants(_build_request(variant_count=2))


def test_codex_wrapper_provider_rejects_empty_chat_completion_content() -> None:
    provider = CodexWrapperDraftGenerationProvider(
        client=_RecordingCodexWrapperClient(_StubChatCompletionResponse("   ")),
    )

    with pytest.raises(
        DraftGenerationProviderError,
        match="Codex-Wrapper draft generation returned an empty response",
    ):
        provider.generate_variants(_build_request(variant_count=2))


@dataclass
class _StubChatCompletionResponse:
    output_text: str

    @property
    def choices(self) -> list[object]:
        return [_StubChatChoice(message=_StubChatMessage(content=self.output_text))]


@dataclass
class _StubChatChoice:
    message: object


@dataclass
class _StubChatMessage:
    content: str


class _RecordingCodexWrapperClient:
    def __init__(self, response_or_exception: object) -> None:
        self._response_or_exception = response_or_exception
        self.payloads: list[dict[str, object]] = []

    def create_completion(self, *, payload) -> object:
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
