"""Configuration loading and validation for sns-content-engine."""

from app.config.errors import ConfigError, ConfigLoadError, ConfigReferenceError, ConfigValidationError
from app.config.loaders import load_accounts_config, load_prompts_config, load_providers_config, load_sources_config
from app.config.registry import ConfigRegistry
from app.config.schemas import (
    AIProvidersConfig,
    AccountAIConfig,
    AccountConfig,
    AccountMatchingConfig,
    AccountValidationConfig,
    AccountsFileConfig,
    BaseSourceConfig,
    ChannelConfig,
    ChannelPublisherConfig,
    ChannelValidationConfig,
    GdeltSourceConfig,
    LandingConfig,
    LandingRuleConfig,
    LandingValidationConfig,
    ManualCsvSourceConfig,
    PromptProfileConfig,
    PromptsFileConfig,
    RenderConfig,
    RouteConfig,
    RssSourceConfig,
    ScheduleConfig,
    SitemapSourceConfig,
    SourceSetConfig,
    SourcesFileConfig,
)

__all__ = [
    # Schemas — existing
    "AccountConfig",
    "AccountMatchingConfig",
    "AccountValidationConfig",
    "AccountsFileConfig",
    "BaseSourceConfig",
    "ChannelConfig",
    "ChannelPublisherConfig",
    "ChannelValidationConfig",
    "GdeltSourceConfig",
    "LandingConfig",
    "LandingRuleConfig",
    "LandingValidationConfig",
    "ManualCsvSourceConfig",
    "PromptProfileConfig",
    "PromptsFileConfig",
    "RenderConfig",
    "RssSourceConfig",
    "ScheduleConfig",
    "SitemapSourceConfig",
    "SourceSetConfig",
    "SourcesFileConfig",
    # Schemas — Phase 6 (config-driven AI provider control)
    "AccountAIConfig",
    "AIProvidersConfig",
    "RouteConfig",
    # Errors
    "ConfigError",
    "ConfigLoadError",
    "ConfigReferenceError",
    "ConfigRegistry",
    "ConfigValidationError",
    # Loaders
    "load_accounts_config",
    "load_prompts_config",
    "load_providers_config",
    "load_sources_config",
]
