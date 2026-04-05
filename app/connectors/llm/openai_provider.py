"""OpenAI-backed draft generation provider."""

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

DEFAULT_OPENAI_MODEL = "gpt-5.4-mini"
DEFAULT_OPENAI_REASONING_EFFORT = "none"
DEFAULT_OPENAI_TIMEOUT_SECONDS = 30.0
_ALLOWED_REASONING_EFFORTS = frozenset({"none", "low", "medium", "high"})


class OpenAIResponsesClient(Protocol):
    """HTTP/API boundary for OpenAI Responses API calls."""

    def create_response(self, *, payload: Mapping[str, object]) -> object:
        """Create one OpenAI response for the given payload."""


class OpenAIResponsesClientFactory(Protocol):
    """Factory for OpenAI response clients."""

    def __call__(self, *, api_key: str, timeout_seconds: float) -> OpenAIResponsesClient:
        """Build a client for the given API key and timeout."""


class OpenAIDraftGenerationProvider:
    """Generate draft variants through the OpenAI Responses API."""

    def __init__(
        self,
        *,
        client: OpenAIResponsesClient,
        model: str = DEFAULT_OPENAI_MODEL,
        reasoning_effort: str = DEFAULT_OPENAI_REASONING_EFFORT,
    ) -> None:
        normalized_model = model.strip()
        if not normalized_model:
            raise DraftGenerationProviderError("OPENAI_MODEL must not be empty")

        normalized_effort = reasoning_effort.strip().casefold()
        if normalized_effort not in _ALLOWED_REASONING_EFFORTS:
            allowed = ", ".join(sorted(_ALLOWED_REASONING_EFFORTS))
            raise DraftGenerationProviderError(
                f"OPENAI_REASONING_EFFORT must be one of: {allowed}"
            )

        self._client = client
        self._model = normalized_model
        self._reasoning_effort = normalized_effort

    @classmethod
    def from_environment(
        cls,
        *,
        environment: Mapping[str, str] | None = None,
        client_factory: OpenAIResponsesClientFactory | None = None,
    ) -> "OpenAIDraftGenerationProvider":
        """Build a provider from environment variables."""

        resolved_environment = os.environ if environment is None else environment
        _ec = DraftGenerationProviderError
        api_key = require_env(resolved_environment, "OPENAI_API_KEY", error_cls=_ec)
        model = optional_env(
            resolved_environment,
            "OPENAI_MODEL",
            default=DEFAULT_OPENAI_MODEL,
            error_cls=_ec,
        )
        reasoning_effort = optional_env(
            resolved_environment,
            "OPENAI_REASONING_EFFORT",
            default=DEFAULT_OPENAI_REASONING_EFFORT,
            error_cls=_ec,
        )
        timeout_seconds = resolve_float_env(
            resolved_environment,
            "OPENAI_TIMEOUT_SECONDS",
            default=DEFAULT_OPENAI_TIMEOUT_SECONDS,
            error_cls=_ec,
        )
        resolved_client_factory = client_factory or _build_default_openai_responses_client
        client = resolved_client_factory(api_key=api_key, timeout_seconds=timeout_seconds)
        return cls(
            client=client,
            model=model,
            reasoning_effort=reasoning_effort,
        )

    def generate_variants(self, request: DraftGenerationRequest) -> tuple[str, ...]:
        if request.variant_count not in (2, 3):
            raise ValueError("variant_count must be 2 or 3")

        try:
            response = self._client.create_response(
                payload=_build_openai_payload(
                    request=request,
                    model=self._model,
                    reasoning_effort=self._reasoning_effort,
                )
            )
        except Exception as exc:
            raise DraftGenerationProviderError(
                f"OpenAI draft generation request failed: {exc}"
            ) from exc

        output_text = _extract_output_text(response)
        if not output_text:
            raise DraftGenerationProviderError(
                "OpenAI draft generation returned an empty structured response"
            )

        try:
            parsed = json.loads(output_text)
        except json.JSONDecodeError as exc:
            raise DraftGenerationProviderError(
                "OpenAI draft generation did not return valid JSON"
            ) from exc

        if not isinstance(parsed, dict):
            raise DraftGenerationProviderError(
                "OpenAI draft generation response must be a JSON object"
            )

        variants = parsed.get("variants")
        if not isinstance(variants, list):
            raise DraftGenerationProviderError(
                "OpenAI draft generation response is missing 'variants'"
            )

        if len(variants) != request.variant_count:
            raise DraftGenerationProviderError(
                "OpenAI draft generation returned the wrong number of variants"
            )

        if not all(isinstance(variant, str) for variant in variants):
            raise DraftGenerationProviderError(
                "OpenAI draft generation variants must all be strings"
            )

        return tuple(variants)


class _SDKOpenAIResponsesClient:
    """Minimal adapter around the official OpenAI SDK."""

    def __init__(self, sdk_client: object) -> None:
        self._sdk_client = sdk_client

    def create_response(self, *, payload: Mapping[str, object]) -> object:
        return self._sdk_client.responses.create(**payload)


def _build_default_openai_responses_client(
    *,
    api_key: str,
    timeout_seconds: float,
) -> OpenAIResponsesClient:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise DraftGenerationProviderError(
            "The OpenAI Python SDK is not installed. Reinstall project dependencies to enable OpenAI draft generation."
        ) from exc

    return _SDKOpenAIResponsesClient(
        OpenAI(
            api_key=api_key,
            timeout=timeout_seconds,
        )
    )


def _build_openai_payload(
    *,
    request: DraftGenerationRequest,
    model: str,
    reasoning_effort: str,
) -> dict[str, object]:
    return {
        "model": model,
        "reasoning": {"effort": reasoning_effort},
        "instructions": request.system_prompt,
        "input": request.user_prompt,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "draft_generation_result",
                "strict": True,
                "schema": _build_variants_schema(request.variant_count),
            }
        },
    }


def _build_variants_schema(variant_count: int) -> dict[str, object]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["variants"],
        "properties": {
            "variants": {
                "type": "array",
                "minItems": variant_count,
                "maxItems": variant_count,
                "items": {
                    "type": "string",
                },
            }
        },
    }


def _extract_output_text(response: object) -> str | None:
    attribute_value = getattr(response, "output_text", None)
    if isinstance(attribute_value, str) and attribute_value.strip():
        return attribute_value.strip()

    if isinstance(response, Mapping):
        mapping_value = response.get("output_text")
        if isinstance(mapping_value, str) and mapping_value.strip():
            return mapping_value.strip()

    return None


