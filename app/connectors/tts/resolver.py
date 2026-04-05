"""Runtime TTS provider selection with priority-ordered fallback."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import TYPE_CHECKING

from app.connectors.tts.base import TTSInput, TTSOutput, TTSProvider
from app.connectors.tts.fake import FakeTTSProvider
from app.connectors.routing.executor import execute_with_fallback
from app.connectors.routing.models import Route, StepKey
from app.connectors.routing.registry import RouteRegistry

if TYPE_CHECKING:
    from app.config.schemas import AIProvidersConfig


def resolve_tts_provider(
    *,
    environment: Mapping[str, str] | None = None,
    providers_config: "AIProvidersConfig | None" = None,
) -> TTSProvider:
    """Resolve the runtime TTS provider.

    When ``providers_config`` is supplied (Phase 6 config-driven routing),
    routes come from the config file. Otherwise uses env-var auto-detection.

    Single route → returns the concrete provider directly.
    Multiple routes → returns a ``_RoutedTTSProvider`` that tries each in
    priority order and falls back automatically on failure.

    Provider priority (env-var mode):
      1. ElevenLabs  (ELEVENLABS_API_KEY)
      2. Google TTS  (GOOGLE_APPLICATION_CREDENTIALS or GOOGLE_TTS_CREDENTIALS_JSON)
      3. OpenAI TTS  (OPENAI_API_KEY + OPENAI_TTS_MODEL or OPENAI_TTS_VOICE)
      4. Fake        (fallback — no external calls)

    Args:
        environment:      Override for ``os.environ``.
        providers_config: Optional ``AIProvidersConfig`` from providers.yaml.
    """
    env = os.environ if environment is None else environment

    if providers_config is not None:
        registry = RouteRegistry.from_config(providers_config, environment=env)
    else:
        registry = RouteRegistry.from_environment(environment=env)

    routes = registry.resolve_routes(StepKey.TTS_SYNTHESIZE)

    if not routes:
        return FakeTTSProvider()

    if len(routes) == 1:
        return _build_single_tts_provider(routes[0], env)

    return _RoutedTTSProvider(routes=routes, environment=env)


# --------------------------------------------------------------------------- #
# Internal: routed TTS provider
# --------------------------------------------------------------------------- #


class _RoutedTTSProvider:
    """TTSProvider that tries routes in priority order with automatic fallback."""

    def __init__(self, *, routes: list[Route], environment: Mapping[str, str]) -> None:
        self._routes = routes
        self._environment = environment

    def synthesize(self, input: TTSInput) -> TTSOutput:
        return execute_with_fallback(
            step_key=StepKey.TTS_SYNTHESIZE,
            routes=self._routes,
            build_provider=lambda route: _build_single_tts_provider(
                route, self._environment
            ),
            execute=lambda provider, _route: provider.synthesize(input),
        )


def _build_single_tts_provider(
    route: Route,
    environment: Mapping[str, str],
) -> TTSProvider:
    """Instantiate the concrete TTS provider for a given route."""

    env = environment

    if route.provider == "elevenlabs":
        from app.connectors.tts.elevenlabs_provider import ElevenLabsTTSProvider
        # Apply model override from route if not already in env
        if route.model and "ELEVENLABS_MODEL" not in env:
            env = {**env, "ELEVENLABS_MODEL": route.model}
        # Apply voice_id from route params if present
        voice_id = route.get_param("voice_id")
        if voice_id and "ELEVENLABS_VOICE_ID" not in env:
            env = {**env, "ELEVENLABS_VOICE_ID": voice_id}
        return ElevenLabsTTSProvider.from_environment(environment=env)

    if route.provider == "google":
        from app.connectors.tts.google_provider import GoogleTTSProvider
        if route.model and "GOOGLE_TTS_VOICE_NAME" not in env:
            env = {**env, "GOOGLE_TTS_VOICE_NAME": route.model}
        return GoogleTTSProvider.from_environment(environment=env)

    if route.provider == "openai":
        from app.connectors.tts.openai_provider import OpenAITTSProvider
        if route.model and "OPENAI_TTS_MODEL" not in env:
            env = {**env, "OPENAI_TTS_MODEL": route.model}
        return OpenAITTSProvider.from_environment(environment=env)

    if route.provider == "fake":
        return FakeTTSProvider()

    from app.connectors.tts.base import TTSProviderError
    raise TTSProviderError(
        f"Unknown TTS provider: {route.provider!r}. "
        "Supported values: 'elevenlabs', 'google', 'openai', 'fake'."
    )


# --------------------------------------------------------------------------- #
# Helpers (kept for internal use by registry credential check)
# --------------------------------------------------------------------------- #

def _google_credentials_available(environment: Mapping[str, str]) -> bool:
    return (
        "GOOGLE_APPLICATION_CREDENTIALS" in environment
        or "GOOGLE_TTS_CREDENTIALS_JSON" in environment
    )


def _openai_tts_configured(environment: Mapping[str, str]) -> bool:
    """Return True when the caller has explicitly configured OpenAI for TTS."""
    return (
        "OPENAI_TTS_MODEL" in environment
        or "OPENAI_TTS_VOICE" in environment
    )
