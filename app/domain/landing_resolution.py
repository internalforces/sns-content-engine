"""Domain models for landing URL resolution."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LandingDecision:
    """Resolved landing URL decision for a matched account."""

    landing_url: str
    used_fallback: bool
    matched_rule_index: int | None = None
    matched_tag_hits: tuple[str, ...] = ()
