"""Tests for lightweight project .env loading."""

from __future__ import annotations

from pathlib import Path

from app.env import load_env_file


def test_load_env_file_populates_missing_values(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            (
                "# comment",
                "OPENAI_API_KEY=test-key",
                "OPENAI_MODEL=gpt-5.4-mini",
                "export LOG_LEVEL=INFO",
            )
        ),
        encoding="utf-8",
    )

    environment: dict[str, str] = {}
    load_env_file(env_path, environment=environment)

    assert environment == {
        "OPENAI_API_KEY": "test-key",
        "OPENAI_MODEL": "gpt-5.4-mini",
        "LOG_LEVEL": "INFO",
    }


def test_load_env_file_does_not_override_existing_values_by_default(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("OPENAI_MODEL=gpt-5.4-mini\n", encoding="utf-8")

    environment = {"OPENAI_MODEL": "existing-model"}
    load_env_file(env_path, environment=environment)

    assert environment["OPENAI_MODEL"] == "existing-model"

