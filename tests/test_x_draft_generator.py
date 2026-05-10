"""Tests for X draft generation services and fake provider behavior."""

from __future__ import annotations

import pytest

from app.config import AccountConfig, PromptProfileConfig
from app.connectors.llm import DraftGenerationRequest, FakeLLMProvider
from app.services import DraftGenerationError, XDraftGenerator
from app.storage import ArticleEnrichment, ContentBrief, SourceItem, SourcePolicyMode


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


def test_fake_llm_provider_distinguishes_linkedin_and_threads_structured_tone() -> None:
    provider = FakeLLMProvider()
    linkedin_request = DraftGenerationRequest(
        channel="linkedin",
        system_prompt="Write for operators, founders, investors, and functional leaders.",
        user_prompt="Keep the framing decision-useful and B2B.",
        landing_url="https://example.com/articles/1",
        max_chars=3000,
        variant_count=2,
        title="Useful AI workflow patterns",
        key_points=("Useful AI workflow patterns", "Tight review loops", "Better scheduling"),
    )
    threads_request = DraftGenerationRequest(
        channel="threads",
        system_prompt="Write for fast-scrolling social readers.",
        user_prompt="Keep the framing social-first and worth sharing.",
        landing_url="https://example.com/articles/1",
        max_chars=10000,
        variant_count=2,
        title="Useful AI workflow patterns",
        key_points=("Useful AI workflow patterns", "Tight review loops", "Better scheduling"),
    )

    linkedin_variants = provider.generate_variants(linkedin_request)
    threads_variants = provider.generate_variants(threads_request)

    assert "business and operating context" in linkedin_variants[0]
    assert "decision-useful signal for operators and business readers" in linkedin_variants[0]
    assert "Why it may spread now" in threads_variants[0]
    assert "easy to share without losing the factual core" in threads_variants[0]


def test_fake_llm_provider_generates_ghost_longform_article_shape() -> None:
    provider = FakeLLMProvider()
    request = DraftGenerationRequest(
        channel="ghost",
        system_prompt="Write reviewable long-form country news.",
        user_prompt="Keep source trail visible for Ghost handoff.",
        landing_url="https://example.com/articles/1",
        max_chars=12000,
        variant_count=2,
        title="Useful AI workflow patterns",
        key_points=("Useful AI workflow patterns", "Tight review loops", "Better scheduling"),
    )

    variants = provider.generate_variants(request)

    assert len(variants) == 2
    assert variants[0].startswith("# Useful AI workflow patterns")
    assert "\n## What happened\n" in variants[0]
    assert "\n## Sources\n- Original report: https://example.com/articles/1" in variants[0]
    assert variants[0] != variants[1]


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
            "First X draft https://example.com/articles/1",
            "Second X draft https://example.com/articles/1",
        )
    )
    generator = XDraftGenerator(provider)

    variants = generator.generate(
        content_brief=_build_content_brief(require_attribution=True),
        account_key="ai_tools_daily",
        account=_build_account_config(max_chars=120),
        prompt_profile=PromptProfileConfig(
            system_template=(
                "System for {{ account_key }} on {{ channel }} via {{ source_name }} "
                "{{ policy_mode }} {% if require_attribution %}required{% else %}optional{% endif %}"
            ),
            user_template=(
                "Write about {{ title }} with {{ landing_url }} using {{ source_url }} "
                "and {{ article_summary }}"
            ),
        ),
        variant_count=2,
    )

    assert variants == (
        "First X draft Source: Finance Feed https://example.com/articles/1",
        "Second X draft Source: Finance Feed https://example.com/articles/1",
    )
    assert provider.request is not None
    assert (
        "System for ai_tools_daily on x via Finance Feed restricted required"
        in provider.request.system_prompt
    )
    assert (
        "Write about Useful AI workflow patterns with https://example.com/articles/1 "
        "using https://example.com/articles/1 and A concise guide for operators."
        in provider.request.user_prompt
    )
    assert "Return exactly 2 distinct variants." in provider.request.system_prompt
    assert "Do not give investment advice" in provider.request.system_prompt
    assert "Avoid language that sounds like financial advice." in provider.request.user_prompt
    assert provider.request.max_chars == 120


def test_x_draft_generator_adds_required_source_attribution_to_x_variants() -> None:
    provider = _CapturingProvider(
        (
            "First X draft https://example.com/articles/1",
            "Second X draft https://example.com/articles/1",
        )
    )
    generator = XDraftGenerator(provider)

    variants = generator.generate(
        content_brief=_build_content_brief(require_attribution=True),
        account_key="ai_tools_daily",
        account=_build_account_config(max_chars=120),
        prompt_profile=PromptProfileConfig(
            system_template="System {{ account_key }}",
            user_template="User {{ title }} {{ landing_url }}",
        ),
        variant_count=2,
    )

    assert variants == (
        "First X draft Source: Finance Feed https://example.com/articles/1",
        "Second X draft Source: Finance Feed https://example.com/articles/1",
    )
    assert all(variant.count("https://example.com/articles/1") == 1 for variant in variants)
    assert all(len(variant) <= 120 for variant in variants)


def test_x_draft_generator_deduplicates_existing_attribution_in_short_x_variants() -> None:
    provider = _CapturingProvider(
        (
            "First X draft Source: Finance Feed. The update is Source: Finance Feed https://example.com/articles/1",
            "Second X draft, per Finance Feed. https://example.com/articles/1",
        )
    )
    generator = XDraftGenerator(provider)

    variants = generator.generate(
        content_brief=_build_content_brief(require_attribution=True),
        account_key="ai_tools_daily",
        account=_build_account_config(max_chars=140),
        prompt_profile=PromptProfileConfig(
            system_template="System {{ account_key }}",
            user_template="User {{ title }} {{ landing_url }}",
        ),
        variant_count=2,
    )

    assert variants == (
        "First X draft Source: Finance Feed https://example.com/articles/1",
        "Second X draft Source: Finance Feed https://example.com/articles/1",
    )
    assert all(variant.count("Source: Finance Feed") == 1 for variant in variants)
    assert all(variant.count("https://example.com/articles/1") == 1 for variant in variants)
    assert all(len(variant) <= 140 for variant in variants)


def test_x_draft_generator_preserves_required_attribution_when_shortening_x_variants() -> None:
    long_context = " ".join(["Korea policy update for global readers"] * 8)
    provider = _CapturingProvider(
        (
            f"{long_context} https://example.com/articles/1",
            f"Second angle: {long_context} https://example.com/articles/1",
        )
    )
    generator = XDraftGenerator(provider)

    variants = generator.generate(
        content_brief=_build_content_brief(require_attribution=True),
        account_key="ai_tools_daily",
        account=_build_account_config(max_chars=110),
        prompt_profile=PromptProfileConfig(
            system_template="System {{ account_key }}",
            user_template="User {{ title }} {{ landing_url }}",
        ),
        variant_count=2,
    )

    assert len(variants) == 2
    assert all("Source: Finance Feed" in variant for variant in variants)
    assert all(variant.count("https://example.com/articles/1") == 1 for variant in variants)
    assert all(variant.endswith("https://example.com/articles/1") for variant in variants)
    assert all(len(variant) <= 110 for variant in variants)


def test_x_draft_generator_deduplicates_existing_attribution_when_shortening_x_variants() -> None:
    long_context = " ".join(["Japan wage policy update for global readers"] * 8)
    provider = _CapturingProvider(
        (
            f"According to Source: Finance Feed, {long_context} https://example.com/articles/1",
            f"Per Finance Feed, second angle: {long_context} https://example.com/articles/1",
        )
    )
    generator = XDraftGenerator(provider)

    variants = generator.generate(
        content_brief=_build_content_brief(require_attribution=True),
        account_key="ai_tools_daily",
        account=_build_account_config(max_chars=120),
        prompt_profile=PromptProfileConfig(
            system_template="System {{ account_key }}",
            user_template="User {{ title }} {{ landing_url }}",
        ),
        variant_count=2,
    )

    assert all(variant.count("Source: Finance Feed") == 1 for variant in variants)
    assert all(variant.count("https://example.com/articles/1") == 1 for variant in variants)
    assert all(len(variant) <= 120 for variant in variants)


def test_x_draft_generator_includes_domain_sensitivity_context_for_high_risk_topics() -> None:
    provider = _CapturingProvider(
        (
            "First health draft https://example.com/articles/1",
            "Second health draft https://example.com/articles/1",
        )
    )
    generator = XDraftGenerator(provider)

    generator.generate(
        content_brief=_build_content_brief(
            title="FDA clears updated vaccine rollout",
            summary="Public health officials shared a vaccine rollout update.",
            landing_url="https://gilgop.cloud/health",
            tags=("health", "vaccine"),
        ),
        account_key="public_health_daily",
        account=_build_account_config(max_chars=140, topic="Public health updates"),
        prompt_profile=PromptProfileConfig(
            system_template=(
                "System {{ sensitivity_domain }} :: "
                "{% if sensitivity_is_high_risk %}{{ sensitivity_guidance }}{% endif %}"
            ),
            user_template=(
                "User {{ title }} :: "
                "{% if sensitivity_is_high_risk %}{{ sensitivity_review_note }}{% endif %} :: "
                "{{ landing_url }}"
            ),
        ),
        variant_count=2,
    )

    assert provider.request is not None
    assert "System health ::" in provider.request.system_prompt
    assert "Avoid medical advice" in provider.request.system_prompt
    assert "Health coverage should stay attributed" in provider.request.user_prompt


def test_x_draft_generator_preserves_multiline_structure_for_linkedin_channel() -> None:
    provider = _CapturingProvider(
        (
            "1. One-line summary\nA professional summary.\n2. Key points\n- First point\n- Second point\n- Third point\n3. Keywords\nAI, Workflow\n4. Background/Context\nContext line.\n5. Forward impact\nImpact line.\n6. Insight\nInsight line.\n7. One-line conclusion\nConclusion line.\n8. URL\nhttps://example.com/articles/1",
            "1. One-line summary\nA second professional summary.\n2. Key points\n- First point\n- Second point\n- Third point\n3. Keywords\nAI, Workflow\n4. Background/Context\nContext line.\n5. Forward impact\nImpact line.\n6. Insight\nInsight line.\n7. One-line conclusion\nConclusion line.\n8. URL\nhttps://example.com/articles/1",
        )
    )
    generator = XDraftGenerator(provider)

    variants = generator.generate(
        content_brief=_build_content_brief(),
        account_key="ai_tools_daily",
        account=_build_account_config(max_chars=3000, channels=("x", "linkedin")),
        prompt_profile=PromptProfileConfig(
            system_template="System {{ account_key }} for {{ channel }}",
            user_template="User {{ title }} {{ landing_url }}",
        ),
        variant_count=2,
        channel="linkedin",
    )

    assert variants[0].startswith("1. One-line summary\n")
    assert "\n2. Key points\n- First point" in variants[0]
    assert variants[0].endswith("8. URL\nhttps://example.com/articles/1")
    assert provider.request is not None
    assert provider.request.channel == "linkedin"
    assert "1. One-line summary" in provider.request.system_prompt


def test_x_draft_generator_preserves_ghost_longform_structure_and_adds_source_attribution() -> None:
    provider = _CapturingProvider(
        (
            "# Useful AI workflow patterns\n\n## What happened\nDraft one.\n\n## Sources\n- https://example.com/articles/1",
            "# Useful AI workflow patterns\n\n## What happened\nDraft two.\n\n## Sources\n- https://example.com/articles/1",
        )
    )
    generator = XDraftGenerator(provider)

    variants = generator.generate(
        content_brief=_build_content_brief(require_attribution=True),
        account_key="ai_tools_daily",
        account=_build_account_config(max_chars=12000, channels=("ghost",)),
        prompt_profile=PromptProfileConfig(
            system_template="System {{ account_key }} for {{ channel }}",
            user_template="User {{ title }} {{ landing_url }}",
        ),
        variant_count=2,
        channel="ghost",
    )

    assert variants[0].startswith("# Useful AI workflow patterns\n")
    assert "\n## Sources\n- https://example.com/articles/1" in variants[0]
    assert "\nSource: Finance Feed" in variants[0]
    assert provider.request is not None
    assert provider.request.channel == "ghost"
    assert "article drafts, not social teasers" in provider.request.system_prompt


@pytest.mark.parametrize(
    ("channel", "system_phrase", "user_phrase"),
    [
        (
            "linkedin",
            "operators, functional leaders, founders, investors, and other B2B decision-makers",
            "business impact, strategic context, execution risk, market relevance, or policy significance",
        ),
        (
            "threads",
            "broad social readers scanning quickly for timely, worth-sharing updates",
            "why the update is timely, surprising, conversation-worthy, or useful to pass along right now",
        ),
    ],
)
def test_x_draft_generator_exposes_channel_style_context_to_prompt_templates(
    channel: str,
    system_phrase: str,
    user_phrase: str,
) -> None:
    provider = _CapturingProvider(
        (
            "1. One-line summary\nSummary line.\n2. Key points\n- First point\n- Second point\n- Third point\n3. Keywords\nAI, Workflow\n4. Background/Context\nContext line.\n5. Forward impact\nImpact line.\n6. Insight\nInsight line.\n7. One-line conclusion\nConclusion line.\n8. URL\nhttps://example.com/articles/1",
            "1. One-line summary\nAnother summary line.\n2. Key points\n- First point\n- Second point\n- Third point\n3. Keywords\nAI, Workflow\n4. Background/Context\nContext line.\n5. Forward impact\nImpact line.\n6. Insight\nInsight line.\n7. One-line conclusion\nConclusion line.\n8. URL\nhttps://example.com/articles/1",
        )
    )
    generator = XDraftGenerator(provider)

    generator.generate(
        content_brief=_build_content_brief(),
        account_key="ai_tools_daily",
        account=_build_account_config(
            max_chars=3000 if channel == "linkedin" else 10000,
            channels=(channel,),
        ),
        prompt_profile=PromptProfileConfig(
            system_template="Audience {{ channel_audience }} / Voice {{ channel_voice }} / Goal {{ channel_editorial_goal }}",
            user_template="Reader {{ channel_reader_focus }} / Implications {{ channel_implication_focus }}",
        ),
        variant_count=2,
        channel=channel,
    )

    assert provider.request is not None
    assert system_phrase in provider.request.system_prompt
    assert user_phrase in provider.request.user_prompt


@pytest.mark.parametrize(
    ("variants", "message", "max_chars"),
    [
        (
            (
                "Duplicate draft https://example.com/articles/1",
                "Duplicate   draft https://example.com/articles/1",
            ),
            "duplicates an earlier variant",
            60,
        ),
        (
            (
                "Missing landing URL",
                "Second draft https://example.com/articles/1",
            ),
            "missing the landing URL",
            60,
        ),
        (
            (
                "This draft has too many words to fit into a very small limit https://example.com/articles/1",
                "Second draft https://example.com/articles/1",
            ),
            "exceeds max_chars",
            20,
        ),
        (
            ("Only one draft https://example.com/articles/1",),
            "expected 2",
            60,
        ),
    ],
)
def test_x_draft_generator_rejects_invalid_provider_output(
    variants: tuple[str, ...],
    message: str,
    max_chars: int,
) -> None:
    generator = XDraftGenerator(_CapturingProvider(variants))

    with pytest.raises(DraftGenerationError, match=message):
        generator.generate(
            content_brief=_build_content_brief(),
            account_key="ai_tools_daily",
            account=_build_account_config(max_chars=max_chars),
            prompt_profile=PromptProfileConfig(
                system_template="System {{ account_key }}",
                user_template="User {{ title }} {{ landing_url }}",
            ),
            variant_count=2,
        )


def test_x_draft_generator_shortens_overlong_variants_that_include_the_required_url() -> None:
    generator = XDraftGenerator(
        _CapturingProvider(
            (
                (
                    "This draft has too many words to fit into a very small limit but still points "
                    "to the right article https://example.com/articles/1 and leaves extra trailing copy"
                ),
                (
                    "Second draft keeps the article context intact while using more words than the "
                    "channel limit allows https://example.com/articles/1 with extra overflow"
                ),
            )
        )
    )

    variants = generator.generate(
        content_brief=_build_content_brief(),
        account_key="ai_tools_daily",
        account=_build_account_config(max_chars=90),
        prompt_profile=PromptProfileConfig(
            system_template="System {{ account_key }}",
            user_template="User {{ title }} {{ landing_url }}",
        ),
        variant_count=2,
    )

    assert len(variants) == 2
    assert all(len(variant) <= 90 for variant in variants)
    assert all(variant.count("https://example.com/articles/1") == 1 for variant in variants)
    assert all(variant.endswith("https://example.com/articles/1") for variant in variants)


def test_x_draft_generator_shortens_overlong_linkedin_variants_while_preserving_structure() -> None:
    long_paragraph = " ".join(["Detailed context for operators and analysts."] * 40)
    provider = _CapturingProvider(
        (
            (
                "1. One-line summary\n"
                f"{long_paragraph}\n"
                "2. Key points\n"
                f"- {long_paragraph}\n"
                f"- {long_paragraph}\n"
                f"- {long_paragraph}\n"
                f"- {long_paragraph}\n"
                f"- {long_paragraph}\n"
                "3. Keywords\n"
                f"{long_paragraph}\n"
                "4. Background/Context\n"
                f"{long_paragraph}\n"
                "5. Forward impact\n"
                f"{long_paragraph}\n"
                "6. Insight\n"
                f"{long_paragraph}\n"
                "7. One-line conclusion\n"
                f"{long_paragraph}\n"
                "8. URL\n"
                "https://example.com/articles/1"
            ),
            (
                "1. One-line summary\n"
                f"Second {long_paragraph}\n"
                "2. Key points\n"
                f"- {long_paragraph}\n"
                f"- {long_paragraph}\n"
                f"- {long_paragraph}\n"
                "3. Keywords\n"
                f"{long_paragraph}\n"
                "4. Background/Context\n"
                f"{long_paragraph}\n"
                "5. Forward impact\n"
                f"{long_paragraph}\n"
                "6. Insight\n"
                f"{long_paragraph}\n"
                "7. One-line conclusion\n"
                f"{long_paragraph}\n"
                "8. URL\n"
                "https://example.com/articles/1"
            ),
        )
    )
    generator = XDraftGenerator(provider)

    variants = generator.generate(
        content_brief=_build_content_brief(),
        account_key="ai_tools_daily",
        account=_build_account_config(max_chars=3000, channels=("linkedin",)),
        prompt_profile=PromptProfileConfig(
            system_template="System {{ account_key }} for {{ channel }}",
            user_template="User {{ title }} {{ landing_url }}",
        ),
        variant_count=2,
        channel="linkedin",
    )

    assert len(variants) == 2
    assert all(len(variant) <= 3000 for variant in variants)
    assert all(variant.startswith("1. One-line summary\n") for variant in variants)
    assert all("\n2. Key points\n- " in variant for variant in variants)
    assert all(variant.endswith("8. URL\nhttps://example.com/articles/1") for variant in variants)


def test_x_draft_generator_restores_missing_url_for_structured_channels() -> None:
    provider = _CapturingProvider(
        (
            "1. One-line summary\nSummary line.\n2. Key points\n- First point\n- Second point\n- Third point\n3. Keywords\nAI, Workflow\n4. Background/Context\nContext line.\n5. Forward impact\nImpact line.\n6. Insight\nInsight line.\n7. One-line conclusion\nConclusion line.\n8. URL\n",
            "1. One-line summary\nAnother summary line.\n2. Key points\n- First point\n- Second point\n- Third point\n3. Keywords\nAI, Workflow\n4. Background/Context\nContext line.\n5. Forward impact\nImpact line.\n6. Insight\nInsight line.\n7. One-line conclusion\nConclusion line.\n8. URL\n",
        )
    )
    generator = XDraftGenerator(provider)

    variants = generator.generate(
        content_brief=_build_content_brief(),
        account_key="ai_tools_daily",
        account=_build_account_config(max_chars=3000, channels=("linkedin",)),
        prompt_profile=PromptProfileConfig(
            system_template="System {{ account_key }} for {{ channel }}",
            user_template="User {{ title }} {{ landing_url }}",
        ),
        variant_count=2,
        channel="linkedin",
    )

    assert all(variant.endswith("8. URL\nhttps://example.com/articles/1") for variant in variants)


def test_x_draft_generator_retries_structured_channels_after_validation_failure() -> None:
    long_paragraph = " ".join(["Detailed context for operators and analysts."] * 60)
    provider = _SequentialProvider(
        [
            (
                (
                    "1. One-line summary\n"
                    f"{long_paragraph}\n"
                    "2. Key points\n"
                    f"- {long_paragraph}\n"
                    f"- {long_paragraph}\n"
                    f"- {long_paragraph}\n"
                    "3. Keywords\n"
                    f"{long_paragraph}\n"
                    "4. Background/Context\n"
                    f"{long_paragraph}\n"
                    "5. Forward impact\n"
                    f"{long_paragraph}\n"
                    "6. Insight\n"
                    f"{long_paragraph}\n"
                    "7. One-line conclusion\n"
                    f"{long_paragraph}\n"
                    "8. URL\n"
                    "https://example.com/articles/1"
                ),
                (
                    "1. One-line summary\n"
                    f"{long_paragraph}\n"
                    "2. Key points\n"
                    f"- {long_paragraph}\n"
                    f"- {long_paragraph}\n"
                    f"- {long_paragraph}\n"
                    "3. Keywords\n"
                    f"{long_paragraph}\n"
                    "4. Background/Context\n"
                    f"{long_paragraph}\n"
                    "5. Forward impact\n"
                    f"{long_paragraph}\n"
                    "6. Insight\n"
                    f"{long_paragraph}\n"
                    "7. One-line conclusion\n"
                    f"{long_paragraph}\n"
                    "8. URL\n"
                    "https://example.com/articles/1"
                ),
            ),
            (
                "1. One-line summary\nShort summary.\n2. Key points\n- First point\n- Second point\n- Third point\n3. Keywords\nAI, Workflow\n4. Background/Context\nContext line.\n5. Forward impact\nImpact line.\n6. Insight\nInsight line.\n7. One-line conclusion\nConclusion line.\n8. URL\nhttps://example.com/articles/1",
                "1. One-line summary\nAnother short summary.\n2. Key points\n- First point\n- Second point\n- Third point\n3. Keywords\nAI, Workflow\n4. Background/Context\nContext line.\n5. Forward impact\nImpact line.\n6. Insight\nInsight line.\n7. One-line conclusion\nConclusion line.\n8. URL\nhttps://example.com/articles/1",
            ),
        ]
    )
    generator = XDraftGenerator(provider)

    variants = generator.generate(
        content_brief=_build_content_brief(),
        account_key="ai_tools_daily",
        account=_build_account_config(max_chars=3000, channels=("linkedin",)),
        prompt_profile=PromptProfileConfig(
            system_template="System {{ account_key }} for {{ channel }}",
            user_template="User {{ title }} {{ landing_url }}",
        ),
        variant_count=2,
        channel="linkedin",
    )

    assert len(variants) == 2
    assert provider.call_count == 2
    assert "Revision requirements:" in provider.requests[-1].system_prompt
    assert all(len(variant) <= 3000 for variant in variants)


def test_x_draft_generator_prefers_article_url_over_content_landing_url() -> None:
    provider = _CapturingProvider(
        (
            "First X draft https://example.com/articles/1",
            "Second X draft https://example.com/articles/1",
        )
    )
    generator = XDraftGenerator(provider)

    generator.generate(
        content_brief=_build_content_brief(landing_url="https://gilgop.cloud/ai-tools"),
        account_key="ai_tools_daily",
        account=_build_account_config(max_chars=120),
        prompt_profile=PromptProfileConfig(
            system_template="System {{ account_key }}",
            user_template="Use {{ landing_url }} not {{ content_landing_url }}",
        ),
        variant_count=2,
    )

    assert provider.request is not None
    assert "Use https://example.com/articles/1 not https://gilgop.cloud/ai-tools" in provider.request.user_prompt
    assert provider.request.landing_url == "https://example.com/articles/1"


class _CapturingProvider:
    def __init__(self, variants: tuple[str, ...]) -> None:
        self._variants = variants
        self.request: DraftGenerationRequest | None = None

    def generate_variants(self, request: DraftGenerationRequest) -> tuple[str, ...]:
        self.request = request
        return self._variants


class _SequentialProvider:
    def __init__(self, responses: list[tuple[str, ...]]) -> None:
        self._responses = responses
        self.call_count = 0
        self.requests: list[DraftGenerationRequest] = []

    def generate_variants(self, request: DraftGenerationRequest) -> tuple[str, ...]:
        self.requests.append(request)
        response = self._responses[min(self.call_count, len(self._responses) - 1)]
        self.call_count += 1
        return response


def _build_account_config(
    *,
    max_chars: int,
    topic: str = "AI tools and workflows",
    channels: tuple[str, ...] = ("x",),
) -> AccountConfig:
    return AccountConfig(
        topic=topic,
        source_sets=("ai_tools_primary",),
        prompt_profile="ai_tools_default",
        landing={"fallback_url": "https://gilgop.cloud/ai-tools", "rules": []},
        channels={
            channel: {
                "schedule": {"cron": "0 9 * * *"},
                "render": {"max_chars": max_chars},
            }
            for channel in channels
        },
    )

def _build_content_brief(
    *,
    title: str = "Useful AI workflow patterns",
    summary: str = "A concise guide for operators.",
    landing_url: str = "https://gilgop.cloud/ai-tools",
    tags: tuple[str, ...] = ("ai", "automation"),
    require_attribution: bool = False,
) -> ContentBrief:
    source_item = SourceItem(
        id=1,
        source_key="finance_rss",
        external_id="entry-1",
        source_url="https://example.com/articles/1",
        title=title,
        summary=summary,
        policy_mode=SourcePolicyMode.RESTRICTED,
        require_attribution=require_attribution,
    )
    source_item.article_enrichment = ArticleEnrichment(
        source_item_id=1,
        source_name="Finance Feed",
        article_url="https://example.com/articles/1",
        regenerated_summary=summary,
    )
    return ContentBrief(
        source_item_id=1,
        source_item=source_item,
        account_key="ai_tools_daily",
        title=title,
        summary=summary,
        key_points=[
            title,
            "Tight review loops",
            "Better scheduling",
        ],
        landing_url=landing_url,
        tags=list(tags),
        angle="practical_how_to",
        language="en",
    )
