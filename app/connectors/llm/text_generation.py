"""Generic single-output text generation layer for structured AI calls.

This module provides a lightweight text generation abstraction used by services
that need one structured JSON response from an LLM (e.g. metadata generation),
as opposed to the draft-variant workflow which always produces 2-3 variants.

Provider priority: OpenAI (1) → Anthropic (2) → Fake (fallback).
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from app.connectors._env_helpers import has_non_empty_env
from app.connectors.llm._env_helpers import (
    optional_env,
    require_env,
    resolve_float_env,
)

if TYPE_CHECKING:
    from app.config.schemas import AIProvidersConfig

DEFAULT_OPENAI_TEXT_MODEL = "gpt-4o-mini"
DEFAULT_OPENAI_TIMEOUT_SECONDS = 30.0
DEFAULT_ANTHROPIC_TEXT_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_ANTHROPIC_MAX_TOKENS = 1024
DEFAULT_ANTHROPIC_TIMEOUT_SECONDS = 60.0


# --------------------------------------------------------------------------- #
# Public types
# --------------------------------------------------------------------------- #


class TextGenerationError(RuntimeError):
    """Raised when a text generation provider cannot fulfill a request."""


@dataclass(frozen=True, slots=True)
class TextGenerationRequest:
    """Minimal prompt payload for single-output text generation."""

    system_prompt: str
    user_prompt: str


class TextGenerationProvider(Protocol):
    """Provider boundary for turning a prompt pair into a single text response."""

    def generate(self, request: TextGenerationRequest) -> str:
        """Return the model's text response for the given request."""


# --------------------------------------------------------------------------- #
# Fake provider (tests / local dev)
# --------------------------------------------------------------------------- #


class FakeTextGenerationProvider:
    """Return a deterministic empty-metadata JSON without external API calls."""

    _STUB_RESPONSE = (
        '{"thumbnail_prompt":"A clean informational graphic",'
        '"tags":["news","analysis"],'
        '"seo_description":"An article summary.",'
        '"classification":"news"}'
    )

    def generate(self, request: TextGenerationRequest) -> str:  # noqa: ARG002
        return self._STUB_RESPONSE


# --------------------------------------------------------------------------- #
# Anthropic provider
# --------------------------------------------------------------------------- #


class _AnthropicMessagesClient(Protocol):
    """Minimal HTTP boundary for Anthropic Messages API calls."""

    def create_message(
        self,
        *,
        model: str,
        system: str,
        messages: list[dict],
        max_tokens: int,
    ) -> object: ...


class _SDKAnthropicMessagesClient:
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


def _build_anthropic_client(*, api_key: str, timeout_seconds: float) -> _AnthropicMessagesClient:
    try:
        import anthropic
    except ImportError as exc:
        raise TextGenerationError(
            "The Anthropic Python SDK is not installed. "
            "Install it with: pip install anthropic"
        ) from exc

    return _SDKAnthropicMessagesClient(
        anthropic.Anthropic(api_key=api_key, timeout=timeout_seconds)
    )


class AnthropicTextGenerationProvider:
    """Single-output text generation via the Anthropic Messages API."""

    def __init__(
        self,
        *,
        client: _AnthropicMessagesClient,
        model: str = DEFAULT_ANTHROPIC_TEXT_MODEL,
        max_tokens: int = DEFAULT_ANTHROPIC_MAX_TOKENS,
    ) -> None:
        normalized_model = model.strip()
        if not normalized_model:
            raise TextGenerationError("ANTHROPIC_MODEL must not be empty")
        self._client = client
        self._model = normalized_model
        self._max_tokens = max_tokens

    @classmethod
    def from_environment(
        cls,
        *,
        environment: Mapping[str, str] | None = None,
    ) -> "AnthropicTextGenerationProvider":
        """Build a provider from environment variables."""
        env = os.environ if environment is None else environment
        _ec = TextGenerationError
        api_key = require_env(env, "ANTHROPIC_API_KEY", error_cls=_ec)
        model = optional_env(env, "ANTHROPIC_MODEL", default=DEFAULT_ANTHROPIC_TEXT_MODEL, error_cls=_ec)
        timeout = resolve_float_env(
            env, "ANTHROPIC_TIMEOUT_SECONDS", default=DEFAULT_ANTHROPIC_TIMEOUT_SECONDS, error_cls=_ec
        )
        client = _build_anthropic_client(api_key=api_key, timeout_seconds=timeout)
        return cls(client=client, model=model)

    def generate(self, request: TextGenerationRequest) -> str:
        try:
            response = self._client.create_message(
                model=self._model,
                system=request.system_prompt,
                messages=[{"role": "user", "content": request.user_prompt}],
                max_tokens=self._max_tokens,
            )
        except Exception as exc:
            raise TextGenerationError(
                f"Anthropic text generation request failed: {exc}"
            ) from exc

        text = _extract_anthropic_text(response)
        if not text:
            raise TextGenerationError("Anthropic text generation returned an empty response")
        return text


def _extract_anthropic_text(response: object) -> str | None:
    """Extract plain text from an Anthropic response object or dict."""
    content = getattr(response, "content", None)
    if isinstance(content, list):
        parts = [
            block.text
            for block in content
            if isinstance(getattr(block, "text", None), str)
        ]
        joined = "".join(parts).strip()
        return joined or None

    if isinstance(response, dict):
        for block in response.get("content", []):
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text", "").strip()
                if text:
                    return text
    return None


# --------------------------------------------------------------------------- #
# OpenAI provider
# --------------------------------------------------------------------------- #


class _OpenAIChatClient(Protocol):
    """Minimal HTTP boundary for OpenAI chat completions."""

    def create_completion(
        self,
        *,
        model: str,
        messages: list[dict],
    ) -> object: ...


class _SDKOpenAIChatClient:
    """Minimal adapter around the official OpenAI SDK chat completions."""

    def __init__(self, sdk_client: object) -> None:
        self._sdk_client = sdk_client

    def create_completion(self, *, model: str, messages: list[dict]) -> object:
        return self._sdk_client.chat.completions.create(model=model, messages=messages)


def _build_openai_chat_client(*, api_key: str, timeout_seconds: float) -> _OpenAIChatClient:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise TextGenerationError(
            "The OpenAI Python SDK is not installed. "
            "Reinstall project dependencies to enable OpenAI text generation."
        ) from exc
    return _SDKOpenAIChatClient(OpenAI(api_key=api_key, timeout=timeout_seconds))


class OpenAITextGenerationProvider:
    """Single-output text generation via the OpenAI Chat Completions API."""

    def __init__(
        self,
        *,
        client: _OpenAIChatClient,
        model: str = DEFAULT_OPENAI_TEXT_MODEL,
    ) -> None:
        normalized_model = model.strip()
        if not normalized_model:
            raise TextGenerationError("OPENAI_MODEL must not be empty")
        self._client = client
        self._model = normalized_model

    @classmethod
    def from_environment(
        cls,
        *,
        environment: Mapping[str, str] | None = None,
    ) -> "OpenAITextGenerationProvider":
        """Build a provider from environment variables."""
        env = os.environ if environment is None else environment
        _ec = TextGenerationError
        api_key = require_env(env, "OPENAI_API_KEY", error_cls=_ec)
        model = optional_env(env, "OPENAI_MODEL", default=DEFAULT_OPENAI_TEXT_MODEL, error_cls=_ec)
        timeout = resolve_float_env(
            env, "OPENAI_TIMEOUT_SECONDS", default=DEFAULT_OPENAI_TIMEOUT_SECONDS, error_cls=_ec
        )
        client = _build_openai_chat_client(api_key=api_key, timeout_seconds=timeout)
        return cls(client=client, model=model)

    def generate(self, request: TextGenerationRequest) -> str:
        try:
            response = self._client.create_completion(
                model=self._model,
                messages=[
                    {"role": "system", "content": request.system_prompt},
                    {"role": "user", "content": request.user_prompt},
                ],
            )
        except Exception as exc:
            raise TextGenerationError(
                f"OpenAI text generation request failed: {exc}"
            ) from exc

        text = _extract_openai_text(response)
        if not text:
            raise TextGenerationError("OpenAI text generation returned an empty response")
        return text


def _extract_openai_text(response: object) -> str | None:
    """Extract plain text from an OpenAI chat completion response."""
    # SDK response: response.choices[0].message.content
    choices = getattr(response, "choices", None)
    if isinstance(choices, list) and choices:
        choice = choices[0]
        message = getattr(choice, "message", None)
        if message is not None:
            content = getattr(message, "content", None)
            if isinstance(content, str) and content.strip():
                return content.strip()

    # Mapping-style response (testing)
    if isinstance(response, dict):
        choices_list = response.get("choices", [])
        if choices_list:
            msg = choices_list[0].get("message", {})
            content = msg.get("content", "")
            if isinstance(content, str) and content.strip():
                return content.strip()
    return None


# --------------------------------------------------------------------------- #
# Resolver
# --------------------------------------------------------------------------- #


def resolve_text_generation_provider(
    *,
    environment: Mapping[str, str] | None = None,
    providers_config: "AIProvidersConfig | None" = None,
) -> TextGenerationProvider:
    """Resolve the runtime text generation provider.

    When ``providers_config`` is supplied (Phase 6 config-driven routing),
    the provider is chosen from the ``metadata_generate`` routes in the config.
    Otherwise falls back to env-var priority order:
        1. OpenAI   — when OPENAI_API_KEY is set
        2. Anthropic — when ANTHROPIC_API_KEY is set
        3. Fake     — no keys present (local dev / tests)

    Args:
        environment:      Override for ``os.environ``.
        providers_config: Optional ``AIProvidersConfig`` from providers.yaml.
                          When provided, the first credentialed route for
                          ``metadata_generate`` step determines the provider.
    """
    from app.connectors.routing.models import StepKey
    from app.connectors.routing.registry import RouteRegistry

    env = os.environ if environment is None else environment

    if providers_config is not None:
        registry = RouteRegistry.from_config(providers_config, environment=env)
        routes = registry.resolve_routes(StepKey.METADATA_GENERATE)
        if routes:
            top = routes[0]
            return _build_text_provider_for_route(top, env)

    # Env-var fallback (original behaviour)
    if has_non_empty_env(env, "OPENAI_API_KEY"):
        return OpenAITextGenerationProvider.from_environment(environment=env)

    if has_non_empty_env(env, "ANTHROPIC_API_KEY"):
        return AnthropicTextGenerationProvider.from_environment(environment=env)

    return FakeTextGenerationProvider()


def _build_text_provider_for_route(
    route: object,
    environment: Mapping[str, str],
) -> TextGenerationProvider:
    """Instantiate a concrete TextGenerationProvider from a Route."""
    provider = getattr(route, "provider", None)
    model = getattr(route, "model", None)

    if provider == "openai":
        env = {**environment, "OPENAI_MODEL": model} if model and "OPENAI_MODEL" not in environment else environment
        return OpenAITextGenerationProvider.from_environment(environment=env)

    if provider == "anthropic":
        env = {**environment, "ANTHROPIC_MODEL": model} if model and "ANTHROPIC_MODEL" not in environment else environment
        return AnthropicTextGenerationProvider.from_environment(environment=env)

    if provider == "fake":
        return FakeTextGenerationProvider()

    # Unknown provider — fall back to env detection
    if has_non_empty_env(environment, "OPENAI_API_KEY"):
        return OpenAITextGenerationProvider.from_environment(environment=environment)
    if has_non_empty_env(environment, "ANTHROPIC_API_KEY"):
        return AnthropicTextGenerationProvider.from_environment(environment=environment)
    return FakeTextGenerationProvider()
