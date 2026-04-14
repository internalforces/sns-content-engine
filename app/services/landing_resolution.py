"""Landing URL resolution service."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from app.config import LandingConfig, LandingRuleConfig
from app.domain import LandingDecision, normalize_title_text

_INVALID_RULE_TAGS_MESSAGE = "landing rule tags must contain non-empty alphanumeric tags"


class LandingResolutionError(ValueError):
    """Raised when landing configuration cannot be resolved safely."""


@dataclass(frozen=True, slots=True)
class _CompiledLandingRule:
    """Normalized landing rule cached for repeated resolution calls."""

    landing_url: str
    normalized_tags: tuple[str, ...]


class LandingResolver:
    """Resolve an account landing URL from normalized source tags."""

    def __init__(self, landing_config: LandingConfig | None) -> None:
        if landing_config is None:
            raise LandingResolutionError("landing configuration is required")
        if landing_config.fallback_url is None:
            raise LandingResolutionError("landing fallback_url is required for static resolution")
        self._fallback_url = str(landing_config.fallback_url)
        self._rules = tuple(_compile_rule(rule) for rule in landing_config.rules)

    def resolve(self, tags: Iterable[str]) -> LandingDecision:
        """Return the resolved landing decision for the provided tags."""

        normalized_tags = _normalize_input_tags(tags)

        for index, rule in enumerate(self._rules):
            matched_tag_hits = tuple(
                normalized_tag
                for normalized_tag in rule.normalized_tags
                if normalized_tag in normalized_tags
            )
            if matched_tag_hits:
                return LandingDecision(
                    landing_url=rule.landing_url,
                    used_fallback=False,
                    matched_rule_index=index,
                    matched_tag_hits=matched_tag_hits,
                )

        return LandingDecision(
            landing_url=self._fallback_url,
            used_fallback=True,
        )


def _compile_rule(rule: LandingRuleConfig) -> _CompiledLandingRule:
    return _CompiledLandingRule(
        landing_url=str(rule.url),
        normalized_tags=_normalize_rule_tags(rule.when_tags_any),
    )


def _normalize_input_tags(tags: Iterable[str]) -> frozenset[str]:
    normalized_tags: set[str] = set()

    for tag in tags:
        normalized_tag = _normalize_input_tag(tag)
        if normalized_tag is None:
            continue
        normalized_tags.add(normalized_tag)

    return frozenset(normalized_tags)


def _normalize_rule_tags(tags: Iterable[str]) -> tuple[str, ...]:
    normalized_tags: list[str] = []
    seen: set[str] = set()

    for tag in tags:
        normalized_tag = _normalize_configured_rule_tag(tag)
        if normalized_tag in seen:
            continue
        seen.add(normalized_tag)
        normalized_tags.append(normalized_tag)

    if not normalized_tags:
        raise LandingResolutionError(_INVALID_RULE_TAGS_MESSAGE)

    return tuple(normalized_tags)


def _normalize_input_tag(tag: str) -> str | None:
    stripped_tag = tag.strip()
    if not stripped_tag:
        return None

    try:
        return normalize_title_text(stripped_tag)
    except ValueError:
        return None


def _normalize_configured_rule_tag(tag: str) -> str:
    stripped_tag = tag.strip()
    if not stripped_tag:
        raise LandingResolutionError(_INVALID_RULE_TAGS_MESSAGE)

    try:
        return normalize_title_text(stripped_tag)
    except ValueError as exc:
        raise LandingResolutionError(_INVALID_RULE_TAGS_MESSAGE) from exc
