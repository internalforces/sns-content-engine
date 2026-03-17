"""Tests for deterministic landing URL resolution."""

from __future__ import annotations

import pytest

from app.config import LandingConfig
from app.services import LandingResolutionError, LandingResolver


def test_resolver_uses_first_matching_rule_in_config_order() -> None:
    resolver = LandingResolver(
        _build_landing_config(
            fallback_url="https://gilgop.cloud/ai-tools",
            rules=(
                {
                    "when_tags_any": ["Agents", "Automation"],
                    "url": "https://gilgop.cloud/ai-agents",
                },
                {
                    "when_tags_any": ["automation", "ai"],
                    "url": "https://gilgop.cloud/ai-automation",
                },
            ),
        )
    )

    decision = resolver.resolve(["  AI  ", "AUTOmation", ""])

    assert decision.landing_url == "https://gilgop.cloud/ai-agents"
    assert decision.used_fallback is False
    assert decision.matched_rule_index == 0
    assert decision.matched_tag_hits == ("automation",)


def test_resolver_returns_fallback_when_no_rule_matches() -> None:
    resolver = LandingResolver(
        _build_landing_config(
            fallback_url="https://gilgop.cloud/ai-tools",
            rules=(
                {
                    "when_tags_any": ["agents"],
                    "url": "https://gilgop.cloud/ai-agents",
                },
            ),
        )
    )

    decision = resolver.resolve(["finance", "markets"])

    assert decision.landing_url == "https://gilgop.cloud/ai-tools"
    assert decision.used_fallback is True
    assert decision.matched_rule_index is None
    assert decision.matched_tag_hits == ()


def test_resolver_rejects_missing_landing_config() -> None:
    with pytest.raises(LandingResolutionError) as exc_info:
        LandingResolver(None)

    assert str(exc_info.value) == "landing configuration is required"


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
