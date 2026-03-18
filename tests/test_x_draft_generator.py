"""Tests for X draft generation services and fake provider behavior."""

from __future__ import annotations

import pytest

from app.config import AccountConfig, PromptProfileConfig
from app.connectors.llm import DraftGenerationRequest, FakeLLMProvider
from app.services import DraftGenerationError, XDraftGenerator
from app.storage import ArticleEnrichment, ContentBrief, SourceItem


def test_fake_llm_provider_is_deterministic_and_respects_request_constraints() -> None:
    provider = FakeLLMProvider()
    request = DraftGenerationRequest(
        channel="x",
        system_prompt="system",
        user_prompt="user",
        landing_url="https://gilgop.cloud/ai-tools",
        max_chars=120,
        variant_count=3,
        title="Useful AI workflow patterns",
        key_points=("Useful AI workflow patterns", "Tight review loops", "Better scheduling"),
    )

    first = provider.generate_variants(request)
    second = provider.generate_variants(request)

    assert first == second
    assert len(first) == 3
    assert all(request.landing_url in variant for variant in first)
    assert all(len(variant) <= request.max_chars for variant in first)


def test_fake_llm_provider_output_changes_when_prompts_change() -> None:
    provider = FakeLLMProvider()
    left = DraftGenerationRequest(
        channel="x",
        system_prompt="Keep posts practical for founders and operators.",
        user_prompt="Write about useful AI workflow patterns.",
        landing_url="https://gilgop.cloud/ai-tools",
        max_chars=140,
        variant_count=2,
        title="Useful AI workflow patterns",
        key_points=("Useful AI workflow patterns", "Tight review loops"),
    )
    right = DraftGenerationRequest(
        channel="x",
        system_prompt="Keep posts analytical for investors and market watchers.",
        user_prompt="Write about useful AI workflow patterns.",
        landing_url="https://gilgop.cloud/ai-tools",
        max_chars=140,
        variant_count=2,
        title="Useful AI workflow patterns",
        key_points=("Useful AI workflow patterns", "Tight review loops"),
    )

    assert provider.generate_variants(left) != provider.generate_variants(right)


def test_fake_llm_provider_uses_guide_cta_for_guide_landings() -> None:
    provider = FakeLLMProvider()
    request = DraftGenerationRequest(
        channel="x",
        system_prompt="Keep posts practical for workflow operators.",
        user_prompt="Write about useful AI workflow patterns and make the click feel like a guide.",
        landing_url="https://odtoolbase.com/guides/ai-agent-workflows-small-teams",
        max_chars=200,
        variant_count=3,
        title="Useful AI workflow patterns",
        key_points=("Useful AI workflow patterns", "Tight review loops", "Better scheduling"),
    )

    variants = provider.generate_variants(request)

    assert "Try this workflow:" in variants[0]
    assert "See the framework:" in variants[1]
    assert "Open the guide:" in variants[2]


def test_x_draft_generator_renders_prompt_context_before_calling_provider() -> None:
    provider = _CapturingProvider(
        (
            "First X draft https://gilgop.cloud/ai-tools",
            "Second X draft https://gilgop.cloud/ai-tools",
        )
    )
    generator = XDraftGenerator(provider)

    variants = generator.generate(
        content_brief=_build_content_brief(),
        account_key="ai_tools_daily",
        account=_build_account_config(max_chars=120),
        prompt_profile=PromptProfileConfig(
            system_template="System for {{ account_key }} on {{ channel }} via {{ source_name }}",
            user_template="Write about {{ title }} with {{ landing_url }} using {{ source_url }}",
        ),
        variant_count=2,
    )

    assert variants == (
        "First X draft https://gilgop.cloud/ai-tools",
        "Second X draft https://gilgop.cloud/ai-tools",
    )
    assert provider.request is not None
    assert "System for ai_tools_daily on x via Finance Feed" in provider.request.system_prompt
    assert "Write about Useful AI workflow patterns with https://gilgop.cloud/ai-tools using https://example.com/articles/1" in provider.request.user_prompt
    assert "Return exactly 2 distinct variants." in provider.request.system_prompt
    assert "Do not give investment advice" in provider.request.system_prompt
    assert "Avoid language that sounds like financial advice." in provider.request.user_prompt
    assert provider.request.max_chars == 120


@pytest.mark.parametrize(
    ("variants", "message"),
    [
        (
            (
                "Duplicate draft https://gilgop.cloud/ai-tools",
                "Duplicate   draft https://gilgop.cloud/ai-tools",
            ),
            "duplicates an earlier variant",
        ),
        (
            (
                "Missing landing URL",
                "Second draft https://gilgop.cloud/ai-tools",
            ),
            "missing the landing URL",
        ),
        (
            (
                "This draft has too many words to fit into a very small limit https://gilgop.cloud/ai-tools",
                "Second draft https://gilgop.cloud/ai-tools",
            ),
            "exceeds max_chars",
        ),
        (
            ("Only one draft https://gilgop.cloud/ai-tools",),
            "expected 2",
        ),
    ],
)
def test_x_draft_generator_rejects_invalid_provider_output(
    variants: tuple[str, ...],
    message: str,
) -> None:
    generator = XDraftGenerator(_CapturingProvider(variants))

    with pytest.raises(DraftGenerationError, match=message):
        generator.generate(
            content_brief=_build_content_brief(),
            account_key="ai_tools_daily",
            account=_build_account_config(max_chars=60),
            prompt_profile=PromptProfileConfig(
                system_template="System {{ account_key }}",
                user_template="User {{ title }} {{ landing_url }}",
            ),
            variant_count=2,
        )


class _CapturingProvider:
    def __init__(self, variants: tuple[str, ...]) -> None:
        self._variants = variants
        self.request: DraftGenerationRequest | None = None

    def generate_variants(self, request: DraftGenerationRequest) -> tuple[str, ...]:
        self.request = request
        return self._variants


def _build_account_config(*, max_chars: int) -> AccountConfig:
    return AccountConfig(
        topic="AI tools and workflows",
        source_sets=("ai_tools_primary",),
        prompt_profile="ai_tools_default",
        landing={"fallback_url": "https://gilgop.cloud/ai-tools", "rules": []},
        channels={
            "x": {
                "schedule": {"cron": "0 9 * * *"},
                "render": {"max_chars": max_chars},
            }
        },
    )


def _build_content_brief() -> ContentBrief:
    source_item = SourceItem(
        id=1,
        source_key="finance_rss",
        external_id="entry-1",
        source_url="https://example.com/articles/1",
        title="Useful AI workflow patterns",
        summary="A concise guide for operators.",
    )
    source_item.article_enrichment = ArticleEnrichment(
        source_item_id=1,
        source_name="Finance Feed",
        article_url="https://example.com/articles/1",
        regenerated_summary="A concise guide for operators.",
    )
    return ContentBrief(
        source_item_id=1,
        source_item=source_item,
        account_key="ai_tools_daily",
        title="Useful AI workflow patterns",
        summary="A concise guide for operators.",
        key_points=[
            "Useful AI workflow patterns",
            "Tight review loops",
            "Better scheduling",
        ],
        landing_url="https://gilgop.cloud/ai-tools",
        tags=["ai", "automation"],
        angle="practical_how_to",
        language="en",
    )
