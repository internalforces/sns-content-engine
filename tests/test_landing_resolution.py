"""Tests for deterministic landing URL resolution."""

from __future__ import annotations

import pytest

from app.config import LandingConfig, LandingRuleConfig
from app.services import LandingResolutionError, LandingResolver


def test_resolver_uses_first_matching_rule_in_config_order() -> None:
    resolver = LandingResolver(
        _build_landing_config(
            fallback_url="https://odtoolbase.com/guides",
            rules=(
                {
                    "when_tags_any": ["Agents", "Automation"],
                    "url": "https://odtoolbase.com/guides/ai-agent-workflows-small-teams",
                },
                {
                    "when_tags_any": ["automation", "ai"],
                    "url": "https://odtoolbase.com/guides/ai-research-stack-content-pipelines",
                },
            ),
        )
    )

    decision = resolver.resolve(["  AI  ", "AUTOmation", ""])

    assert decision.landing_url == "https://odtoolbase.com/guides/ai-agent-workflows-small-teams"
    assert decision.used_fallback is False
    assert decision.matched_rule_index == 0
    assert decision.matched_tag_hits == ("automation",)


def test_resolver_returns_fallback_when_no_rule_matches() -> None:
    resolver = LandingResolver(
        _build_landing_config(
            fallback_url="https://odtoolbase.com/guides",
            rules=(
                {
                    "when_tags_any": ["agents"],
                    "url": "https://odtoolbase.com/guides/ai-agent-workflows-small-teams",
                },
            ),
        )
    )

    decision = resolver.resolve(["finance", "markets"])

    assert decision.landing_url == "https://odtoolbase.com/guides"
    assert decision.used_fallback is True
    assert decision.matched_rule_index is None
    assert decision.matched_tag_hits == ()


def test_resolver_preserves_matched_tag_order_from_rule_definition() -> None:
    resolver = LandingResolver(
        _build_landing_config(
            fallback_url="https://odtoolbase.com/guides",
            rules=(
                {
                    "when_tags_any": ["Automation", "AI", "Automation"],
                    "url": "https://odtoolbase.com/guides/ai-research-stack-content-pipelines",
                },
            ),
        )
    )

    decision = resolver.resolve(["ai", "automation"])

    assert decision.landing_url == "https://odtoolbase.com/guides/ai-research-stack-content-pipelines"
    assert decision.used_fallback is False
    assert decision.matched_rule_index == 0
    assert decision.matched_tag_hits == ("automation", "ai")


def test_resolver_rejects_missing_landing_config() -> None:
    with pytest.raises(LandingResolutionError) as exc_info:
        LandingResolver(None)

    assert str(exc_info.value) == "landing configuration is required"


def test_resolver_rejects_rule_tags_that_collapse_after_normalization() -> None:
    invalid_rule = LandingRuleConfig.model_construct(
        when_tags_any=("!!!",),
        url="https://odtoolbase.com/guides/ai-agent-workflows-small-teams",
    )
    invalid_config = LandingConfig.model_construct(
        fallback_url="https://odtoolbase.com/guides",
        rules=(invalid_rule,),
    )

    with pytest.raises(LandingResolutionError) as exc_info:
        LandingResolver(invalid_config)

    assert str(exc_info.value) == "landing rule tags must contain non-empty alphanumeric tags"


def _build_landing_config(
    *,
    fallback_url: str,
    rules: tuple[dict[str, object], ...],
) -> LandingConfig:
    return LandingConfig.model_validate(
        {
            "fallback_url": fallback_url,
            "rules": list(rules),
        }
    )
