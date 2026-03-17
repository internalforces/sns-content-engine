"""Database bootstrap helpers."""

from __future__ import annotations

from sqlalchemy import inspect
from sqlalchemy.engine import Engine

from app.storage.database import Base, create_database_engine, resolve_database_url
import app.storage.models  # noqa: F401

_REQUIRED_TABLE_COLUMNS = {
    "content_briefs": {
        "account_key",
        "angle",
        "created_at",
        "id",
        "key_points",
        "language",
        "landing_url",
        "source_item_id",
        "summary",
        "tags",
        "title",
        "updated_at",
    },
    "draft_variants": {
        "body",
        "channel",
        "content_brief_id",
        "created_at",
        "id",
        "rejection_reason",
        "reviewed_at",
        "state",
        "updated_at",
        "variant_index",
    },
    "publish_jobs": {
        "attempt_count",
        "channel",
        "created_at",
        "draft_variant_id",
        "external_post_id",
        "id",
        "last_error",
        "published_at",
        "scheduled_for",
        "state",
        "updated_at",
    },
    "publish_logs": {
        "created_at",
        "event_type",
        "id",
        "message",
        "payload",
        "publish_job_id",
    },
    "review_actions": {
        "action_type",
        "after_text",
        "before_text",
        "created_at",
        "draft_state_after",
        "draft_state_before",
        "draft_variant_id",
        "id",
        "publish_job_id",
        "rejection_reason",
        "reviewer",
        "scheduled_for",
    },
    "source_item_recent_fingerprint_claims": {
        "created_at",
        "dedupe_fingerprint",
        "expires_at",
        "id",
        "source_item_id",
    },
    "source_items": {
        "canonical_url",
        "created_at",
        "dedupe_fingerprint",
        "external_id",
        "id",
        "normalized_title",
        "normalized_title_hash",
        "published_at",
        "raw_payload",
        "source_key",
        "source_url",
        "state",
        "summary",
        "title",
        "updated_at",
    },
}
_REQUIRED_UNIQUE_CONSTRAINTS = {
    "content_briefs": {
        "uq_content_briefs_source_item_id_account_key",
    },
    "draft_variants": {
        "uq_draft_variants_content_brief_id_channel_variant_index",
    },
    "source_item_recent_fingerprint_claims": {
        "uq_source_item_recent_fingerprint_claims_dedupe_fingerprint",
        "uq_source_item_recent_fingerprint_claims_source_item_id",
    },
    "source_items": {
        "uq_source_items_canonical_url",
        "uq_source_items_normalized_title_hash",
        "uq_source_items_source_key_external_id",
    },
}


class DatabaseSchemaError(RuntimeError):
    """Raised when an existing database schema does not match the current app model."""


def ensure_database_schema_is_current(engine: Engine) -> None:
    """Validate that the current database exposes the required tables and columns."""

    inspector = inspect(engine)
    actual_tables = set(inspector.get_table_names())
    missing_tables = sorted(set(_REQUIRED_TABLE_COLUMNS) - actual_tables)
    if missing_tables:
        raise DatabaseSchemaError(
            "database schema is outdated and is missing required tables: "
            f"{', '.join(missing_tables)}. Run `sns-engine db init` against a fresh database."
        )

    mismatches: list[str] = []
    for table_name, required_columns in sorted(_REQUIRED_TABLE_COLUMNS.items()):
        actual_columns = {column["name"] for column in inspector.get_columns(table_name)}
        missing_columns = sorted(required_columns - actual_columns)
        if missing_columns:
            mismatches.append(f"{table_name}: missing columns {', '.join(missing_columns)}")

    for table_name, required_constraints in sorted(_REQUIRED_UNIQUE_CONSTRAINTS.items()):
        actual_constraints = {
            constraint["name"]
            for constraint in inspector.get_unique_constraints(table_name)
            if constraint.get("name")
        }
        missing_constraints = sorted(required_constraints - actual_constraints)
        if missing_constraints:
            mismatches.append(
                f"{table_name}: missing unique constraints {', '.join(missing_constraints)}"
            )

    if mismatches:
        mismatch_text = "; ".join(mismatches)
        raise DatabaseSchemaError(
            "database schema is outdated and cannot be upgraded automatically: "
            f"{mismatch_text}. Recreate the SQLite database or apply a migration."
        )


def create_all_tables(engine: Engine) -> None:
    """Create all storage tables on the given engine."""

    Base.metadata.create_all(bind=engine)


def bootstrap_database(database_url: str | None = None) -> str:
    """Initialize the configured database schema and return the resolved URL."""

    resolved_url = resolve_database_url(database_url)
    engine = create_database_engine(resolved_url)
    try:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        if not existing_tables:
            create_all_tables(engine)
        ensure_database_schema_is_current(engine)
    finally:
        engine.dispose()

    return resolved_url
