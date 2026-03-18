"""Tests for operational helper utilities."""

from __future__ import annotations

from sqlalchemy.engine import make_url

from app.operations import _describe_database_target


def test_describe_database_target_redacts_credentials_for_non_sqlite_urls() -> None:
    backend, target = _describe_database_target(
        make_url("postgresql://ops-user:super-secret@db.example.com:5432/appdb")
    )

    assert backend == "postgresql"
    assert target == "db.example.com:5432/appdb"
    assert "super-secret" not in target
    assert "ops-user" not in target
