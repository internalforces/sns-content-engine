"""Runtime provider selection for draft generation with fallback routing."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import TYPE_CHECKING

from app.connectors.llm.base import DraftGenerationProvider, DraftGenerationRequest
from app.connectors.llm.codex_wrapper_provider import (
    CodexWrapperChatCompletionsClientFactory,
    CodexWrapperDraftGenerationProvider,
)
from app.connectors.llm.fake import FakeLLMProvider
from app.connectors.llm.openai_provider import (
    OpenAIDraftGenerationProvider,
    OpenAIResponsesClientFactory,
)
from app.connectors.routing.executor import execute_with_fallback
from app.connectors.routing.models import Route, StepKey
from app.connectors.routing.registry import RouteRegistry

if TYPE_CHECKING:
    from app.config.schemas import AIProvidersConfig


def resolve_draft_generation_provider(
    *,
    environment: Mapping[str, str] | None = None,
    client_factory: OpenAIResponsesClientFactory | None = None,
    codex_wrapper_client_factory: CodexWrapperChatCompletionsClientFactory | None = None,
    providers_config: "AIProvidersConfig | None" = None,
) -> DraftGenerationProvider:
    """Resolve the runtime draft generation provider from environment.

    When multiple provider keys are present, returns a RoutedDraftGenerationProvider
    that tries providers in priority order (OpenAI → Anthropic → Codex-Wrapper
    for env auto-detection, or config priority order when ``providers_config``
    is supplied) and falls back automatically on failure.

    When no provider keys are present, returns FakeLLMProvider for local
    development and testing.

    This function is fully backward-compatible: callers that previously received
    an OpenAIDraftGenerationProvider will now receive either the same provider
    (single route) or a routed wrapper (multiple routes) — both satisfy the
    DraftGenerationProvider Protocol unchanged.

    Args:
        environment:      Override for ``os.environ``.
        client_factory:   Optional OpenAI client factory (used in tests).
        codex_wrapper_client_factory:
                          Optional Codex-Wrapper chat client factory (used in tests).
        providers_config: When provided, routes are built from the config file
                          (Phase 6 config-driven routing). Falls back to
                          env-var auto-detection when ``None``.
    """

    resolved_environment = os.environ if environment is None else environment

    if providers_config is not None:
        registry = RouteRegistry.from_config(
            providers_config, environment=resolved_environment
        )
    else:
        registry = RouteRegistry.from_environment(resolved_environment)

    routes = registry.resolve_routes(StepKey.DRAFT_GENERATE)

    if not routes:
        return FakeLLMProvider()

    if len(routes) == 1:
        return _build_single_provider(
            routes[0],
            resolved_environment,
            client_factory,
            codex_wrapper_client_factory,
        )

    return _RoutedDraftGenerationProvider(
        routes=routes,
        environment=resolved_environment,
        client_factory=client_factory,
        codex_wrapper_client_factory=codex_wrapper_client_factory,
    )


# --------------------------------------------------------------------------- #
# Internal: routed provider wrapping the fallback executor
# --------------------------------------------------------------------------- #

class _RoutedDraftGenerationProvider:
    """DraftGenerationProvider that executes a prioritised fallback chain.

    Caller code never needs to reference this class directly; it is returned
    transparently by resolve_draft_generation_provider().
    """

    def __init__(
        self,
        *,
        routes: list[Route],
        environment: Mapping[str, str],
        client_factory: OpenAIResponsesClientFactory | None,
        codex_wrapper_client_factory: CodexWrapperChatCompletionsClientFactory | None,
    ) -> None:
        self._routes = routes
        self._environment = environment
        self._client_factory = client_factory
        self._codex_wrapper_client_factory = codex_wrapper_client_factory

    def generate_variants(self, request: DraftGenerationRequest) -> tuple[str, ...]:
        return execute_with_fallback(
            step_key=StepKey.DRAFT_GENERATE,
            routes=self._routes,
            build_provider=lambda route: _build_single_provider(
                route,
                self._environment,
                self._client_factory,
                self._codex_wrapper_client_factory,
            ),
            execute=lambda provider, _route: provider.generate_variants(request),
        )


def _build_single_provider(
    route: Route,
    environment: Mapping[str, str],
    client_factory: OpenAIResponsesClientFactory | None,
    codex_wrapper_client_factory: CodexWrapperChatCompletionsClientFactory | None,
) -> DraftGenerationProvider:
    """Instantiate the concrete provider for a given route."""

    if route.provider == "openai":
        env_override = _with_model_override(environment, route.model, "OPENAI_MODEL")
        return OpenAIDraftGenerationProvider.from_environment(
            environment=env_override,
            client_factory=client_factory,
        )

    if route.provider == "anthropic":
        from app.connectors.llm.anthropic_provider import AnthropicDraftGenerationProvider
        env_override = _with_model_override(environment, route.model, "ANTHROPIC_MODEL")
        return AnthropicDraftGenerationProvider.from_environment(
            environment=env_override,
        )

    if route.provider == "codex_wrapper":
        env_override = _with_model_override(
            environment,
            route.model,
            "CODEX_WRAPPER_MODEL",
        )
        return CodexWrapperDraftGenerationProvider.from_environment(
            environment=env_override,
            client_factory=codex_wrapper_client_factory,
        )

    if route.provider == "fake":
        return FakeLLMProvider()

    from app.connectors.llm.base import DraftGenerationProviderError
    raise DraftGenerationProviderError(
        f"Unknown LLM provider: {route.provider!r}. "
        "Supported values: 'openai', 'anthropic', 'codex_wrapper', 'fake'."
    )


def _with_model_override(
    environment: Mapping[str, str],
    model: str | None,
    env_key: str,
) -> Mapping[str, str]:
    """Return a view of environment with the model key set to *model* if provided."""

    if model is None or env_key in environment:
        return environment
    return {**environment, env_key: model}
