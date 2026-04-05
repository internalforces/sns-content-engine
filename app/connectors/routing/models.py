"""Route and step key data models for the provider routing layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class StepKey:
    """Well-known step identifiers used to look up routes.

    Each constant maps to a pipeline step that can be served by
    one or more providers in priority order.
    """

    DRAFT_GENERATE = "draft_generate"
    TTS_SYNTHESIZE = "tts_synthesize"
    METADATA_GENERATE = "metadata_generate"
    IMAGE_PROMPT_GENERATE = "image_prompt_generate"


@dataclass(frozen=True, slots=True)
class Route:
    """Single provider route for a given pipeline step.

    Routes are sorted by priority (ascending) before execution.
    The fallback executor tries each enabled route in order and moves
    to the next one when a provider raises an exception.

    Attributes:
        step_key:  The pipeline step this route serves (see StepKey).
        provider:  Provider identifier — "openai", "anthropic",
                   "elevenlabs", "google", "fake".
        model:     Provider-specific model identifier. None uses
                   the provider's default.
        priority:  Execution order. Lower value = tried first.
                   Routes with equal priority are tried in definition order.
        enabled:   When False the route is excluded from resolution.
        params:    Extra provider-specific parameters (e.g. voice_id,
                   reasoning_effort). Frozen via tuple for hashability.
    """

    step_key: str
    provider: str
    priority: int = 1
    model: str | None = None
    enabled: bool = True
    params: tuple[tuple[str, Any], ...] = field(default_factory=tuple)

    def get_param(self, key: str, default: Any = None) -> Any:
        """Return the value of a named extra parameter."""
        for k, v in self.params:
            if k == key:
                return v
        return default
