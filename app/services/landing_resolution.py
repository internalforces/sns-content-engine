"""Landing URL resolution service."""

from __future__ import annotations

from collections.abc import Iterable

from app.config import LandingConfig
from app.domain import LandingDecision, normalize_title_text


class LandingResolutionError(ValueError):
    """Raised when landing configuration cannot be resolved safely."""


class LandingResolver:
    """Resolve an account landing URL from normalized source tags."""

    def __init__(self, landing_config: LandingConfig | None) -> None:
        if landing_config is None:
            raise LandingResolutionError("landing configuration is required")
        self._landing_config = landing_config

    def resolve(self, tags: Iterable[str]) -> LandingDecision:
        """Return the resolved landing decision for the provided tags."""

        normalized_tags = _normalize_input_tags(tags)

        for index, rule in enumerate(self._landing_config.rules):
            matched_tag_hits = tuple(
                normalized_tag
                for normalized_tag in _normalize_rule_tags(rule.when_tags_any)
                if normalized_tag in normalized_tags
            )
            if matched_tag_hits:
                return LandingDecision(
                    landing_url=str(rule.url),
                    used_fallback=False,
                    matched_rule_index=index,
                    matched_tag_hits=matched_tag_hits,
                )

        return LandingDecision(
            landing_url=str(self._landing_config.fallback_url),
            used_fallback=True,
        )


def _normalize_input_tags(tags: Iterable[str]) -> frozenset[str]:
    normalized_tags: set[str] = set()

    for tag in tags:
        normalized_tag = _normalize_tag(tag)
        if normalized_tag is None:
            continue
        normalized_tags.add(normalized_tag)

    return frozenset(normalized_tags)


def _normalize_rule_tags(tags: Iterable[str]) -> tuple[str, ...]:
    normalized_tags: list[str] = []

    for tag in tags:
        normalized_tag = _normalize_tag(tag)
        if normalized_tag is None:
            continue
        normalized_tags.append(normalized_tag)

    return tuple(normalized_tags)


def _normalize_tag(tag: str) -> str | None:
    stripped_tag = tag.strip()
    if not stripped_tag:
        return None

    try:
        return normalize_title_text(stripped_tag)
    except ValueError:
        return None
