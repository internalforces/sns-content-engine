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
    ManualCsvSourceConfig,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_registry_loads_sample_config_directory() -> None:
    registry = ConfigRegistry.from_directory(PROJECT_ROOT / "config")

    account = registry.get_account("ai_tools_daily")
    channel = account.channels["x"]

    assert account.topic == "AI tools and workflows"
    assert account.prompt_profile == "ai_tools_default"
    assert list(registry.accounts) == ["ai_tools_daily"]
    assert str(account.landing.fallback_url) == "https://gilgop.cloud/ai-tools"
    assert str(account.landing.rules[0].url) == "https://gilgop.cloud/ai-agents"
    assert channel.schedule.cron == "0 9 * * *"
    assert channel.render.max_chars == 280
    assert registry.get_prompt_profile("ai_tools_default").system_template.startswith("You are an editor")
    assert registry.get_source_set("ai_tools_primary").sources == (
        "ai_tools_rss",
        "ai_tools_sitemap",
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
