"""Tests for deterministic content brief building."""

from __future__ import annotations

from dataclasses import asdict

from app.config import AccountConfig
from app.domain import AccountMatchCandidate, LandingDecision
from app.services import ContentBriefBuilder
from app.storage import SourceItem


def test_builder_extracts_key_points_in_priority_order_and_caps_at_three() -> None:
    builder = ContentBriefBuilder()

    brief = builder.build(
        source_item=_build_source_item(
            title="How to automate content review",
            summary="First supporting point. Second supporting point! Third supporting point?",
            raw_payload={"tags": ["ai"]},
        ),
        account_id="ai_tools_daily",
        account=_build_account(),
        match_candidate=AccountMatchCandidate(
            account_key="ai_tools_daily",
            score=21,
            eligible=True,
            source_tag_hits=("ai",),
            topic_keyword_hits=("automation",),
            include_keyword_hits=("automation",),
        ),
        landing_decision=LandingDecision(
            landing_url="https://gilgop.cloud/ai-tools",
            used_fallback=True,
        ),
    )

    assert brief.key_points == (
        "How to automate content review",
        "First supporting point",
        "Second supporting point",
    )


def test_builder_prefers_source_tags_over_match_evidence() -> None:
    builder = ContentBriefBuilder()

    brief = builder.build(
        source_item=_build_source_item(
            raw_payload={"tags": ["AI", "Automation", "AI"]},
        ),
        account_id="ai_tools_daily",
        account=_build_account(),
        match_candidate=AccountMatchCandidate(
            account_key="ai_tools_daily",
            score=21,
            eligible=True,
            source_tag_hits=("agents",),
            topic_keyword_hits=("workflows",),
            include_keyword_hits=("openai",),
        ),
        landing_decision=LandingDecision(
            landing_url="https://gilgop.cloud/ai-tools",
            used_fallback=False,
        ),
    )

    assert brief.tags == ("ai", "automation")


def test_builder_uses_match_evidence_tags_when_source_tags_are_missing() -> None:
    builder = ContentBriefBuilder()

    brief = builder.build(
        source_item=_build_source_item(raw_payload={}),
        account_id="ai_tools_daily",
        account=_build_account(),
        match_candidate=AccountMatchCandidate(
            account_key="ai_tools_daily",
            score=21,
            eligible=True,
            source_tag_hits=("automation", "agents"),
            topic_keyword_hits=("automation", "ops"),
            include_keyword_hits=("automation", "playbooks", "openai"),
        ),
        landing_decision=LandingDecision(
            landing_url="https://gilgop.cloud/ai-tools",
            used_fallback=True,
        ),
    )

    assert brief.tags == (
        "automation",
        "agents",
        "ops",
        "playbooks",
        "openai",
    )


def test_builder_assigns_expected_angle_labels() -> None:
    builder = ContentBriefBuilder()

    practical = builder.build(
        source_item=_build_source_item(
            title="Checklist for AI content QA",
            summary="A practical tutorial for review teams.",
        ),
        account_id="ai_tools_daily",
        account=_build_account(),
        match_candidate=_build_match_candidate(),
        landing_decision=_build_landing_decision(),
    )
    product = builder.build(
        source_item=_build_source_item(
            title="New agent release for support teams",
            summary="The launch adds routing automation.",
        ),
        account_id="ai_tools_daily",
        account=_build_account(),
        match_candidate=_build_match_candidate(),
        landing_decision=_build_landing_decision(),
    )
    trend = builder.build(
        source_item=_build_source_item(
            title="2026 benchmark report for AI agents",
            summary="Fresh survey data across SaaS teams.",
        ),
        account_id="ai_tools_daily",
        account=_build_account(),
        match_candidate=_build_match_candidate(),
        landing_decision=_build_landing_decision(),
    )
    takeaway = builder.build(
        source_item=_build_source_item(
            title="AI teams refine editorial operations",
            summary="Operators share lessons from niche accounts.",
        ),
        account_id="ai_tools_daily",
        account=_build_account(),
        match_candidate=_build_match_candidate(),
        landing_decision=_build_landing_decision(),
    )

    assert practical.angle == "practical_how_to"
    assert product.angle == "product_update"
    assert trend.angle == "trend_insight"
    assert takeaway.angle == "topic_takeaway"


def test_builder_returns_channel_neutral_brief_shape() -> None:
    builder = ContentBriefBuilder()

    brief = builder.build(
        source_item=_build_source_item(),
        account_id="ai_tools_daily",
        account=_build_account(),
        match_candidate=_build_match_candidate(),
        landing_decision=_build_landing_decision(),
    )

    assert set(asdict(brief)) == {
        "account_id",
        "source_item_id",
        "source_title",
        "source_summary",
        "key_points",
        "tags",
        "angle",
        "landing_url",
        "language",
    }


def _build_source_item(
    *,
    title: str = "AI agent improves review workflows",
    summary: str | None = "A focused update for operators.",
    raw_payload: dict | None = None,
) -> SourceItem:
    return SourceItem(
        id=1,
        source_key="ai_tools_rss",
        external_id="entry-1",
        source_url="https://example.com/posts/1",
        title=title,
        summary=summary,
        raw_payload=raw_payload or {},
    )


def _build_account() -> AccountConfig:
    return AccountConfig.model_validate(
        {
            "topic": "AI tools and workflows",
            "source_sets": ["ai_tools_primary"],
            "prompt_profile": "ai_tools_default",
            "landing": {
                "fallback_url": "https://gilgop.cloud/ai-tools",
                "rules": [],
            },
            "channels": {
                "x": {
                    "schedule": {"cron": "0 9 * * *"},
                    "render": {"max_chars": 280},
                }
            },
        }
    )


def _build_match_candidate() -> AccountMatchCandidate:
    return AccountMatchCandidate(
        account_key="ai_tools_daily",
        score=21,
        eligible=True,
        source_tag_hits=("ai",),
        topic_keyword_hits=("automation",),
        include_keyword_hits=("agents",),
    )


def _build_landing_decision() -> LandingDecision:
    return LandingDecision(
        landing_url="https://gilgop.cloud/ai-tools",
        used_fallback=False,
        matched_rule_index=0,
        matched_tag_hits=("ai",),
    )
