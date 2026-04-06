"""Tests for prompt template rendering."""

from __future__ import annotations

import pytest

from app.config import PromptProfileConfig
from app.services import PromptRenderer, PromptRenderingError


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
