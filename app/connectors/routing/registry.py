"""Route registry: builds and resolves provider routes from environment config."""

from __future__ import annotations

import dataclasses
import os
from collections.abc import Mapping
from typing import TYPE_CHECKING

from app.connectors.routing.models import Route, StepKey

if TYPE_CHECKING:
    from app.config.schemas import AIProvidersConfig, AccountAIConfig

# --------------------------------------------------------------------------- #
# Default model identifiers
# --------------------------------------------------------------------------- #

_DEFAULT_OPENAI_LLM_MODEL = "gpt-5.4-mini"
_DEFAULT_ANTHROPIC_LLM_MODEL = "claude-haiku-4-5-20251001"
_DEFAULT_OPENAI_TTS_MODEL = "tts-1"
_DEFAULT_ELEVENLABS_TTS_MODEL = "eleven_multilingual_v2"
_DEFAULT_GOOGLE_TTS_MODEL = "en-US-Standard-C"


class RouteRegistry:
    """Holds a prioritized list of routes and resolves them by step key.

    Routes are ordered by priority (ascending) on resolution so the caller
    always receives a ready-to-iterate list: try index 0 first, fall back
    to index 1, and so on.

    Typical usage::

        registry = RouteRegistry.from_environment()
        routes = registry.resolve_routes(StepKey.DRAFT_GENERATE)
        # → [Route(provider="openai", priority=1), Route(provider="anthropic", priority=2)]
    """

    def __init__(self, routes: list[Route]) -> None:
        self._routes = routes

    # ------------------------------------------------------------------ #
    # Resolution
    # ------------------------------------------------------------------ #

    def resolve_routes(self, step_key: str) -> list[Route]:
        """Return enabled routes for *step_key* sorted by ascending priority."""

        return sorted(
            [r for r in self._routes if r.step_key == step_key and r.enabled],
            key=lambda r: (r.priority, self._routes.index(r)),
        )

    # ------------------------------------------------------------------ #
    # Factory
    # ------------------------------------------------------------------ #

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str] | None = None,
    ) -> "RouteRegistry":
        """Build a registry from environment variables.

        LLM routes (step_key = "draft_generate"):
            Priority 1  OpenAI   — requires OPENAI_API_KEY
            Priority 2  Anthropic — requires ANTHROPIC_API_KEY

        TTS routes (step_key = "tts_synthesize"):
            Priority 1  ElevenLabs — requires ELEVENLABS_API_KEY
            Priority 2  Google     — requires GOOGLE_APPLICATION_CREDENTIALS
            Priority 3  OpenAI     — requires OPENAI_API_KEY +
                                     (OPENAI_TTS_MODEL or OPENAI_TTS_VOICE)
        """

        env = os.environ if environment is None else environment
        routes: list[Route] = []

        # ---- LLM routes ----
        # All three LLM step keys (draft_generate, metadata_generate,
        # image_prompt_generate) share the same provider pool so that
        # with_account_override() and from_config() work consistently
        # regardless of which step is being served.
        for llm_step in _LLM_STEP_KEYS:
            if "OPENAI_API_KEY" in env:
                routes.append(
                    Route(
                        step_key=llm_step,
                        provider="openai",
                        model=env.get("OPENAI_MODEL", _DEFAULT_OPENAI_LLM_MODEL),
                        priority=1,
                    )
                )

            if "ANTHROPIC_API_KEY" in env:
                routes.append(
                    Route(
                        step_key=llm_step,
                        provider="anthropic",
                        model=env.get("ANTHROPIC_MODEL", _DEFAULT_ANTHROPIC_LLM_MODEL),
                        priority=2,
                    )
                )

        # ---- TTS routes ----
        if "ELEVENLABS_API_KEY" in env:
            routes.append(
                Route(
                    step_key=StepKey.TTS_SYNTHESIZE,
                    provider="elevenlabs",
                    model=env.get("ELEVENLABS_MODEL", _DEFAULT_ELEVENLABS_TTS_MODEL),
                    priority=1,
                    params=(
                        ("voice_id", env.get("ELEVENLABS_VOICE_ID", "")),
                        ("api_key", env["ELEVENLABS_API_KEY"]),
                    ),
                )
            )

        if _google_credentials_available(env):
            routes.append(
                Route(
                    step_key=StepKey.TTS_SYNTHESIZE,
                    provider="google",
                    model=env.get("GOOGLE_TTS_VOICE_NAME", _DEFAULT_GOOGLE_TTS_MODEL),
                    priority=2,
                )
            )

        if "OPENAI_API_KEY" in env and _openai_tts_explicitly_configured(env):
            routes.append(
                Route(
                    step_key=StepKey.TTS_SYNTHESIZE,
                    provider="openai",
                    model=env.get("OPENAI_TTS_MODEL", _DEFAULT_OPENAI_TTS_MODEL),
                    priority=3,
                )
            )

        return cls(routes)

    # ------------------------------------------------------------------ #
    # Mutation helpers (for runtime overrides without rebuilding from env)
    # ------------------------------------------------------------------ #

    def with_route(self, route: Route) -> "RouteRegistry":
        """Return a new registry with *route* appended."""
        return RouteRegistry([*self._routes, route])

    def without_provider(self, step_key: str, provider: str) -> "RouteRegistry":
        """Return a new registry with all routes matching step_key+provider removed."""
        return RouteRegistry(
            [
                r
                for r in self._routes
                if not (r.step_key == step_key and r.provider == provider)
            ]
        )

    def all_routes(self) -> list[Route]:
        """Return all registered routes (enabled and disabled)."""
        return list(self._routes)

    # ------------------------------------------------------------------ #
    # Config-driven factory (Phase 6)
    # ------------------------------------------------------------------ #

    @classmethod
    def from_config(
        cls,
        config: "AIProvidersConfig",
        *,
        environment: Mapping[str, str] | None = None,
    ) -> "RouteRegistry":
        """Build a registry from a ``providers.yaml`` config object.

        Each route in the config is included only when the corresponding
        provider's API key (or credentials) is present in the environment.
        This preserves the security property that a provider is never used
        unless explicitly configured and credentialed.

        When no routes survive the credential check (e.g. all specified
        providers are uncredentialed in the current environment), the method
        falls back to the standard env-var auto-detection so the system
        degrades gracefully rather than silently producing no routes.

        Args:
            config:       Validated ``AIProvidersConfig`` from providers.yaml.
            environment:  Override for ``os.environ`` (useful in tests).

        Returns:
            A new ``RouteRegistry`` populated from the config file.
        """
        env = os.environ if environment is None else environment
        routes: list[Route] = []

        for rc in config.routes:
            if not rc.enabled:
                continue
            if not _provider_credentials_available(rc.provider, env):
                continue
            params = tuple(rc.params.items()) if rc.params else ()
            routes.append(
                Route(
                    step_key=rc.step,
                    provider=rc.provider,
                    model=rc.model,
                    priority=rc.priority,
                    enabled=True,
                    params=params,
                )
            )

        # Graceful degradation: fall back to env-var detection when no routes
        # survive the credential check.
        if not routes:
            return cls.from_environment(environment=env)

        return cls(routes)

    def with_account_override(
        self,
        ai_config: "AccountAIConfig",
    ) -> "RouteRegistry":
        """Return a new registry with per-account provider preferences applied.

        The account's preferred provider is promoted to priority 0 (highest)
        for all applicable step keys in its category:
          - ``llm_provider`` applies to: draft_generate, metadata_generate,
            image_prompt_generate
          - ``tts_provider`` applies to: tts_synthesize

        If the account specifies a model override (``llm_model`` / ``tts_model``),
        the model field on the promoted route is updated accordingly.

        When the preferred provider has no existing route in the registry (i.e.
        it is not credentialed), the account override is silently skipped for
        that step so the system degrades gracefully.

        Args:
            ai_config: Per-account AI settings from accounts.yaml ``ai:`` block.

        Returns:
            A new ``RouteRegistry`` or ``self`` when no overrides apply.
        """
        extra_routes: list[Route] = []

        if ai_config.llm_provider:
            for step_key in _LLM_STEP_KEYS:
                existing = next(
                    (
                        r for r in self._routes
                        if r.step_key == step_key and r.provider == ai_config.llm_provider
                    ),
                    None,
                )
                if existing is not None:
                    extra_routes.append(
                        dataclasses.replace(
                            existing,
                            priority=0,
                            model=ai_config.llm_model if ai_config.llm_model else existing.model,
                        )
                    )

        if ai_config.tts_provider:
            for step_key in _TTS_STEP_KEYS:
                existing = next(
                    (
                        r for r in self._routes
                        if r.step_key == step_key and r.provider == ai_config.tts_provider
                    ),
                    None,
                )
                if existing is not None:
                    extra_routes.append(
                        dataclasses.replace(
                            existing,
                            priority=0,
                            model=ai_config.tts_model if ai_config.tts_model else existing.model,
                        )
                    )

        if not extra_routes:
            return self  # nothing to override

        return RouteRegistry([*extra_routes, *self._routes])


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

#: Step keys served by LLM providers (used for per-account LLM override).
_LLM_STEP_KEYS: tuple[str, ...] = (
    StepKey.DRAFT_GENERATE,
    StepKey.METADATA_GENERATE,
    StepKey.IMAGE_PROMPT_GENERATE,
)

#: Step keys served by TTS providers (used for per-account TTS override).
_TTS_STEP_KEYS: tuple[str, ...] = (StepKey.TTS_SYNTHESIZE,)

#: Maps provider identifiers to required environment variable names.
#: None means no credential is required (e.g. "fake" provider).
_PROVIDER_CREDENTIAL_ENV: dict[str, str | None] = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "elevenlabs": "ELEVENLABS_API_KEY",
    "google": "GOOGLE_APPLICATION_CREDENTIALS",
    "fake": None,
}


def _provider_credentials_available(provider: str, env: Mapping[str, str]) -> bool:
    """Return True when the named provider's credential is present in *env*.

    Unknown providers (not in ``_PROVIDER_CREDENTIAL_ENV``) are treated as
    always-credentialed to support future provider additions without changing
    this helper.
    """
    key = _PROVIDER_CREDENTIAL_ENV.get(provider.casefold())
    if key is None:
        # Fake provider or unknown provider — assume available.
        return True
    if key == "GOOGLE_APPLICATION_CREDENTIALS":
        return _google_credentials_available(env)
    return key in env


def _google_credentials_available(env: Mapping[str, str]) -> bool:
    return (
        "GOOGLE_APPLICATION_CREDENTIALS" in env
        or "GOOGLE_TTS_CREDENTIALS_JSON" in env
    )


def _openai_tts_explicitly_configured(env: Mapping[str, str]) -> bool:
    """True when the operator has set OpenAI-specific TTS env vars."""
    return "OPENAI_TTS_MODEL" in env or "OPENAI_TTS_VOICE" in env
