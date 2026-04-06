"""Tests for configuration loading and registry validation."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from app.config import (
    ConfigLoadError,
    ConfigReferenceError,
    ConfigRegistry,
    ConfigValidationError,
    GdeltSourceConfig,
    ManualCsvSourceConfig,
    RssSourceConfig,
    SitemapSourceConfig,
    load_sources_config,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_registry_loads_sample_config_directory() -> None:
    registry = ConfigRegistry.from_directory(PROJECT_ROOT / "config")

    ai_account = registry.get_account("ai_tools_daily")
    ai_channel = ai_account.channels["x"]
    seo_account = registry.get_account("seo_tools_daily")

    assert ai_account.topic == "AI workflows and guides"
    assert ai_account.prompt_profile == "ai_tools_default"
    assert list(registry.accounts) == ["ai_tools_daily", "seo_tools_daily"]
    assert str(ai_account.landing.fallback_url) == "https://odtoolbase.com/guides"
    assert str(ai_account.landing.rules[0].url) == (
        "https://odtoolbase.com/guides/ai-research-stack-content-pipelines"
    )
    assert str(ai_account.landing.rules[1].url) == (
        "https://odtoolbase.com/guides/ai-agent-workflows-small-teams"
    )
    assert ai_account.landing.validation.require_live_url is True
    assert tuple(str(prefix) for prefix in ai_account.landing.validation.allowed_url_prefixes) == (
        "https://odtoolbase.com/guides",
    )
    assert ai_account.matching.include_keywords == ("ai", "agent", "workflow", "automation", "guide")
    assert ai_account.matching.exclude_keywords == (
        "seo",
        "backlink",
        "search ranking",
        "earnings",
        "stock",
    )
    assert ai_account.matching.source_tags == ("ai", "automation", "workflow", "guide")
    assert ai_account.matching.strict_topic_guard is True
    assert ai_account.validation.profile == "standard"
    assert ai_channel.schedule.cron == "0 9 * * *"
    assert ai_channel.render.max_chars == 280
    assert ai_channel.validation.max_links == 1
    assert ai_channel.validation.banned_phrases == ()
    assert ai_channel.validation.recent_duplicate_window_days == 7
    assert ai_channel.publisher is not None
    assert ai_channel.publisher.credential_ref == "X_AI_TOOLS_DAILY_PUBLISHER_CREDENTIALS"

    assert seo_account.topic == "SEO tools and search optimization"
    assert seo_account.prompt_profile == "seo_tools_default"
    assert str(seo_account.landing.fallback_url) == "https://odtoolbase.com/tools"
    assert seo_account.landing.validation.require_live_url is True

    assert registry.get_prompt_profile("ai_tools_default").system_template.startswith(
        "You are the growth editor"
    )
    assert registry.get_prompt_profile("seo_tools_default").system_template.startswith(
        "You are the growth editor"
    )
    assert registry.get_prompt_profile("all_domain_general_news_summary").system_template.startswith(
        "You are the review-first editor"
    )
    assert registry.get_prompt_profile("all_domain_factual_x_post").system_template.startswith(
        "You are the review-first editor"
    )
    assert registry.get_prompt_profile(
        "all_domain_attribution_first_short_post"
    ).system_template.startswith("You are the attribution-first editor")
    assert registry.get_source_set("ai_tools_primary").sources == (
        "ai_tools_rss",
        "ai_tools_manual",
    )
    assert registry.get_source_set("seo_tools_primary").sources == (
        "seo_tools_rss",
        "seo_tools_manual",
    )


def test_registry_loads_all_domain_example_config_directory() -> None:
    registry = ConfigRegistry.from_directory(PROJECT_ROOT / "config/examples/all_domain_news")

    account = registry.get_account("all_domain_news_daily")
    channel = account.channels["x"]
    official_source = registry.get_source("official_updates_reusable")
    corporate_source = registry.get_source("corporate_ir_reusable")
    gdelt_source = registry.get_source("gdelt_latest_discovery")
    wikinews_source = registry.get_source("wikinews_attribution_friendly")

    assert account.topic == "All-domain latest news"
    assert account.prompt_profile == "all_domain_factual_x_post"
    assert list(account.source_sets) == ["all_domain_primary"]
    assert str(account.landing.fallback_url) == "https://newsroom.example.com/daily-brief"
    assert account.matching.include_keywords == ("policy", "launch", "update", "report", "statement")
    assert account.matching.exclude_keywords == ("coupon", "giveaway", "rumor")
    assert account.matching.source_tags == ("official", "newsroom", "wikinews")
    assert account.validation.profile == "standard"
    assert channel.validation.max_links == 1
    assert channel.validation.recent_duplicate_window_days == 2

    assert isinstance(official_source, RssSourceConfig)
    assert official_source.policy_mode == "reusable"
    assert official_source.require_attribution is True
    assert official_source.allow_full_text_fetch is True
    assert "government-style feed" in official_source.notes

    assert isinstance(corporate_source, SitemapSourceConfig)
    assert corporate_source.policy_mode == "reusable"
    assert corporate_source.require_attribution is True
    assert corporate_source.allow_llm_rewrite is True

    assert isinstance(gdelt_source, GdeltSourceConfig)
    assert gdelt_source.query == "domain:news"
    assert gdelt_source.policy_mode == "discovery_only"
    assert gdelt_source.allow_full_text_fetch is False
    assert gdelt_source.allow_llm_rewrite is False
    assert gdelt_source.require_attribution is True

    assert isinstance(wikinews_source, RssSourceConfig)
    assert wikinews_source.policy_mode == "reusable"
    assert wikinews_source.require_attribution is True
    assert wikinews_source.notes == "Sample Wikinews-style source with attribution-friendly defaults."

    assert registry.get_prompt_profile("all_domain_review_default").system_template.startswith(
        "You are the review-first editor"
    )
    assert registry.get_prompt_profile("all_domain_general_news_summary").system_template.startswith(
        "You are the review-first editor"
    )
    assert registry.get_prompt_profile("all_domain_factual_x_post").system_template.startswith(
        "You are the review-first editor"
    )
    assert registry.get_prompt_profile(
        "all_domain_attribution_first_short_post"
    ).system_template.startswith("You are the attribution-first editor")
    assert registry.get_source_set("public_reusable").sources == ("official_updates_reusable",)
    assert registry.get_source_set("corporate_reusable").sources == ("corporate_ir_reusable",)
    assert registry.get_source_set("attribution_friendly_reusable").sources == (
        "wikinews_attribution_friendly",
    )
    assert registry.get_source_set("all_domain_primary").sources == (
        "official_updates_reusable",
        "corporate_ir_reusable",
        "wikinews_attribution_friendly",
    )
    assert registry.get_source_set("discovery_only_monitoring").sources == (
        "gdelt_latest_discovery",
    )


def test_registry_is_deeply_immutable() -> None:
    registry = ConfigRegistry.from_directory(PROJECT_ROOT / "config")
    account = registry.get_account("ai_tools_daily")

    assert isinstance(account.source_sets, tuple)
    assert isinstance(account.landing.rules, tuple)

    with pytest.raises(AttributeError):
        account.source_sets.append("another_source_set")

    with pytest.raises(TypeError):
        account.channels["threads"] = account.channels["x"]


def test_validation_errors_include_file_name_and_field_path(tmp_path: Path) -> None:
    _write_valid_prompts_yaml(tmp_path)
    _write_valid_sources_yaml(tmp_path)
    _write_file(
        tmp_path / "accounts.yaml",
        """
        accounts:
          ai_tools_daily:
            topic: "AI tools and workflows"
            source_sets:
              - ai_tools_primary
            prompt_profile: ai_tools_default
            landing:
              fallback_url: https://gilgop.cloud/ai-tools
              rules: []
            channels:
              x:
                schedule:
                  cron: "0 9 * * *"
                render:
                  max_chars: 280
            unsupported_field: true
        """,
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        ConfigRegistry.from_directory(tmp_path)

    message = str(exc_info.value)
    assert "accounts.yaml" in message
    assert "accounts.ai_tools_daily.unsupported_field" in message


def test_registry_rejects_unknown_prompt_profile_reference(tmp_path: Path) -> None:
    _write_valid_prompts_yaml(tmp_path)
    _write_valid_sources_yaml(tmp_path)
    _write_file(
        tmp_path / "accounts.yaml",
        """
        accounts:
          ai_tools_daily:
            topic: "AI tools and workflows"
            source_sets:
              - ai_tools_primary
            prompt_profile: missing_profile
            landing:
              fallback_url: https://gilgop.cloud/ai-tools
              rules: []
            channels:
              x:
                schedule:
                  cron: "0 9 * * *"
                render:
                  max_chars: 280
        """,
    )

    with pytest.raises(ConfigReferenceError) as exc_info:
        ConfigRegistry.from_directory(tmp_path)

    message = str(exc_info.value)
    assert "accounts.yaml" in message
    assert "accounts.ai_tools_daily.prompt_profile" in message
    assert "missing_profile" in message


def test_registry_rejects_source_set_with_unknown_source(tmp_path: Path) -> None:
    _write_valid_prompts_yaml(tmp_path)
    _write_file(
        tmp_path / "accounts.yaml",
        """
        accounts:
          ai_tools_daily:
            topic: "AI tools and workflows"
            source_sets:
              - ai_tools_primary
            prompt_profile: ai_tools_default
            landing:
              fallback_url: https://gilgop.cloud/ai-tools
              rules: []
            channels:
              x:
                schedule:
                  cron: "0 9 * * *"
                render:
                  max_chars: 280
        """,
    )
    _write_file(
        tmp_path / "sources.yaml",
        """
        sources:
          ai_tools_rss:
            type: rss
            url: https://example.com/feed.xml

        source_sets:
          ai_tools_primary:
            sources:
              - missing_source
        """,
    )

    with pytest.raises(ConfigReferenceError) as exc_info:
        ConfigRegistry.from_directory(tmp_path)

    message = str(exc_info.value)
    assert "sources.yaml" in message
    assert "source_sets.ai_tools_primary.sources.0" in message
    assert "missing_source" in message


def test_manual_csv_source_variant_loads_successfully(tmp_path: Path) -> None:
    _write_valid_prompts_yaml(tmp_path)
    _write_file(
        tmp_path / "accounts.yaml",
        """
        accounts:
          ai_tools_daily:
            topic: "AI tools and workflows"
            source_sets:
              - ai_tools_manual
            prompt_profile: ai_tools_default
            landing:
              fallback_url: https://gilgop.cloud/ai-tools
              rules: []
            channels:
              x:
                schedule:
                  cron: "0 9 * * *"
                render:
                  max_chars: 280
        """,
    )
    _write_file(
        tmp_path / "sources.yaml",
        """
        sources:
          ai_tools_seed:
            type: manual_csv
            path: data/manual/ai_tools.csv

        source_sets:
          ai_tools_manual:
            sources:
              - ai_tools_seed
        """,
    )

    registry = ConfigRegistry.from_directory(tmp_path)
    source = registry.get_source("ai_tools_seed")

    assert isinstance(source, ManualCsvSourceConfig)
    assert source.path == (tmp_path / "data/manual/ai_tools.csv").resolve()


def test_gdelt_source_variant_loads_discovery_only_defaults(tmp_path: Path) -> None:
    _write_valid_prompts_yaml(tmp_path)
    _write_file(
        tmp_path / "accounts.yaml",
        """
        accounts:
          ai_tools_daily:
            topic: "AI tools and workflows"
            source_sets:
              - ai_tools_discovery
            prompt_profile: ai_tools_default
            landing:
              fallback_url: https://gilgop.cloud/ai-tools
              rules: []
            channels:
              x:
                schedule:
                  cron: "0 9 * * *"
                render:
                  max_chars: 280
        """,
    )
    _write_file(
        tmp_path / "sources.yaml",
        """
        sources:
          ai_tools_gdelt:
            type: gdelt
            query: "domain:news"

        source_sets:
          ai_tools_discovery:
            sources:
              - ai_tools_gdelt
        """,
    )

    registry = ConfigRegistry.from_directory(tmp_path)
    source = registry.get_source("ai_tools_gdelt")

    assert isinstance(source, GdeltSourceConfig)
    assert source.query == "domain:news"
    assert source.policy_mode == "discovery_only"
    assert source.allow_full_text_fetch is False
    assert source.allow_llm_rewrite is False
    assert source.require_attribution is True


def test_validation_config_loads_successfully(tmp_path: Path) -> None:
    _write_valid_prompts_yaml(tmp_path)
    _write_valid_sources_yaml(tmp_path)
    _write_file(
        tmp_path / "accounts.yaml",
        """
        accounts:
          finance_news_daily:
            topic: "Finance markets and investing"
            source_sets:
              - ai_tools_primary
            prompt_profile: ai_tools_default
            landing:
              fallback_url: https://gilgop.cloud/finance
              rules: []
            validation:
              profile: finance_strict
            channels:
              x:
                schedule:
                  cron: "0 9 * * *"
                render:
                  max_chars: 280
                validation:
                  max_links: 2
                  banned_phrases:
                    - "risk free"
                    - "guaranteed returns"
                  recent_duplicate_window_days: 14
        """,
    )

    registry = ConfigRegistry.from_directory(tmp_path)
    account = registry.get_account("finance_news_daily")
    channel = account.channels["x"]

    assert account.validation.profile == "finance_strict"
    assert channel.validation.max_links == 2
    assert channel.validation.banned_phrases == ("risk free", "guaranteed returns")
    assert channel.validation.recent_duplicate_window_days == 14


def test_sources_default_duplicate_window_days_to_thirty(tmp_path: Path) -> None:
    _write_valid_sources_yaml(tmp_path)
    sources_config = load_sources_config(tmp_path / "sources.yaml")
    source = sources_config.sources["ai_tools_rss"]

    assert isinstance(source, RssSourceConfig)
    assert source.policy_mode == "reusable"
    assert source.allow_full_text_fetch is True
    assert source.allow_llm_rewrite is True
    assert source.require_attribution is False
    assert source.notes is None
    assert source.duplicate_window_days == 30


def test_sources_load_policy_overrides_for_supported_variants(tmp_path: Path) -> None:
    _write_valid_prompts_yaml(tmp_path)
    _write_file(
        tmp_path / "accounts.yaml",
        """
        accounts:
          ai_tools_daily:
            topic: "AI tools and workflows"
            source_sets:
              - ai_tools_primary
            prompt_profile: ai_tools_default
            landing:
              fallback_url: https://gilgop.cloud/ai-tools
              rules: []
            channels:
              x:
                schedule:
                  cron: "0 9 * * *"
                render:
                  max_chars: 280
        """,
    )
    _write_file(
        tmp_path / "sources.yaml",
        """
        sources:
          ai_tools_rss:
            type: rss
            url: https://example.com/feed.xml
            policy_mode: discovery_only
            allow_full_text_fetch: false
            allow_llm_rewrite: false
            require_attribution: true
            notes: "Aggregator feed for discovery only"
          ai_tools_sitemap:
            type: sitemap
            url: https://example.com/sitemap.xml
            policy_mode: restricted
            require_attribution: true
          ai_tools_seed:
            type: manual_csv
            path: data/manual/ai_tools.csv
            policy_mode: reusable
            allow_full_text_fetch: true
            allow_llm_rewrite: true
            require_attribution: false
            notes: "Operator-curated reusable seeds"

        source_sets:
          ai_tools_primary:
            sources:
              - ai_tools_rss
              - ai_tools_sitemap
              - ai_tools_seed
        """,
    )

    registry = ConfigRegistry.from_directory(tmp_path)
    rss_source = registry.get_source("ai_tools_rss")
    sitemap_source = registry.get_source("ai_tools_sitemap")
    manual_source = registry.get_source("ai_tools_seed")

    assert isinstance(rss_source, RssSourceConfig)
    assert rss_source.policy_mode == "discovery_only"
    assert rss_source.allow_full_text_fetch is False
    assert rss_source.allow_llm_rewrite is False
    assert rss_source.require_attribution is True
    assert rss_source.notes == "Aggregator feed for discovery only"

    assert sitemap_source.policy_mode == "restricted"
    assert sitemap_source.allow_full_text_fetch is True
    assert sitemap_source.allow_llm_rewrite is True
    assert sitemap_source.require_attribution is True
    assert sitemap_source.notes is None

    assert isinstance(manual_source, ManualCsvSourceConfig)
    assert manual_source.policy_mode == "reusable"
    assert manual_source.allow_full_text_fetch is True
    assert manual_source.allow_llm_rewrite is True
    assert manual_source.require_attribution is False
    assert manual_source.notes == "Operator-curated reusable seeds"


def test_invalid_source_policy_mode_raises_validation_error(tmp_path: Path) -> None:
    _write_valid_prompts_yaml(tmp_path)
    _write_file(
        tmp_path / "accounts.yaml",
        """
        accounts:
          ai_tools_daily:
            topic: "AI tools and workflows"
            source_sets:
              - ai_tools_primary
            prompt_profile: ai_tools_default
            landing:
              fallback_url: https://gilgop.cloud/ai-tools
              rules: []
            channels:
              x:
                schedule:
                  cron: "0 9 * * *"
                render:
                  max_chars: 280
        """,
    )
    _write_file(
        tmp_path / "sources.yaml",
        """
        sources:
          ai_tools_rss:
            type: rss
            url: https://example.com/feed.xml
            policy_mode: "   "

        source_sets:
          ai_tools_primary:
            sources:
              - ai_tools_rss
        """,
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        ConfigRegistry.from_directory(tmp_path)

    message = str(exc_info.value)
    assert "sources.ai_tools_rss.rss.policy_mode" in message
    assert "must not be empty" in message


def test_negative_duplicate_window_days_raise_validation_error(tmp_path: Path) -> None:
    _write_valid_prompts_yaml(tmp_path)
    _write_file(
        tmp_path / "accounts.yaml",
        """
        accounts:
          ai_tools_daily:
            topic: "AI tools and workflows"
            source_sets:
              - ai_tools_primary
            prompt_profile: ai_tools_default
            landing:
              fallback_url: https://gilgop.cloud/ai-tools
              rules: []
            channels:
              x:
                schedule:
                  cron: "0 9 * * *"
                render:
                  max_chars: 280
        """,
    )
    _write_file(
        tmp_path / "sources.yaml",
        """
        sources:
          ai_tools_rss:
            type: rss
            url: https://example.com/feed.xml
            duplicate_window_days: -1

        source_sets:
          ai_tools_primary:
            sources:
              - ai_tools_rss
        """,
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        ConfigRegistry.from_directory(tmp_path)

    message = str(exc_info.value)
    assert "sources.ai_tools_rss.rss.duplicate_window_days" in message
    assert "greater than or equal to 0" in message


def test_invalid_validation_profile_raises_validation_error(tmp_path: Path) -> None:
    _write_valid_prompts_yaml(tmp_path)
    _write_valid_sources_yaml(tmp_path)
    _write_file(
        tmp_path / "accounts.yaml",
        """
        accounts:
          ai_tools_daily:
            topic: "AI tools and workflows"
            source_sets:
              - ai_tools_primary
            prompt_profile: ai_tools_default
            landing:
              fallback_url: https://gilgop.cloud/ai-tools
              rules: []
            validation:
              profile: unsupported
            channels:
              x:
                schedule:
                  cron: "0 9 * * *"
                render:
                  max_chars: 280
        """,
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        ConfigRegistry.from_directory(tmp_path)

    message = str(exc_info.value)
    assert "accounts.ai_tools_daily.validation.profile" in message
    assert "finance_strict" in message


def test_negative_validation_duplicate_window_days_raise_validation_error(tmp_path: Path) -> None:
    _write_valid_prompts_yaml(tmp_path)
    _write_valid_sources_yaml(tmp_path)
    _write_file(
        tmp_path / "accounts.yaml",
        """
        accounts:
          ai_tools_daily:
            topic: "AI tools and workflows"
            source_sets:
              - ai_tools_primary
            prompt_profile: ai_tools_default
            landing:
              fallback_url: https://gilgop.cloud/ai-tools
              rules: []
            channels:
              x:
                schedule:
                  cron: "0 9 * * *"
                render:
                  max_chars: 280
                validation:
                  recent_duplicate_window_days: -1
        """,
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        ConfigRegistry.from_directory(tmp_path)

    message = str(exc_info.value)
    assert "accounts.ai_tools_daily.channels.x.validation.recent_duplicate_window_days" in message
    assert "greater than or equal to 0" in message


def test_duplicate_yaml_keys_raise_load_error(tmp_path: Path) -> None:
    _write_valid_prompts_yaml(tmp_path)
    _write_valid_sources_yaml(tmp_path)
    _write_file(
        tmp_path / "accounts.yaml",
        """
        accounts:
          ai_tools_daily:
            topic: "AI tools and workflows"
            topic: "Duplicate topic should fail"
            source_sets:
              - ai_tools_primary
            prompt_profile: ai_tools_default
            landing:
              fallback_url: https://gilgop.cloud/ai-tools
              rules: []
            channels:
              x:
                schedule:
                  cron: "0 9 * * *"
                render:
                  max_chars: 280
        """,
    )

    with pytest.raises(ConfigLoadError) as exc_info:
        ConfigRegistry.from_directory(tmp_path)

    message = str(exc_info.value)
    assert "accounts.yaml" in message
    assert "duplicate key 'topic'" in message


def test_invalid_cron_expression_raises_validation_error(tmp_path: Path) -> None:
    _write_valid_prompts_yaml(tmp_path)
    _write_valid_sources_yaml(tmp_path)
    _write_file(
        tmp_path / "accounts.yaml",
        """
        accounts:
          ai_tools_daily:
            topic: "AI tools and workflows"
            source_sets:
              - ai_tools_primary
            prompt_profile: ai_tools_default
            landing:
              fallback_url: https://gilgop.cloud/ai-tools
              rules: []
            channels:
              x:
                schedule:
                  cron: "not-a-cron"
                render:
                  max_chars: 280
        """,
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        ConfigRegistry.from_directory(tmp_path)

    message = str(exc_info.value)
    assert "accounts.ai_tools_daily.channels.x.schedule.cron" in message
    assert "invalid cron expression" in message


def test_negative_schedule_values_raise_validation_error(tmp_path: Path) -> None:
    _write_valid_prompts_yaml(tmp_path)
    _write_valid_sources_yaml(tmp_path)
    _write_file(
        tmp_path / "accounts.yaml",
        """
        accounts:
          ai_tools_daily:
            topic: "AI tools and workflows"
            source_sets:
              - ai_tools_primary
            prompt_profile: ai_tools_default
            landing:
              fallback_url: https://gilgop.cloud/ai-tools
              rules: []
            channels:
              x:
                schedule:
                  cron: "0 9 * * *"
                  jitter_minutes: -1
                render:
                  max_chars: 280
        """,
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        ConfigRegistry.from_directory(tmp_path)

    message = str(exc_info.value)
    assert "accounts.ai_tools_daily.channels.x.schedule.jitter_minutes" in message
    assert "greater than or equal to 0" in message


def test_blank_matching_keyword_raises_validation_error(tmp_path: Path) -> None:
    _write_valid_prompts_yaml(tmp_path)
    _write_valid_sources_yaml(tmp_path)
    _write_file(
        tmp_path / "accounts.yaml",
        """
        accounts:
          ai_tools_daily:
            topic: "AI tools and workflows"
            source_sets:
              - ai_tools_primary
            prompt_profile: ai_tools_default
            landing:
              fallback_url: https://gilgop.cloud/ai-tools
              rules: []
            matching:
              include_keywords:
                - "   "
            channels:
              x:
                schedule:
                  cron: "0 9 * * *"
                render:
                  max_chars: 280
        """,
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        ConfigRegistry.from_directory(tmp_path)

    message = str(exc_info.value)
    assert "accounts.ai_tools_daily.matching.include_keywords" in message
    assert "must not be empty" in message


def test_blank_banned_phrase_raises_validation_error(tmp_path: Path) -> None:
    _write_valid_prompts_yaml(tmp_path)
    _write_valid_sources_yaml(tmp_path)
    _write_file(
        tmp_path / "accounts.yaml",
        """
        accounts:
          ai_tools_daily:
            topic: "AI tools and workflows"
            source_sets:
              - ai_tools_primary
            prompt_profile: ai_tools_default
            landing:
              fallback_url: https://gilgop.cloud/ai-tools
              rules: []
            channels:
              x:
                schedule:
                  cron: "0 9 * * *"
                render:
                  max_chars: 280
                validation:
                  banned_phrases:
                    - "   "
        """,
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        ConfigRegistry.from_directory(tmp_path)

    message = str(exc_info.value)
    assert "accounts.ai_tools_daily.channels.x.validation.banned_phrases" in message
    assert "must not be empty" in message


def test_blank_publisher_credential_ref_raises_validation_error(tmp_path: Path) -> None:
    _write_valid_prompts_yaml(tmp_path)
    _write_valid_sources_yaml(tmp_path)
    _write_file(
        tmp_path / "accounts.yaml",
        """
        accounts:
          ai_tools_daily:
            topic: "AI tools and workflows"
            source_sets:
              - ai_tools_primary
            prompt_profile: ai_tools_default
            landing:
              fallback_url: https://gilgop.cloud/ai-tools
              rules: []
            channels:
              x:
                schedule:
                  cron: "0 9 * * *"
                render:
                  max_chars: 280
                publisher:
                  credential_ref: "   "
        """,
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        ConfigRegistry.from_directory(tmp_path)

    message = str(exc_info.value)
    assert "accounts.ai_tools_daily.channels.x.publisher.credential_ref" in message
    assert "must not be empty" in message


def test_invalid_landing_rule_tags_raise_validation_error(tmp_path: Path) -> None:
    _write_valid_prompts_yaml(tmp_path)
    _write_valid_sources_yaml(tmp_path)
    _write_file(
        tmp_path / "accounts.yaml",
        """
        accounts:
          ai_tools_daily:
            topic: "AI tools and workflows"
            source_sets:
              - ai_tools_primary
            prompt_profile: ai_tools_default
            landing:
              fallback_url: https://gilgop.cloud/ai-tools
              rules:
                - when_tags_any:
                    - "!!!"
                  url: https://gilgop.cloud/ai-agents
            channels:
              x:
                schedule:
                  cron: "0 9 * * *"
                render:
                  max_chars: 280
        """,
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        ConfigRegistry.from_directory(tmp_path)

    message = str(exc_info.value)
    assert "accounts.ai_tools_daily.landing.rules.0.when_tags_any" in message
    assert "must contain non-empty alphanumeric tags" in message


def _write_valid_prompts_yaml(tmp_path: Path) -> None:
    _write_file(
        tmp_path / "prompts.yaml",
        """
        profiles:
          ai_tools_default:
            system_template: |
              You are an editor for the ai_tools_daily account.
            user_template: |
              Write about {{ title }} and include {{ landing_url }}.
        """,
    )


def _write_valid_sources_yaml(tmp_path: Path) -> None:
    _write_file(
        tmp_path / "sources.yaml",
        """
        sources:
          ai_tools_rss:
            type: rss
            url: https://example.com/feed.xml
          ai_tools_sitemap:
            type: sitemap
            url: https://example.com/sitemap.xml

        source_sets:
          ai_tools_primary:
            sources:
              - ai_tools_rss
              - ai_tools_sitemap
        """,
    )


def _write_file(path: Path, contents: str) -> None:
    path.write_text(dedent(contents).strip() + "\n", encoding="utf-8")
