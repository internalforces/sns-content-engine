"""Pydantic schemas for sns-content-engine configuration files."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from types import MappingProxyType
from typing import Annotated, Literal, Mapping

from apscheduler.triggers.cron import CronTrigger
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from app.domain.source_deduplication import normalize_title_text


class FrozenConfigModel(BaseModel):
    """Base config model with strict validation and immutable instances."""

    model_config = ConfigDict(extra="forbid", frozen=True)


def _normalize_non_empty_string(value: str, *, label: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} must not be empty")
    return normalized


def _normalize_non_empty_string_sequence(
    values: tuple[str, ...] | list[str], *, label: str
) -> tuple[str, ...]:
    normalized = tuple(_normalize_non_empty_string(value, label=label) for value in values)
    if not normalized:
        raise ValueError(f"{label} must contain at least one value")
    return normalized


def _normalize_string_sequence(
    values: tuple[str, ...] | list[str],
    *,
    label: str,
    normalizer: Callable[[str], str] | None = None,
) -> tuple[str, ...]:
    normalized_values: list[str] = []
    seen: set[str] = set()

    for value in values:
        normalized = _normalize_non_empty_string(value, label=label)
        if normalizer is None:
            normalized = normalized.casefold()
        else:
            normalized = normalizer(normalized)
        if normalized in seen:
            continue
        seen.add(normalized)
        normalized_values.append(normalized)

    return tuple(normalized_values)


def _normalize_tag_sequence(
    values: tuple[str, ...] | list[str],
    *,
    label: str,
    require_non_empty: bool,
) -> tuple[str, ...]:
    normalized_values: list[str] = []
    seen: set[str] = set()

    for value in values:
        normalized_input = _normalize_non_empty_string(value, label=label)
        try:
            normalized = normalize_title_text(normalized_input)
        except ValueError as exc:
            raise ValueError(f"{label} must contain non-empty alphanumeric tags") from exc
        if normalized in seen:
            continue
        seen.add(normalized)
        normalized_values.append(normalized)

    if require_non_empty and not normalized_values:
        raise ValueError(f"{label} must contain at least one value")

    return tuple(normalized_values)


def _validate_mapping_keys(
    mapping: Mapping[str, object], *, label: str
) -> Mapping[str, object]:
    normalized_mapping = dict(mapping)
    for key in normalized_mapping:
        if key != key.strip():
            raise ValueError(f"{label} keys must not include leading or trailing whitespace")
        if not key:
            raise ValueError(f"{label} keys must not be empty")
    return MappingProxyType(normalized_mapping)


class LandingRuleConfig(FrozenConfigModel):
    """Tag-based landing rule."""

    when_tags_any: tuple[str, ...] = Field(min_length=1)
    url: HttpUrl

    @field_validator("when_tags_any")
    @classmethod
    def validate_tags(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return _normalize_tag_sequence(
            values,
            label="landing rule tags",
            require_non_empty=True,
        )


class LandingConfig(FrozenConfigModel):
    """Landing resolution settings for an account."""

    fallback_url: HttpUrl
    rules: tuple[LandingRuleConfig, ...] = Field(default_factory=tuple)


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


class ChannelValidationConfig(FrozenConfigModel):
    """Validation rules applied to channel drafts."""

    max_links: int = Field(default=1, ge=0)
    banned_phrases: tuple[str, ...] = Field(default_factory=tuple)
    recent_duplicate_window_days: int = Field(default=7, ge=0)

    @field_validator("banned_phrases")
    @classmethod
    def validate_banned_phrases(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return _normalize_string_sequence(values, label="banned phrase")


class ChannelPublisherConfig(FrozenConfigModel):
    """Publisher credential lookup settings for a channel."""

    credential_ref: str

    @field_validator("credential_ref")
    @classmethod
    def validate_credential_ref(cls, value: str) -> str:
        return _normalize_non_empty_string(value, label="credential_ref")


class ChannelConfig(FrozenConfigModel):
    """Channel-level settings for publishing."""

    schedule: ScheduleConfig
    render: RenderConfig
    validation: ChannelValidationConfig = Field(default_factory=ChannelValidationConfig)
    publisher: ChannelPublisherConfig | None = None



class AccountMatchingConfig(FrozenConfigModel):
    """Deterministic rule-based account matching configuration."""

    include_keywords: tuple[str, ...] = Field(default_factory=tuple)
    exclude_keywords: tuple[str, ...] = Field(default_factory=tuple)
    source_tags: tuple[str, ...] = Field(default_factory=tuple)
    strict_topic_guard: bool = False

    @field_validator("include_keywords", "exclude_keywords")
    @classmethod
    def validate_keyword_sequences(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return _normalize_string_sequence(values, label="matching value")

    @field_validator("source_tags")
    @classmethod
    def validate_source_tags(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return _normalize_tag_sequence(
            values,
            label="matching value",
            require_non_empty=False,
        )


class AccountValidationConfig(FrozenConfigModel):
    """Account-level validation profile selection."""

    profile: Literal["standard", "finance_strict"] = "standard"


class AccountConfig(FrozenConfigModel):
    """Account-level content engine settings."""

    topic: str
    source_sets: tuple[str, ...] = Field(min_length=1)
    prompt_profile: str
    landing: LandingConfig
    matching: AccountMatchingConfig = Field(default_factory=AccountMatchingConfig)
    validation: AccountValidationConfig = Field(default_factory=AccountValidationConfig)
    channels: Mapping[str, ChannelConfig] = Field(min_length=1)

    @field_validator("topic", "prompt_profile")
    @classmethod
    def validate_strings(cls, value: str) -> str:
        return _normalize_non_empty_string(value, label="account value")

    @field_validator("source_sets")
    @classmethod
    def validate_source_sets(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return _normalize_non_empty_string_sequence(values, label="source set references")

    @field_validator("channels")
    @classmethod
    def validate_channel_keys(
        cls, value: Mapping[str, ChannelConfig]
    ) -> Mapping[str, ChannelConfig]:
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

    sources: tuple[str, ...] = Field(min_length=1)

    @field_validator("sources")
    @classmethod
    def validate_sources(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return _normalize_non_empty_string_sequence(values, label="source references")


class BaseSourceConfig(FrozenConfigModel):
    """Shared source configuration fields."""

    duplicate_window_days: int = Field(default=30, ge=0)


class RssSourceConfig(BaseSourceConfig):
    """RSS source definition."""

    type: Literal["rss"]
    url: HttpUrl


class SitemapSourceConfig(BaseSourceConfig):
    """Sitemap source definition."""

    type: Literal["sitemap"]
    url: HttpUrl


class ManualCsvSourceConfig(BaseSourceConfig):
    """Manual CSV source definition."""

    type: Literal["manual_csv"]
    path: Path


SourceConfig = Annotated[
    RssSourceConfig | SitemapSourceConfig | ManualCsvSourceConfig,
    Field(discriminator="type"),
]


class AccountsFileConfig(FrozenConfigModel):
    """Top-level schema for accounts.yaml."""

    accounts: Mapping[str, AccountConfig]

    @field_validator("accounts")
    @classmethod
    def validate_account_keys(
        cls, value: Mapping[str, AccountConfig]
    ) -> Mapping[str, AccountConfig]:
        return _validate_mapping_keys(value, label="account")


class PromptsFileConfig(FrozenConfigModel):
    """Top-level schema for prompts.yaml."""

    profiles: Mapping[str, PromptProfileConfig]

    @field_validator("profiles")
    @classmethod
    def validate_profile_keys(
        cls, value: Mapping[str, PromptProfileConfig]
    ) -> Mapping[str, PromptProfileConfig]:
        return _validate_mapping_keys(value, label="prompt profile")


class SourcesFileConfig(FrozenConfigModel):
    """Top-level schema for sources.yaml."""

    sources: Mapping[str, SourceConfig]
    source_sets: Mapping[str, SourceSetConfig]

    @field_validator("sources")
    @classmethod
    def validate_source_keys(
        cls, value: Mapping[str, SourceConfig]
    ) -> Mapping[str, SourceConfig]:
        return _validate_mapping_keys(value, label="source")

    @field_validator("source_sets")
    @classmethod
    def validate_source_set_keys(
        cls, value: Mapping[str, SourceSetConfig]
    ) -> Mapping[str, SourceSetConfig]:
        return _validate_mapping_keys(value, label="source set")
