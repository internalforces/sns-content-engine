"""YAML-backed loaders for configuration files."""

from __future__ import annotations

from pathlib import Path
from typing import Any, TypeVar

import yaml
from pydantic import BaseModel, ValidationError

from app.config.errors import ConfigLoadError, ConfigValidationError
from app.config.schemas import AccountsFileConfig, PromptsFileConfig, SourcesFileConfig

ConfigModel = TypeVar("ConfigModel", bound=BaseModel)


def load_accounts_config(path: Path) -> AccountsFileConfig:
    """Load and validate accounts.yaml."""

    return _load_config_file(path, AccountsFileConfig)


def load_prompts_config(path: Path) -> PromptsFileConfig:
    """Load and validate prompts.yaml."""

    return _load_config_file(path, PromptsFileConfig)


def load_sources_config(path: Path) -> SourcesFileConfig:
    """Load and validate sources.yaml."""

    return _load_config_file(path, SourcesFileConfig)


def _load_config_file(path: Path, model_type: type[ConfigModel]) -> ConfigModel:
    data = _load_yaml_mapping(path)
    try:
        return model_type.model_validate(data)
    except ValidationError as exc:
        raise ConfigValidationError(path=path, errors=_format_validation_errors(path, exc)) from exc


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    try:
        raw_text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ConfigLoadError(f"{path.name}: file not found", path=path) from exc
    except OSError as exc:
        raise ConfigLoadError(f"{path.name}: could not read file: {exc}", path=path) from exc

    try:
        data = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        raise ConfigLoadError(f"{path.name}: invalid YAML: {exc}", path=path) from exc

    if not isinstance(data, dict):
        raise ConfigLoadError(f"{path.name}: top-level YAML document must be a mapping", path=path)

    return data


def _format_validation_errors(path: Path, error: ValidationError) -> list[str]:
    formatted_errors: list[str] = []
    for item in error.errors():
        location = ".".join(str(part) for part in item["loc"]) or "<root>"
        formatted_errors.append(f"{path.name}: {location}: {item['msg']}")
    return formatted_errors
