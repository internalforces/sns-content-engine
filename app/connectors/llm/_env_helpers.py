"""Shared environment-variable helpers for LLM connector providers.

These utilities are used by openai_provider, anthropic_provider, and
text_generation to resolve and validate environment variables.  Keeping
them in one place eliminates the three-way duplication that existed before
Phase 6 / review fix M3.

All helpers accept an ``error_cls`` parameter so each provider can raise its
own domain-specific exception (``DraftGenerationProviderError`` vs
``TextGenerationError``) while sharing the same validation logic.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def require_env(
    environment: Mapping[str, str],
    name: str,
    *,
    error_cls: type[Exception],
) -> str:
    """Return the value of *name* from *environment*, stripping whitespace.

    Raises:
        error_cls: If the variable is absent or set to an empty/blank string.
    """
    if name not in environment:
        raise error_cls(f"{name} is required")
    value = environment[name].strip()
    if not value:
        raise error_cls(f"{name} is set but empty")
    return value


def optional_env(
    environment: Mapping[str, str],
    name: str,
    *,
    default: str,
    error_cls: type[Exception],
) -> str:
    """Return the value of *name* from *environment*, or *default* if absent.

    Raises:
        error_cls: If the variable is present but set to an empty/blank string.
    """
    if name not in environment:
        return default
    value = environment[name].strip()
    if not value:
        raise error_cls(f"{name} is set but empty")
    return value


def resolve_float_env(
    environment: Mapping[str, str],
    name: str,
    *,
    default: float,
    error_cls: type[Exception],
) -> float:
    """Return *name* parsed as a positive float, or *default* if absent.

    Raises:
        error_cls: If the variable is present but blank, non-numeric, or <= 0.
    """
    raw = environment.get(name)
    if raw is None:
        return default
    normalized = raw.strip()
    if not normalized:
        raise error_cls(f"{name} is set but empty")
    try:
        value = float(normalized)
    except ValueError as exc:
        raise error_cls(f"{name} must be a positive number") from exc
    if value <= 0:
        raise error_cls(f"{name} must be a positive number")
    return value
