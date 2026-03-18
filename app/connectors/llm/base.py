"""Interfaces for draft generation providers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class DraftGenerationProviderError(RuntimeError):
    """Raised when a draft generation provider cannot fulfill a request."""


@dataclass(frozen=True, slots=True)
class DraftGenerationRequest:
    """Normalized request payload for channel draft generation."""

    channel: str
    system_prompt: str
    user_prompt: str
    landing_url: str
    max_chars: int
    variant_count: int
    title: str
    key_points: tuple[str, ...]


class DraftGenerationProvider(Protocol):
    """Provider boundary for turning prompts into draft variants."""

    def generate_variants(self, request: DraftGenerationRequest) -> tuple[str, ...]:
        """Return channel-ready draft variants for the given request."""
