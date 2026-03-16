"""Database engine and session helpers for the storage layer."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DEFAULT_DATABASE_URL = "sqlite:///data/sns_content_engine.db"


class Base(DeclarativeBase):
    """Base declarative model for ORM mappings."""


def resolve_database_url(database_url: str | None = None) -> str:
    """Resolve the database URL from explicit input, env, or the default."""

    if database_url and database_url.strip():
        return database_url.strip()

    environment_url = os.environ.get("DATABASE_URL", "").strip()
    if environment_url:
        return environment_url

    return DEFAULT_DATABASE_URL


def create_database_engine(database_url: str | None = None) -> Engine:
    """Create a SQLAlchemy engine for the resolved database URL."""

    resolved_url = resolve_database_url(database_url)
    _ensure_sqlite_directory(resolved_url)
    return create_engine(resolved_url, future=True, pool_pre_ping=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a configured session factory for the given engine."""

    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@contextmanager
def session_scope(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    """Provide a transactional scope around a series of operations."""

    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _ensure_sqlite_directory(database_url: str) -> None:
    url = make_url(database_url)
    if not url.drivername.startswith("sqlite"):
        return

    database = url.database
    if not database or database == ":memory:" or database.startswith("file:"):
        return

    Path(database).expanduser().parent.mkdir(parents=True, exist_ok=True)
