"""Fallback execution engine for multi-route provider chains."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TypeVar

from app.connectors.routing.models import Route

T = TypeVar("T")

_logger = logging.getLogger(__name__)


class AllProvidersFailedError(RuntimeError):
    """Raised when every route in a fallback chain has failed.

    Attributes:
        step_key: The pipeline step that was being executed.
        errors:   List of (provider_name, exception) pairs in the order
                  they were tried.
    """

    def __init__(self, step_key: str, errors: list[tuple[str, Exception]]) -> None:
        self.step_key = step_key
        self.errors = errors
        if errors:
            detail = "; ".join(f"{p}: {e}" for p, e in errors)
            message = f"All providers failed for step '{step_key}': {detail}"
        else:
            message = f"No routes configured for step '{step_key}'"
        super().__init__(message)


def execute_with_fallback(
    step_key: str,
    routes: list[Route],
    build_provider: Callable[[Route], object],
    execute: Callable[[object, Route], T],
    *,
    on_failure: Callable[[Route, Exception], None] | None = None,
) -> T:
    """Execute routes in priority order, falling back on provider failure.

    Args:
        step_key:       Pipeline step identifier (used in logs and errors).
        routes:         Prioritized list of routes to try (index 0 = highest priority).
                        The list should already be sorted by the RouteRegistry.
        build_provider: Callable that takes a Route and returns a provider instance.
                        May raise — the exception is caught and treated as a route failure.
        execute:        Callable that takes (provider, route) and returns the result.
                        May raise — triggers fallback to the next route.
        on_failure:     Optional callback called after each route failure with
                        (failed_route, exception).  Useful for logging / metrics.

    Returns:
        The result of the first successful provider execution.

    Raises:
        AllProvidersFailedError: When every route raises or no routes are provided.

    Example::

        result = execute_with_fallback(
            step_key=StepKey.DRAFT_GENERATE,
            routes=registry.resolve_routes(StepKey.DRAFT_GENERATE),
            build_provider=lambda route: _build_llm_provider(route, env),
            execute=lambda provider, route: provider.generate_variants(request),
        )
    """

    if not routes:
        raise AllProvidersFailedError(step_key, [])

    errors: list[tuple[str, Exception]] = []

    for route in routes:
        try:
            provider = build_provider(route)
        except Exception as exc:
            _logger.warning(
                "Failed to build provider %r for step %r: %s",
                route.provider,
                step_key,
                exc,
            )
            errors.append((route.provider, exc))
            if on_failure is not None:
                on_failure(route, exc)
            continue

        try:
            result = execute(provider, route)
        except Exception as exc:
            _logger.warning(
                "Provider %r failed for step %r (priority %d): %s",
                route.provider,
                step_key,
                route.priority,
                exc,
            )
            errors.append((route.provider, exc))
            if on_failure is not None:
                on_failure(route, exc)
            continue

        _logger.debug(
            "Provider %r succeeded for step %r (priority %d)",
            route.provider,
            step_key,
            route.priority,
        )
        return result

    raise AllProvidersFailedError(step_key, errors)
