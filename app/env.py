"""Minimal project-local .env loading helpers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping, MutableMapping


def load_project_env(
    *,
    project_root: Path | None = None,
    environment: MutableMapping[str, str] | None = None,
    override: bool = False,
) -> Path | None:
    """Load the repository's ``.env`` file into the target environment.

    The loader is intentionally tiny so the project does not need an extra
    dependency just to support local operator workflows.
    """

    root = project_root or Path(__file__).resolve().parents[1]
    env_path = root / ".env"
    if not env_path.exists():
        return None

    load_env_file(env_path, environment=environment, override=override)
    return env_path


def load_env_file(
    path: Path,
    *,
    environment: MutableMapping[str, str] | None = None,
    override: bool = False,
) -> None:
    """Parse ``path`` as a dotenv-style file and merge values into environment."""

    target = os.environ if environment is None else environment
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        if not override and key in target:
            continue
        target[key] = _normalize_env_value(raw_value.strip())


def _normalize_env_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value

