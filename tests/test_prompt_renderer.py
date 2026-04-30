"""Tests for prompt template rendering."""

from __future__ import annotations

import pytest

from app.config import PromptProfileConfig
from app.services import PromptRenderer, PromptRenderingError
from app.services.prompt_renderer import build_domain_sensitivity


def test_prompt_renderer_renders_profile_with_full_context() -> None:
    renderer = PromptRenderer()
    profile = PromptProfileConfig(
        system_template="System for {{ account_key }} on {{ channel }} ({{ max_chars }})",
        user_template="Write about {{ title }} -> {{ landing_url }} :: {{ key_points|length }}",
    )

    rendered = renderer.render(
        profile,
        context={
            "account_key": "ai_tools_daily",
            "channel": "x",
            "max_chars": 280,
            "title": "Useful AI workflows",
            "landing_url": "https://gilgop.cloud/ai-tools",
            "key_points": ("Use repeatable prompts", "Keep the review loop tight"),
        },
    )

    assert rendered.system_prompt == "System for ai_tools_daily on x (280)"
    assert rendered.user_prompt == "Write about Useful AI workflows -> https://gilgop.cloud/ai-tools :: 2"


def test_prompt_renderer_rejects_missing_template_variables() -> None:
    renderer = PromptRenderer()
    profile = PromptProfileConfig(
        system_template="System {{ missing_value }}",
        user_template="User {{ title }}",
    )

    with pytest.raises(PromptRenderingError, match="missing_value"):
        renderer.render(profile, context={"title": "Useful AI workflows"})


def test_prompt_renderer_supports_source_policy_conditionals_and_fallbacks() -> None:
    renderer = PromptRenderer()
    profile = PromptProfileConfig(
        system_template=(
            "System {{ policy_mode }} "
            "{% if require_attribution %}required{% else %}optional{% endif %} "
            "{{ source_name or source_url or 'the source' }}"
        ),
        user_template="User {{ article_summary or summary }} -> {{ landing_url }}",
    )

    rendered = renderer.render(
        profile,
        context={
            "policy_mode": "restricted",
            "require_attribution": True,
            "source_name": None,
            "source_url": "https://example.com/articles/1",
            "article_summary": None,
            "summary": "Verified update from a public source.",
            "landing_url": "https://newsroom.example.com/daily-brief",
        },
    )

    assert rendered.system_prompt == (
        "System restricted required https://example.com/articles/1"
    )
    assert (
        rendered.user_prompt
        == "User Verified update from a public source. -> https://newsroom.example.com/daily-brief"
    )


def test_prompt_renderer_supports_domain_sensitivity_conditionals() -> None:
    renderer = PromptRenderer()
    profile = PromptProfileConfig(
        system_template=(
            "System {% if sensitivity_is_high_risk %}{{ sensitivity_domain }} :: "
            "{{ sensitivity_guidance }}{% else %}neutral{% endif %}"
        ),
        user_template=(
            "User {% if sensitivity_is_high_risk %}{{ sensitivity_review_note }}{% else %}plain{% endif %}"
        ),
    )

    sensitivity = build_domain_sensitivity(
        title="FDA clears updated vaccine rollout",
        summary="Public health officials shared a nationwide vaccine update.",
        tags=("health", "vaccine"),
        topic="Health policy updates",
    )
    rendered = renderer.render(
        profile,
        context={
            "sensitivity_domain": sensitivity.domain,
            "sensitivity_is_high_risk": sensitivity.is_high_risk,
            "sensitivity_guidance": sensitivity.prompt_guidance,
            "sensitivity_review_note": sensitivity.review_note,
        },
    )

    assert rendered.system_prompt.startswith("System health :: Avoid medical advice")
    assert "Health coverage should stay attributed" in rendered.user_prompt


def test_build_domain_sensitivity_returns_neutral_signal_for_low_risk_topic() -> None:
    sensitivity = build_domain_sensitivity(
        title="New AI workflow shortcuts for small teams",
        summary="A practical guide for operators.",
        tags=("ai", "automation"),
        topic="AI tools and workflows",
    )

    assert sensitivity.is_high_risk is False
    assert sensitivity.domain is None
    assert sensitivity.matched_terms == ()
    assert sensitivity.prompt_guidance is None


@pytest.mark.parametrize(
    ("title", "summary", "tags", "expected_domain", "expected_note"),
    [
        (
            "Court ruling changes election campaign rules",
            "Judges issued a new ruling after a legal challenge.",
            ("law",),
            "politics",
            "Politics coverage should stay sourced",
        ),
        (
            "Defense ministry reports a new missile launch",
            "Officials said national security agencies are reviewing the incident.",
            ("security",),
            "security",
            "Security coverage should verify attribution",
        ),
        (
            "Prosecutors open investigation into public contract",
            "The case remains under review after police submitted charges.",
            ("legal",),
            "legal",
            "Legal coverage should preserve alleged",
        ),
        (
            "Earthquake prompts emergency evacuation",
            "Authorities said rescue work is continuing after the disaster.",
            ("disaster",),
            "disaster",
            "Disaster coverage should stay restrained",
        ),
        (
            "Foreign ministry announces bilateral summit",
            "Officials described the talks as a diplomatic step.",
            ("diplomacy",),
            "diplomacy",
            "Diplomacy coverage should distinguish official statements",
        ),
    ],
)
def test_build_domain_sensitivity_covers_country_news_high_risk_domains(
    title: str,
    summary: str,
    tags: tuple[str, ...],
    expected_domain: str,
    expected_note: str,
) -> None:
    sensitivity = build_domain_sensitivity(
        title=title,
        summary=summary,
        tags=tags,
        topic="Korea news for global readers",
    )

    assert sensitivity.is_high_risk is True
    assert sensitivity.domain == expected_domain
    assert sensitivity.matched_terms
    assert sensitivity.review_note is not None
    assert expected_note in sensitivity.review_note
