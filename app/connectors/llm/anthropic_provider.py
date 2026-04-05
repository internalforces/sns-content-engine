"""Anthropic-backed draft generation provider (Claude)."""

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

DEFAULT_ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_ANTHROPIC_MAX_TOKENS = 2048
DEFAULT_ANTHROPIC_TIMEOUT_SECONDS = 60.0


class AnthropicMessagesClient(Protocol):
    """HTTP/API boundary for Anthropic Messages API calls."""

    def create_message(
        self,
        *,
        model: str,
        system: str,
        messages: list[dict],
        max_tokens: int,
    ) -> object:
        """Create one Anthropic message and return the response object."""


class AnthropicDraftGenerationProvider:
    """Generate draft variants through the Anthropic Messages API.

    This provider satisfies the same DraftGenerationProvider Protocol as
    OpenAIDraftGenerationProvider, so it can be used as a drop-in replacement
    or fallback in a RoutedDraftGenerationProvider chain.
    """

    def __init__(
        self,
        *,
        client: AnthropicMessagesClient,
        model: str = DEFAULT_ANTHROPIC_MODEL,
        max_tokens: int = DEFAULT_ANTHROPIC_MAX_TOKENS,
    ) -> None:
        normalized_model = model.strip()
        if not normalized_model:
            raise DraftGenerationProviderError("ANTHROPIC_MODEL must not be empty")

        self._client = client
        self._model = normalized_model
        self._max_tokens = max_tokens

    @classmethod
    def from_environment(
        cls,
        *,
        environment: Mapping[str, str] | None = None,
        client_factory=None,
    ) -> "AnthropicDraftGenerationProvider":
        """Build a provider from environment variables."""

        resolved_environment = os.environ if environment is None else environment
        _ec = DraftGenerationProviderError
        api_key = require_env(resolved_environment, "ANTHROPIC_API_KEY", error_cls=_ec)
        model = optional_env(
            resolved_environment,
            "ANTHROPIC_MODEL",
            default=DEFAULT_ANTHROPIC_MODEL,
            error_cls=_ec,
        )
        timeout_seconds = resolve_float_env(
            resolved_environment,
            "ANTHROPIC_TIMEOUT_SECONDS",
            default=DEFAULT_ANTHROPIC_TIMEOUT_SECONDS,
            error_cls=_ec,
        )
        resolved_factory = client_factory or _build_default_anthropic_client
        client = resolved_factory(api_key=api_key, timeout_seconds=timeout_seconds)
        return cls(client=client, model=model)

    def generate_variants(self, request: DraftGenerationRequest) -> tuple[str, ...]:
        if request.variant_count not in (2, 3):
            raise ValueError("variant_count must be 2 or 3")

        system_prompt = _build_system_prompt_with_json_instructions(
            base_system=request.system_prompt,
            variant_count=request.variant_count,
        )

        try:
            response = self._client.create_message(
                model=self._model,
                system=system_prompt,
                messages=[{"role": "user", "content": request.user_prompt}],
                max_tokens=self._max_tokens,
            )
        except Exception as exc:
            raise DraftGenerationProviderError(
                f"Anthropic draft generation request failed: {exc}"
            ) from exc

        raw_text = _extract_text_content(response)
        if not raw_text:
            raise DraftGenerationProviderError(
                "Anthropic draft generation returned an empty response"
            )

        return _parse_variants(raw_text, expected_count=request.variant_count)


class _SDKAnthropicClient:
    """Minimal adapter around the official Anthropic SDK."""

    def __init__(self, sdk_client: object) -> None:
        self._sdk_client = sdk_client

    def create_message(
        self,
        *,
        model: str,
        system: str,
        messages: list[dict],
        max_tokens: int,
    ) -> object:
        return self._sdk_client.messages.create(
            model=model,
            system=system,
            messages=messages,
            max_tokens=max_tokens,
        )


def _build_default_anthropic_client(
    *,
    api_key: str,
    timeout_seconds: float,
) -> AnthropicMessagesClient:
    try:
        import anthropic
    except ImportError as exc:
        raise DraftGenerationProviderError(
            "The Anthropic Python SDK is not installed. "
            "Install it with: pip install anthropic"
        ) from exc

    return _SDKAnthropicClient(
        anthropic.Anthropic(api_key=api_key, timeout=timeout_seconds)
    )


def _build_system_prompt_with_json_instructions(
    *,
    base_system: str,
    variant_count: int,
) -> str:
    """Append JSON output instructions to the base system prompt."""

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


def _extract_text_content(response: object) -> str | None:
    """Extract the plain text content from an Anthropic response object."""

    # SDK response: response.content is a list of ContentBlock objects
    content = getattr(response, "content", None)
    if isinstance(content, list):
        parts = []
        for block in content:
            text = getattr(block, "text", None)
            if isinstance(text, str):
                parts.append(text)
        joined = "".join(parts).strip()
        return joined if joined else None

    # Mapping-style response (testing)
    if isinstance(response, dict):
        for block in response.get("content", []):
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text", "").strip()
                if text:
                    return text

    return None


def _parse_variants(
    raw_text: str,
    *,
    expected_count: int,
) -> tuple[str, ...]:
    """Parse and validate JSON variants from the model response."""

    # Strip accidental markdown code fences
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
            "Anthropic draft generation did not return valid JSON"
        ) from exc

    if not isinstance(parsed, dict):
        raise DraftGenerationProviderError(
            "Anthropic draft generation response must be a JSON object"
        )

    variants = parsed.get("variants")
    if not isinstance(variants, list):
        raise DraftGenerationProviderError(
            "Anthropic draft generation response is missing 'variants'"
        )

    if len(variants) != expected_count:
        raise DraftGenerationProviderError(
            f"Anthropic draft generation returned {len(variants)} variants, "
            f"expected {expected_count}"
        )

    if not all(isinstance(v, str) for v in variants):
        raise DraftGenerationProviderError(
            "Anthropic draft generation variants must all be strings"
        )

    return tuple(variants)


