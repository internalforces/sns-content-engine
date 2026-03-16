"""Custom exceptions for configuration loading and validation."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence


class ConfigError(Exception):
    """Base class for configuration-related failures."""


class ConfigLoadError(ConfigError):
    """Raised when a configuration file cannot be read or parsed."""

    def __init__(self, message: str, *, path: Path | None = None) -> None:
        self.path = path
        super().__init__(message)


class ConfigValidationError(ConfigError):
    """Raised when structured configuration validation fails."""

    def __init__(self, *, path: Path, errors: Sequence[str]) -> None:
        self.path = path
        self.errors = tuple(errors)
        super().__init__("\n".join(self.errors))


class ConfigReferenceError(ConfigError):
    """Raised when cross-file configuration references are invalid."""

    def __init__(self, errors: Sequence[str]) -> None:
        self.errors = tuple(errors)
        super().__init__("\n".join(self.errors))
