"""Codex-Wrapper-backed draft generation provider."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from typing import Protocol

from app.connectors.llm._env_helpers import optional_env, require_env, resolve_float_env
from app.connectors.llm.base import (
    DraftGenerationProviderError,
    DraftGenerationRequest,
)

DEFAULT_CODEX_WRAPPER_MODEL = "gpt-5.4-mini"
DEFAULT_CODEX_WRAPPER_TIMEOUT_SECONDS = 30.0
_ALLOWED_REASONING_EFFORTS = frozenset({"none", "low", "medium", "high"})


class CodexWrapperChatCompletionsClient(Protocol):
    """HTTP/API boundary for Codex-Wrapper chat completion calls."""

    def create_completion(self, *, payload: Mapping[str, object]) -> object:
        """Create one chat completion for the given payload."""


class CodexWrapperChatCompletionsClientFactory(Protocol):
    """Factory for Codex-Wrapper chat completion clients."""

    def __call__(
        self,
        *,
        api_key: str,
        base_url: str,
        timeout_seconds: float,
    ) -> CodexWrapperChatCompletionsClient:
        """Build a client for the given credentials and timeout."""


class CodexWrapperDraftGenerationProvider:
    """Generate draft variants through an OpenAI-compatible Codex-Wrapper."""

    def __init__(
        self,
        *,
        client: CodexWrapperChatCompletionsClient,
        model: str = DEFAULT_CODEX_WRAPPER_MODEL,
        reasoning_effort: str | None = None,
    ) -> None:
        normalized_model = model.strip()
        if not normalized_model:
            raise DraftGenerationProviderError("CODEX_WRAPPER_MODEL must not be empty")

        normalized_effort = _normalize_reasoning_effort(reasoning_effort)

        self._client = client
        self._model = normalized_model
        self._reasoning_effort = normalized_effort

    @classmethod
    def from_environment(
        cls,
        *,
        environment: Mapping[str, str] | None = None,
        client_factory: CodexWrapperChatCompletionsClientFactory | None = None,
    ) -> "CodexWrapperDraftGenerationProvider":
        """Build a provider from environment variables."""

        resolved_environment = os.environ if environment is None else environment
        _ec = DraftGenerationProviderError
        base_url = require_env(
            resolved_environment,
            "CODEX_WRAPPER_BASE_URL",
            error_cls=_ec,
        )
        api_key = require_env(
            resolved_environment,
            "CODEX_WRAPPER_API_KEY",
            error_cls=_ec,
        )
        model = optional_env(
            resolved_environment,
            "CODEX_WRAPPER_MODEL",
            default=DEFAULT_CODEX_WRAPPER_MODEL,
            error_cls=_ec,
        )
        timeout_seconds = resolve_float_env(
            resolved_environment,
            "CODEX_WRAPPER_TIMEOUT_SECONDS",
            default=DEFAULT_CODEX_WRAPPER_TIMEOUT_SECONDS,
            error_cls=_ec,
        )
        reasoning_effort = _resolve_reasoning_effort_env(resolved_environment)
        resolved_factory = client_factory or _build_default_codex_wrapper_chat_client
        client = resolved_factory(
            api_key=api_key,
            base_url=base_url.rstrip("/"),
            timeout_seconds=timeout_seconds,
        )
        return cls(
            client=client,
            model=model,
            reasoning_effort=reasoning_effort,
        )

    def generate_variants(self, request: DraftGenerationRequest) -> tuple[str, ...]:
        if request.variant_count not in (2, 3):
            raise ValueError("variant_count must be 2 or 3")

        try:
            response = self._client.create_completion(
                payload=_build_codex_wrapper_payload(
                    request=request,
                    model=self._model,
                    reasoning_effort=self._reasoning_effort,
                )
            )
        except Exception as exc:
            raise DraftGenerationProviderError(
                f"Codex-Wrapper draft generation request failed: {exc}"
            ) from exc

        raw_text = _extract_message_content(response)
        if not raw_text:
            raise DraftGenerationProviderError(
                "Codex-Wrapper draft generation returned an empty response"
            )

        return _parse_variants(raw_text, expected_count=request.variant_count)


class _SDKCodexWrapperChatClient:
    """Minimal adapter around the official OpenAI SDK chat completions API."""

    def __init__(self, sdk_client: object) -> None:
        self._sdk_client = sdk_client

    def create_completion(self, *, payload: Mapping[str, object]) -> object:
        return self._sdk_client.chat.completions.create(**payload)


def _build_default_codex_wrapper_chat_client(
    *,
    api_key: str,
    base_url: str,
    timeout_seconds: float,
) -> CodexWrapperChatCompletionsClient:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise DraftGenerationProviderError(
            "The OpenAI Python SDK is not installed. Reinstall project dependencies to enable Codex-Wrapper draft generation."
        ) from exc

    return _SDKCodexWrapperChatClient(
        OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout_seconds,
        )
    )


def _resolve_reasoning_effort_env(environment: Mapping[str, str]) -> str | None:
    raw = environment.get("CODEX_WRAPPER_REASONING_EFFORT")
    if raw is None:
        return None
    return _normalize_reasoning_effort(raw)


def _normalize_reasoning_effort(reasoning_effort: str | None) -> str | None:
    if reasoning_effort is None:
        return None

    normalized = reasoning_effort.strip().casefold()
    if not normalized:
        raise DraftGenerationProviderError(
            "CODEX_WRAPPER_REASONING_EFFORT is set but empty"
        )

    if normalized not in _ALLOWED_REASONING_EFFORTS:
        allowed = ", ".join(sorted(_ALLOWED_REASONING_EFFORTS))
        raise DraftGenerationProviderError(
            f"CODEX_WRAPPER_REASONING_EFFORT must be one of: {allowed}"
        )

    if normalized == "none":
        return None
    return normalized


def _build_codex_wrapper_payload(
    *,
    request: DraftGenerationRequest,
    model: str,
    reasoning_effort: str | None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": _build_system_prompt_with_json_instructions(
                    base_system=request.system_prompt,
                    variant_count=request.variant_count,
                ),
            },
            {
                "role": "user",
                "content": request.user_prompt,
            },
        ],
        "response_format": {"type": "json_object"},
    }
    if reasoning_effort is not None:
        payload["reasoning_effort"] = reasoning_effort
    return payload


def _build_system_prompt_with_json_instructions(
    *,
    base_system: str,
    variant_count: int,
) -> str:
    json_schema = json.dumps(
        {
            "type": "object",
            "required": ["variants"],
            "properties": {
                "variants": {
                    "type": "array",
                    "minItems": variant_count,
                    "maxItems": variant_count,
                    "items": {"type": "string"},
                }
            },
        },
        indent=2,
    )
    return (
        f"{base_system}\n\n"
        "IMPORTANT: Your entire response must be a single valid JSON object "
        "with no markdown fences, no commentary, and no text outside the JSON.\n\n"
        f"Required JSON schema:\n{json_schema}"
    )


def _extract_message_content(response: object) -> str | None:
    choices = getattr(response, "choices", None)
    if isinstance(choices, list) and choices:
        message = getattr(choices[0], "message", None)
        text = _coerce_content_to_text(getattr(message, "content", None))
        if text:
            return text

    if isinstance(response, Mapping):
        response_choices = response.get("choices")
        if isinstance(response_choices, list) and response_choices:
            first_choice = response_choices[0]
            if isinstance(first_choice, Mapping):
                message = first_choice.get("message")
                if isinstance(message, Mapping):
                    text = _coerce_content_to_text(message.get("content"))
                    if text:
                        return text

    return None


def _coerce_content_to_text(content: object) -> str | None:
    if isinstance(content, str):
        stripped = content.strip()
        return stripped or None

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, Mapping):
                text = item.get("text")
            else:
                text = getattr(item, "text", None)
            if isinstance(text, str) and text.strip():
                parts.append(text.strip())
        if parts:
            return "".join(parts)

    return None


def _parse_variants(
    raw_text: str,
    *,
    expected_count: int,
) -> tuple[str, ...]:
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(
            line for line in lines if not line.strip().startswith("```")
        ).strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise DraftGenerationProviderError(
            "Codex-Wrapper draft generation did not return valid JSON"
        ) from exc

    if not isinstance(parsed, dict):
        raise DraftGenerationProviderError(
            "Codex-Wrapper draft generation response must be a JSON object"
        )

    variants = parsed.get("variants")
    if not isinstance(variants, list):
        raise DraftGenerationProviderError(
            "Codex-Wrapper draft generation response is missing 'variants'"
        )

    if len(variants) != expected_count:
        raise DraftGenerationProviderError(
            "Codex-Wrapper draft generation returned the wrong number of variants"
        )

    if not all(isinstance(variant, str) for variant in variants):
        raise DraftGenerationProviderError(
            "Codex-Wrapper draft generation variants must all be strings"
        )

    return tuple(variants)
