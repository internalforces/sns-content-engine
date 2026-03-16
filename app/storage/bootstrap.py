"""Database bootstrap helpers."""

from __future__ import annotations

from sqlalchemy.engine import Engine

from app.storage.database import Base, create_database_engine, resolve_database_url
import app.storage.models  # noqa: F401


def create_all_tables(engine: Engine) -> None:
    """Create all storage tables on the given engine."""

    Base.metadata.create_all(bind=engine)


def bootstrap_database(database_url: str | None = None) -> str:
    """Initialize the configured database schema and return the resolved URL."""

    resolved_url = resolve_database_url(database_url)
    engine = create_database_engine(resolved_url)
    try:
        create_all_tables(engine)
    finally:
        engine.dispose()

    return resolved_url
