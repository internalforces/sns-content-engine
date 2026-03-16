"""Pydantic schemas for sns-content-engine configuration files."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

from apscheduler.triggers.cron import CronTrigger
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class FrozenConfigModel(BaseModel):
    """Base config model with strict validation and immutable instances."""

    model_config = ConfigDict(extra="forbid", frozen=True)


def _normalize_non_empty_string(value: str, *, label: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} must not be empty")
    return normalized


def _normalize_non_empty_string_list(values: list[str], *, label: str) -> list[str]:
    normalized = [_normalize_non_empty_string(value, label=label) for value in values]
    if not normalized:
        raise ValueError(f"{label} must contain at least one value")
    return normalized


def _validate_mapping_keys(mapping: dict[str, object], *, label: str) -> dict[str, object]:
    for key in mapping:
        if key != key.strip():
            raise ValueError(f"{label} keys must not include leading or trailing whitespace")
        if not key:
            raise ValueError(f"{label} keys must not be empty")
    return mapping


class LandingRuleConfig(FrozenConfigModel):
    """Tag-based landing rule."""

    when_tags_any: list[str] = Field(min_length=1)
    url: HttpUrl

    @field_validator("when_tags_any")
    @classmethod
    def validate_tags(cls, values: list[str]) -> list[str]:
        return _normalize_non_empty_string_list(values, label="landing rule tags")


class LandingConfig(FrozenConfigModel):
    """Landing resolution settings for an account."""

    fallback_url: HttpUrl
    rules: list[LandingRuleConfig] = Field(default_factory=list)


class ScheduleConfig(FrozenConfigModel):
    """Schedule settings shared across channels."""

    cron: str
    window_minutes: int = Field(default=0, ge=0)
    jitter_minutes: int = Field(default=0, ge=0)
    min_gap_minutes: int = Field(default=0, ge=0)
    backlog_target: int = Field(default=0, ge=0)

    @field_validator("cron")
    @classmethod
    def validate_cron(cls, value: str) -> str:
        normalized = _normalize_non_empty_string(value, label="cron")
        try:
            CronTrigger.from_crontab(normalized)
        except ValueError as exc:
            raise ValueError(f"invalid cron expression: {normalized}") from exc
        return normalized


class RenderConfig(FrozenConfigModel):
    """Rendering options for a channel."""

    max_chars: int = Field(gt=0)


class ChannelConfig(FrozenConfigModel):
    """Channel-level settings for publishing."""

    schedule: ScheduleConfig
    render: RenderConfig


class AccountConfig(FrozenConfigModel):
    """Account-level content engine settings."""

    topic: str
    source_sets: list[str] = Field(min_length=1)
    prompt_profile: str
    landing: LandingConfig
    channels: dict[str, ChannelConfig] = Field(min_length=1)

    @field_validator("topic", "prompt_profile")
    @classmethod
    def validate_strings(cls, value: str) -> str:
        return _normalize_non_empty_string(value, label="account value")

    @field_validator("source_sets")
    @classmethod
    def validate_source_sets(cls, values: list[str]) -> list[str]:
        return _normalize_non_empty_string_list(values, label="source set references")

    @field_validator("channels")
    @classmethod
    def validate_channel_keys(cls, value: dict[str, ChannelConfig]) -> dict[str, ChannelConfig]:
        return _validate_mapping_keys(value, label="channel")


class PromptProfileConfig(FrozenConfigModel):
    """Prompt templates used during draft generation."""

    system_template: str
    user_template: str

    @field_validator("system_template", "user_template")
    @classmethod
    def validate_template(cls, value: str) -> str:
        return _normalize_non_empty_string(value, label="template")


class SourceSetConfig(FrozenConfigModel):
    """Reusable grouping of source identifiers."""

    sources: list[str] = Field(min_length=1)

    @field_validator("sources")
    @classmethod
    def validate_sources(cls, values: list[str]) -> list[str]:
        return _normalize_non_empty_string_list(values, label="source references")


class RssSourceConfig(FrozenConfigModel):
    """RSS source definition."""

    type: Literal["rss"]
    url: HttpUrl


class SitemapSourceConfig(FrozenConfigModel):
    """Sitemap source definition."""

    type: Literal["sitemap"]
    url: HttpUrl


class ManualCsvSourceConfig(FrozenConfigModel):
    """Manual CSV source definition."""

    type: Literal["manual_csv"]
    path: Path


SourceConfig = Annotated[
    RssSourceConfig | SitemapSourceConfig | ManualCsvSourceConfig,
    Field(discriminator="type"),
]


class AccountsFileConfig(FrozenConfigModel):
    """Top-level schema for accounts.yaml."""

    accounts: dict[str, AccountConfig]

    @field_validator("accounts")
    @classmethod
    def validate_account_keys(cls, value: dict[str, AccountConfig]) -> dict[str, AccountConfig]:
        return _validate_mapping_keys(value, label="account")


class PromptsFileConfig(FrozenConfigModel):
    """Top-level schema for prompts.yaml."""

    profiles: dict[str, PromptProfileConfig]

    @field_validator("profiles")
    @classmethod
    def validate_profile_keys(
        cls, value: dict[str, PromptProfileConfig]
    ) -> dict[str, PromptProfileConfig]:
        return _validate_mapping_keys(value, label="prompt profile")


class SourcesFileConfig(FrozenConfigModel):
    """Top-level schema for sources.yaml."""

    sources: dict[str, SourceConfig]
    source_sets: dict[str, SourceSetConfig]

    @field_validator("sources")
    @classmethod
    def validate_source_keys(cls, value: dict[str, SourceConfig]) -> dict[str, SourceConfig]:
        return _validate_mapping_keys(value, label="source")

    @field_validator("source_sets")
    @classmethod
    def validate_source_set_keys(
        cls, value: dict[str, SourceSetConfig]
    ) -> dict[str, SourceSetConfig]:
        return _validate_mapping_keys(value, label="source set")
