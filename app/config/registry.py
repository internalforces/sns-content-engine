"""Registry object for loaded project configuration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from app.config.errors import ConfigReferenceError
from app.config.loaders import load_accounts_config, load_prompts_config, load_sources_config
from app.config.schemas import (
    AccountConfig,
    ManualCsvSourceConfig,
    PromptProfileConfig,
    SourceConfig,
    SourceSetConfig,
)


@dataclass(frozen=True)
class ConfigRegistry:
    """Frozen registry for resolved configuration values."""

    accounts: Mapping[str, AccountConfig]
    profiles: Mapping[str, PromptProfileConfig]
    sources: Mapping[str, SourceConfig]
    source_sets: Mapping[str, SourceSetConfig]

    @classmethod
    def from_directory(cls, config_dir: Path) -> "ConfigRegistry":
        """Load the project registry from a configuration directory."""

        config_dir = Path(config_dir).resolve()
        accounts_config = load_accounts_config(config_dir / "accounts.yaml")
        prompts_config = load_prompts_config(config_dir / "prompts.yaml")
        sources_config = load_sources_config(config_dir / "sources.yaml")
        normalized_sources = _normalize_sources(sources_config.sources, config_dir)

        _validate_references(
            accounts=accounts_config.accounts,
            profiles=prompts_config.profiles,
            sources=normalized_sources,
            source_sets=sources_config.source_sets,
        )

        return cls(
            accounts=MappingProxyType(dict(accounts_config.accounts)),
            profiles=MappingProxyType(dict(prompts_config.profiles)),
            sources=MappingProxyType(dict(normalized_sources)),
            source_sets=MappingProxyType(dict(sources_config.source_sets)),
        )

    def get_account(self, account_key: str) -> AccountConfig:
        """Return an account configuration by key."""

        return self.accounts[account_key]

    def get_prompt_profile(self, profile_key: str) -> PromptProfileConfig:
        """Return a prompt profile configuration by key."""

        return self.profiles[profile_key]

    def get_source(self, source_key: str) -> SourceConfig:
        """Return a source configuration by key."""

        return self.sources[source_key]

    def get_source_set(self, source_set_key: str) -> SourceSetConfig:
        """Return a source set configuration by key."""

        return self.source_sets[source_set_key]


def _validate_references(
    *,
    accounts: Mapping[str, AccountConfig],
    profiles: Mapping[str, PromptProfileConfig],
    sources: Mapping[str, SourceConfig],
    source_sets: Mapping[str, SourceSetConfig],
) -> None:
    errors: list[str] = []

    for account_key, account in accounts.items():
        if account.prompt_profile not in profiles:
            errors.append(
                "accounts.yaml: "
                f"accounts.{account_key}.prompt_profile: "
                f"unknown prompt profile '{account.prompt_profile}'"
            )

        for index, source_set_key in enumerate(account.source_sets):
            if source_set_key not in source_sets:
                errors.append(
                    "accounts.yaml: "
                    f"accounts.{account_key}.source_sets.{index}: "
                    f"unknown source set '{source_set_key}'"
                )

    for source_set_key, source_set in source_sets.items():
        for index, source_key in enumerate(source_set.sources):
            if source_key not in sources:
                errors.append(
                    "sources.yaml: "
                    f"source_sets.{source_set_key}.sources.{index}: "
                    f"unknown source '{source_key}'"
                )

    if errors:
        raise ConfigReferenceError(errors)


def _normalize_sources(
    sources: Mapping[str, SourceConfig], config_dir: Path
) -> dict[str, SourceConfig]:
    normalized_sources: dict[str, SourceConfig] = {}

    for source_key, source in sources.items():
        if isinstance(source, ManualCsvSourceConfig) and not source.path.is_absolute():
            normalized_sources[source_key] = source.model_copy(
                update={"path": (config_dir / source.path).resolve()}
            )
            continue

        normalized_sources[source_key] = source

    return normalized_sources
