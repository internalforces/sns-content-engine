"""Shared connector environment-variable helpers."""

from __future__ import annotations

from collections.abc import Mapping


def has_non_empty_env(environment: Mapping[str, str], name: str) -> bool:
    """Return True when *name* is present and not blank after stripping."""
    raw = environment.get(name)
    return raw is not None and bool(raw.strip())
