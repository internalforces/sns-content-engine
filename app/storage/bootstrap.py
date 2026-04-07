"""Database bootstrap and SQLite migration helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json

from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import SQLAlchemyError

from app.domain import (
    build_dedupe_fingerprint,
    build_normalized_title_hash,
    canonicalize_url,
    normalize_title_text,
)
from app.storage.database import Base, create_database_engine, resolve_database_url
import app.storage.models  # noqa: F401

_SCHEMA_MIGRATIONS_TABLE = "schema_migrations"
_LEGACY_SCHEMA_VERSION = 1
_LATEST_SCHEMA_VERSION = 2
_LATEST_SCHEMA_MIGRATION_NAME = "002_sqlite_migration_baseline"

_REQUIRED_TABLE_COLUMNS = {
    "article_enrichments": {
        "article_extract_status",
        "article_text",
        "article_url",
        "brief_build_status",
        "classification",
        "company_names",
        "created_at",
        "discovered_at",
        "draft_generate_status",
        "extracted_at",
        "failure_code",
        "failure_message",
        "failure_stage",
        "fetched_at",
        "html_content",
        "html_fetch_status",
        "id",
        "last_stage",
        "markets",
        "metadata_json",
        "policy_decision_reason",
        "published_at",
        "regenerated_key_points",
        "regenerated_summary",
        "review_status",
        "rss_discovered_status",
        "saved_status",
        "source_item_id",
        "source_name",
        "summarized_at",
        "summary_regenerate_status",
        "tags",
        "tickers",
        "updated_at",
    },
    "pipeline_runs": {
        "completed_at",
        "created_at",
        "discovered_count",
        "draft_count",
        "enriched_count",
        "failure_count",
        "id",
        "latest_error_code",
        "latest_error_message",
        "saved_count",
        "source_count",
        "started_at",
        "status",
        "summary_json",
        "summarized_count",
        "trigger_mode",
        "updated_at",
        "workflow_name",
        "brief_count",
    },
    "pipeline_run_stages": {
        "completed_at",
        "created_at",
        "failure_count",
        "id",
        "item_count",
        "latest_error_code",
        "latest_error_message",
        "pipeline_run_id",
        "stage",
        "started_at",
        "status",
        "success_count",
        "summary_json",
        "updated_at",
    },
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
        "article_url",
        "body",
        "channel",
        "content_brief_id",
        "created_at",
        "id",
        "rejection_reason",
        "reviewed_at",
        "source_name",
        "source_policy_mode",
        "source_published_at",
        "source_url",
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
        "idempotency_key",
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
        "allow_full_text_fetch",
        "allow_llm_rewrite",
        "normalized_title",
        "normalized_title_hash",
        "policy_mode",
        "published_at",
        "raw_payload",
        "require_attribution",
        "source_key",
        "source_url",
        "state",
        "summary",
        "title",
        "updated_at",
    },
}
_REQUIRED_UNIQUE_CONSTRAINTS = {
    "article_enrichments": {
        "uq_article_enrichments_source_item_id",
    },
    "pipeline_run_stages": {
        "uq_pipeline_run_stages_pipeline_run_id_stage",
    },
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
_REQUIRED_UNIQUE_INDEXES = {
    "publish_jobs": {
        "uq_publish_jobs_active_draft_variant_id",
        "uq_publish_jobs_idempotency_key",
    },
}
_SQLITE_REQUIRED_UNIQUE_INDEX_STATEMENTS = {
    ("article_enrichments", "uq_article_enrichments_source_item_id"): (
        "CREATE UNIQUE INDEX uq_article_enrichments_source_item_id "
        "ON article_enrichments (source_item_id)"
    ),
    ("pipeline_run_stages", "uq_pipeline_run_stages_pipeline_run_id_stage"): (
        "CREATE UNIQUE INDEX uq_pipeline_run_stages_pipeline_run_id_stage "
        "ON pipeline_run_stages (pipeline_run_id, stage)"
    ),
    ("content_briefs", "uq_content_briefs_source_item_id_account_key"): (
        "CREATE UNIQUE INDEX uq_content_briefs_source_item_id_account_key "
        "ON content_briefs (source_item_id, account_key)"
    ),
    ("draft_variants", "uq_draft_variants_content_brief_id_channel_variant_index"): (
        "CREATE UNIQUE INDEX uq_draft_variants_content_brief_id_channel_variant_index "
        "ON draft_variants (content_brief_id, channel, variant_index)"
    ),
    (
        "source_item_recent_fingerprint_claims",
        "uq_source_item_recent_fingerprint_claims_dedupe_fingerprint",
    ): (
        "CREATE UNIQUE INDEX uq_source_item_recent_fingerprint_claims_dedupe_fingerprint "
        "ON source_item_recent_fingerprint_claims (dedupe_fingerprint)"
    ),
    (
        "source_item_recent_fingerprint_claims",
        "uq_source_item_recent_fingerprint_claims_source_item_id",
    ): (
        "CREATE UNIQUE INDEX uq_source_item_recent_fingerprint_claims_source_item_id "
        "ON source_item_recent_fingerprint_claims (source_item_id)"
    ),
    ("source_items", "uq_source_items_canonical_url"): (
        "CREATE UNIQUE INDEX uq_source_items_canonical_url ON source_items (canonical_url)"
    ),
    ("source_items", "uq_source_items_normalized_title_hash"): (
        "CREATE UNIQUE INDEX uq_source_items_normalized_title_hash "
        "ON source_items (normalized_title_hash)"
    ),
    ("source_items", "uq_source_items_source_key_external_id"): (
        "CREATE UNIQUE INDEX uq_source_items_source_key_external_id "
        "ON source_items (source_key, external_id)"
    ),
    ("publish_jobs", "uq_publish_jobs_idempotency_key"): (
        "CREATE UNIQUE INDEX uq_publish_jobs_idempotency_key "
        "ON publish_jobs (idempotency_key)"
    ),
    ("publish_jobs", "uq_publish_jobs_active_draft_variant_id"): (
        "CREATE UNIQUE INDEX uq_publish_jobs_active_draft_variant_id "
        "ON publish_jobs (draft_variant_id) "
        "WHERE state IN ('SCHEDULED', 'PUBLISHING', 'PUBLISHED')"
    ),
}


@dataclass(frozen=True, slots=True)
class SchemaUpgradeResult:
    """Summary of one explicit schema upgrade attempt."""

    database_url: str
    from_version: int
    to_version: int
    applied_migrations: tuple[str, ...]

    @property
    def was_upgraded(self) -> bool:
        """Return whether any upgrade step was applied."""

        return bool(self.applied_migrations)


class DatabaseSchemaError(RuntimeError):
    """Raised when an existing database schema does not match the current app model."""


def ensure_database_schema_is_current(engine: Engine) -> None:
    """Validate that the current database exposes the required tables and columns."""

    inspector = inspect(engine)
    actual_tables = set(inspector.get_table_names())
    if not actual_tables:
        raise DatabaseSchemaError(
            "database schema is not initialized. Run `sns-engine db init` against a fresh database."
        )

    missing_tables = sorted(set(_REQUIRED_TABLE_COLUMNS) - actual_tables)
    mismatches: list[str] = []
    for table_name, required_columns in sorted(_REQUIRED_TABLE_COLUMNS.items()):
        if table_name not in actual_tables:
            continue

        actual_columns = {column["name"] for column in inspector.get_columns(table_name)}
        missing_columns = sorted(required_columns - actual_columns)
        if missing_columns:
            mismatches.append(f"{table_name}: missing columns {', '.join(missing_columns)}")

    for table_name, required_constraints in sorted(_REQUIRED_UNIQUE_CONSTRAINTS.items()):
        if table_name not in actual_tables:
            continue
        actual_unique_names = _collect_unique_names(inspector, table_name)
        missing_constraints = sorted(required_constraints - actual_unique_names)
        if missing_constraints:
            mismatches.append(
                f"{table_name}: missing unique constraints {', '.join(missing_constraints)}"
            )

    for table_name, required_indexes in sorted(_REQUIRED_UNIQUE_INDEXES.items()):
        if table_name not in actual_tables:
            continue
        actual_indexes = {
            index["name"]
            for index in inspector.get_indexes(table_name)
            if index.get("name") and index.get("unique")
        }
        missing_indexes = sorted(required_indexes - actual_indexes)
        if missing_indexes:
            mismatches.append(f"{table_name}: missing unique indexes {', '.join(missing_indexes)}")

    if missing_tables or mismatches:
        raise DatabaseSchemaError(
            _format_outdated_schema_message(
                engine=engine,
                missing_tables=missing_tables,
                mismatches=mismatches,
            )
        )


def create_all_tables(bind: Engine | Connection) -> None:
    """Create all storage tables on the given engine or connection."""

    Base.metadata.create_all(bind=bind)


def get_database_schema_version(engine: Engine) -> int:
    """Return the detected schema version for the given database."""

    inspector = inspect(engine)
    actual_tables = set(inspector.get_table_names())
    if not actual_tables:
        return 0

    if _SCHEMA_MIGRATIONS_TABLE not in actual_tables:
        return _LEGACY_SCHEMA_VERSION

    with engine.connect() as connection:
        version = connection.execute(
            text(f"SELECT MAX(version) FROM {_SCHEMA_MIGRATIONS_TABLE}")
        ).scalar_one()

    if version is None:
        return _LEGACY_SCHEMA_VERSION if actual_tables - {_SCHEMA_MIGRATIONS_TABLE} else 0

    return int(version)


def bootstrap_database(database_url: str | None = None) -> str:
    """Initialize the configured database schema and return the resolved URL."""

    resolved_url = resolve_database_url(database_url)
    engine = create_database_engine(resolved_url)
    try:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        if not existing_tables:
            with engine.begin() as connection:
                create_all_tables(connection)
                _ensure_schema_migrations_table(connection)
                _record_schema_migration(
                    connection,
                    version=_LATEST_SCHEMA_VERSION,
                    description="bootstrap current schema",
                )
        ensure_database_schema_is_current(engine)
    finally:
        engine.dispose()

    return resolved_url


def upgrade_database_schema(database_url: str | None = None) -> SchemaUpgradeResult:
    """Apply the supported SQLite schema upgrades to an existing database."""

    resolved_url = resolve_database_url(database_url)
    engine = create_database_engine(resolved_url)
    try:
        if not _is_sqlite_engine(engine):
            raise DatabaseSchemaError(
                "automatic schema upgrades are only supported for SQLite local databases."
            )

        actual_tables = set(inspect(engine).get_table_names())
        if not actual_tables:
            raise DatabaseSchemaError(
                "database schema is not initialized. Run `sns-engine db init` against a fresh database."
            )

        from_version = get_database_schema_version(engine)
        if from_version > _LATEST_SCHEMA_VERSION:
            raise DatabaseSchemaError(
                "database schema version is newer than this application supports. "
                "Upgrade the app before running schema changes."
            )

        applied_migrations: list[str] = []
        if from_version < _LATEST_SCHEMA_VERSION:
            if from_version != _LEGACY_SCHEMA_VERSION:
                raise DatabaseSchemaError(
                    f"database schema version `{from_version}` is not supported by the SQLite upgrader."
                )
            _apply_sqlite_legacy_upgrade(engine)
            applied_migrations.append(_LATEST_SCHEMA_MIGRATION_NAME)

        ensure_database_schema_is_current(engine)
        to_version = get_database_schema_version(engine)
    finally:
        engine.dispose()

    return SchemaUpgradeResult(
        database_url=resolved_url,
        from_version=from_version,
        to_version=to_version,
        applied_migrations=tuple(applied_migrations),
    )


def _format_outdated_schema_message(
    *,
    engine: Engine,
    missing_tables: list[str],
    mismatches: list[str],
) -> str:
    details: list[str] = []
    if missing_tables:
        details.append(f"missing required tables: {', '.join(missing_tables)}")
    details.extend(mismatches)
    detail_text = "; ".join(details)

    if _is_sqlite_engine(engine):
        return (
            "database schema is outdated: "
            f"{detail_text}. Run `sns-engine db upgrade` to apply the SQLite migration baseline "
            "or recreate the database if the file is not a supported local schema."
        )

    return (
        "database schema is outdated and cannot be upgraded automatically: "
        f"{detail_text}. Recreate the database or apply a manual migration."
    )


def _apply_sqlite_legacy_upgrade(engine: Engine) -> None:
    try:
        with engine.begin() as connection:
            create_all_tables(connection)
            _upgrade_pipeline_runs_table(connection)
            _upgrade_source_items_table(connection)
            _upgrade_article_enrichments_table(connection)
            _upgrade_content_briefs_table(connection)
            _upgrade_draft_variants_table(connection)
            _upgrade_publish_jobs_table(connection)
            _ensure_sqlite_unique_indexes(connection)
            _ensure_schema_migrations_table(connection)
            _record_schema_migration(
                connection,
                version=_LATEST_SCHEMA_VERSION,
                description="sqlite migration baseline",
            )
    except (SQLAlchemyError, ValueError) as exc:
        raise DatabaseSchemaError(
            "database schema upgrade failed: "
            f"{exc}. Recreate the SQLite database if the stored data cannot be migrated safely."
        ) from exc


def _upgrade_pipeline_runs_table(connection: Connection) -> None:
    if not _table_exists(connection, "pipeline_runs"):
        return
    _add_column_if_missing(
        connection,
        table_name="pipeline_runs",
        column_name="brief_count",
        column_sql="brief_count INTEGER NOT NULL DEFAULT 0",
    )


def _upgrade_source_items_table(connection: Connection) -> None:
    if not _table_exists(connection, "source_items"):
        return

    _add_column_if_missing(
        connection,
        table_name="source_items",
        column_name="canonical_url",
        column_sql="canonical_url VARCHAR(2048)",
    )
    _add_column_if_missing(
        connection,
        table_name="source_items",
        column_name="normalized_title",
        column_sql="normalized_title VARCHAR(500)",
    )
    _add_column_if_missing(
        connection,
        table_name="source_items",
        column_name="normalized_title_hash",
        column_sql="normalized_title_hash VARCHAR(64)",
    )
    _add_column_if_missing(
        connection,
        table_name="source_items",
        column_name="dedupe_fingerprint",
        column_sql="dedupe_fingerprint VARCHAR(64)",
    )
    _add_column_if_missing(
        connection,
        table_name="source_items",
        column_name="policy_mode",
        column_sql="policy_mode VARCHAR(32) NOT NULL DEFAULT 'REUSABLE'",
    )
    _add_column_if_missing(
        connection,
        table_name="source_items",
        column_name="allow_full_text_fetch",
        column_sql="allow_full_text_fetch BOOLEAN NOT NULL DEFAULT 1",
    )
    _add_column_if_missing(
        connection,
        table_name="source_items",
        column_name="allow_llm_rewrite",
        column_sql="allow_llm_rewrite BOOLEAN NOT NULL DEFAULT 1",
    )
    _add_column_if_missing(
        connection,
        table_name="source_items",
        column_name="require_attribution",
        column_sql="require_attribution BOOLEAN NOT NULL DEFAULT 0",
    )

    rows = connection.execute(
        text(
            "SELECT id, source_url, title, summary, canonical_url, normalized_title, "
            "normalized_title_hash, dedupe_fingerprint "
            "FROM source_items ORDER BY id"
        )
    ).mappings()
    for row in rows:
        updates: dict[str, object] = {}
        if _is_missing_scalar(row["canonical_url"]):
            updates["canonical_url"] = canonicalize_url(str(row["source_url"]))
        if _is_missing_scalar(row["normalized_title"]):
            updates["normalized_title"] = normalize_title_text(str(row["title"]))
        if _is_missing_scalar(row["normalized_title_hash"]):
            updates["normalized_title_hash"] = build_normalized_title_hash(str(row["title"]))
        if _is_missing_scalar(row["dedupe_fingerprint"]):
            updates["dedupe_fingerprint"] = build_dedupe_fingerprint(
                title=str(row["title"]),
                summary=_clean_optional_text(row["summary"]),
            )
        if updates:
            _update_row(connection, table_name="source_items", row_id=int(row["id"]), values=updates)


def _upgrade_article_enrichments_table(connection: Connection) -> None:
    if not _table_exists(connection, "article_enrichments"):
        return
    _add_column_if_missing(
        connection,
        table_name="article_enrichments",
        column_name="policy_decision_reason",
        column_sql="policy_decision_reason TEXT",
    )


def _upgrade_content_briefs_table(connection: Connection) -> None:
    if not _table_exists(connection, "content_briefs"):
        return

    _add_column_if_missing(
        connection,
        table_name="content_briefs",
        column_name="key_points",
        column_sql="key_points JSON NOT NULL DEFAULT '[]'",
    )
    _add_column_if_missing(
        connection,
        table_name="content_briefs",
        column_name="angle",
        column_sql="angle VARCHAR(64) NOT NULL DEFAULT 'topic_takeaway'",
    )
    _add_column_if_missing(
        connection,
        table_name="content_briefs",
        column_name="language",
        column_sql="language VARCHAR(8) NOT NULL DEFAULT 'en'",
    )

    rows = connection.execute(
        text("SELECT id, title, summary, key_points, angle, language FROM content_briefs ORDER BY id")
    ).mappings()
    for row in rows:
        updates: dict[str, object] = {}
        if _is_missing_json_array(row["key_points"]):
            fallback_points = [str(row["title"]).strip()]
            summary = _clean_optional_text(row["summary"])
            if summary and summary not in fallback_points and len(fallback_points) < 3:
                fallback_points.append(summary)
            updates["key_points"] = json.dumps(fallback_points)
        if _is_missing_scalar(row["angle"]):
            updates["angle"] = "topic_takeaway"
        if _is_missing_scalar(row["language"]):
            updates["language"] = "en"
        if updates:
            _update_row(connection, table_name="content_briefs", row_id=int(row["id"]), values=updates)


def _upgrade_draft_variants_table(connection: Connection) -> None:
    if not _table_exists(connection, "draft_variants"):
        return

    _add_column_if_missing(
        connection,
        table_name="draft_variants",
        column_name="source_name",
        column_sql="source_name VARCHAR(255)",
    )
    _add_column_if_missing(
        connection,
        table_name="draft_variants",
        column_name="source_url",
        column_sql="source_url VARCHAR(2048)",
    )
    _add_column_if_missing(
        connection,
        table_name="draft_variants",
        column_name="article_url",
        column_sql="article_url VARCHAR(2048)",
    )
    _add_column_if_missing(
        connection,
        table_name="draft_variants",
        column_name="source_published_at",
        column_sql="source_published_at DATETIME",
    )
    _add_column_if_missing(
        connection,
        table_name="draft_variants",
        column_name="source_policy_mode",
        column_sql="source_policy_mode VARCHAR(32)",
    )

    rows = connection.execute(
        text(
            "SELECT draft_variants.id, draft_variants.source_name, draft_variants.source_url, "
            "draft_variants.article_url, draft_variants.source_published_at, "
            "draft_variants.source_policy_mode, source_items.source_key, source_items.source_url AS item_source_url, "
            "source_items.published_at AS item_published_at, source_items.policy_mode AS item_policy_mode, "
            "article_enrichments.source_name AS enrichment_source_name, "
            "article_enrichments.article_url AS enrichment_article_url, "
            "article_enrichments.published_at AS enrichment_published_at "
            "FROM draft_variants "
            "JOIN content_briefs ON content_briefs.id = draft_variants.content_brief_id "
            "JOIN source_items ON source_items.id = content_briefs.source_item_id "
            "LEFT JOIN article_enrichments ON article_enrichments.source_item_id = source_items.id "
            "ORDER BY draft_variants.id"
        )
    ).mappings()
    for row in rows:
        updates: dict[str, object] = {}
        if _is_missing_scalar(row["source_name"]):
            updates["source_name"] = row["enrichment_source_name"] or row["source_key"]
        if _is_missing_scalar(row["source_url"]):
            updates["source_url"] = row["item_source_url"]
        if _is_missing_scalar(row["article_url"]):
            updates["article_url"] = row["enrichment_article_url"] or row["item_source_url"]
        if row["source_published_at"] is None:
            updates["source_published_at"] = (
                row["enrichment_published_at"] or row["item_published_at"]
            )
        if _is_missing_scalar(row["source_policy_mode"]):
            updates["source_policy_mode"] = row["item_policy_mode"] or "REUSABLE"
        if updates:
            _update_row(connection, table_name="draft_variants", row_id=int(row["id"]), values=updates)


def _upgrade_publish_jobs_table(connection: Connection) -> None:
    if not _table_exists(connection, "publish_jobs"):
        return

    _add_column_if_missing(
        connection,
        table_name="publish_jobs",
        column_name="idempotency_key",
        column_sql="idempotency_key VARCHAR(64)",
    )

    rows = connection.execute(
        text(
            "SELECT id, draft_variant_id, channel, scheduled_for, created_at, idempotency_key "
            "FROM publish_jobs ORDER BY id"
        )
    ).mappings()
    for row in rows:
        if not _is_missing_scalar(row["idempotency_key"]):
            continue

        updates = {
            "idempotency_key": _build_migrated_publish_job_idempotency_key(row),
        }
        _update_row(connection, table_name="publish_jobs", row_id=int(row["id"]), values=updates)


def _ensure_sqlite_unique_indexes(connection: Connection) -> None:
    for table_name, required_constraints in _REQUIRED_UNIQUE_CONSTRAINTS.items():
        if not _table_exists(connection, table_name):
            continue
        actual_unique_names = _collect_unique_names(inspect(connection), table_name)
        for unique_name in sorted(required_constraints - actual_unique_names):
            statement = _SQLITE_REQUIRED_UNIQUE_INDEX_STATEMENTS[(table_name, unique_name)]
            connection.execute(text(statement))

    for table_name, required_indexes in _REQUIRED_UNIQUE_INDEXES.items():
        if not _table_exists(connection, table_name):
            continue
        actual_indexes = {
            index["name"]
            for index in inspect(connection).get_indexes(table_name)
            if index.get("name") and index.get("unique")
        }
        for index_name in sorted(required_indexes - actual_indexes):
            statement = _SQLITE_REQUIRED_UNIQUE_INDEX_STATEMENTS[(table_name, index_name)]
            connection.execute(text(statement))


def _ensure_schema_migrations_table(connection: Connection) -> None:
    connection.execute(
        text(
            f"""
            CREATE TABLE IF NOT EXISTS {_SCHEMA_MIGRATIONS_TABLE} (
                version INTEGER PRIMARY KEY,
                description TEXT NOT NULL,
                applied_at DATETIME NOT NULL
            )
            """
        )
    )


def _record_schema_migration(connection: Connection, *, version: int, description: str) -> None:
    existing_version = connection.execute(
        text(
            f"SELECT version FROM {_SCHEMA_MIGRATIONS_TABLE} "
            "WHERE version = :version"
        ),
        {"version": version},
    ).scalar_one_or_none()
    if existing_version is not None:
        return

    connection.execute(
        text(
            f"""
            INSERT INTO {_SCHEMA_MIGRATIONS_TABLE} (version, description, applied_at)
            VALUES (:version, :description, :applied_at)
            """
        ),
        {
            "version": version,
            "description": description,
            "applied_at": datetime.now(timezone.utc).isoformat(),
        },
    )


def _add_column_if_missing(
    connection: Connection,
    *,
    table_name: str,
    column_name: str,
    column_sql: str,
) -> bool:
    if column_name in _get_column_names(connection, table_name):
        return False

    connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}"))
    return True


def _get_column_names(connection: Connection, table_name: str) -> set[str]:
    return {column["name"] for column in inspect(connection).get_columns(table_name)}


def _table_exists(connection: Connection, table_name: str) -> bool:
    return table_name in set(inspect(connection).get_table_names())


def _collect_unique_names(inspector, table_name: str) -> set[str]:
    constraint_names = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints(table_name)
        if constraint.get("name")
    }
    unique_index_names = {
        index["name"]
        for index in inspector.get_indexes(table_name)
        if index.get("name") and index.get("unique")
    }
    return constraint_names | unique_index_names


def _update_row(
    connection: Connection,
    *,
    table_name: str,
    row_id: int,
    values: dict[str, object],
) -> None:
    assignments = ", ".join(f"{column_name} = :{column_name}" for column_name in values)
    parameters = dict(values)
    parameters["row_id"] = row_id
    connection.execute(
        text(f"UPDATE {table_name} SET {assignments} WHERE id = :row_id"),
        parameters,
    )


def _build_migrated_publish_job_idempotency_key(row) -> str:
    from app.storage.repositories import build_publish_job_idempotency_key

    scheduled_for = _coerce_utc_datetime(row["scheduled_for"])
    if scheduled_for is not None:
        return build_publish_job_idempotency_key(
            draft_variant_id=int(row["draft_variant_id"]),
            channel=str(row["channel"]),
            scheduled_for=scheduled_for,
        )

    fallback_raw = (
        f"{row['id']}:{row['draft_variant_id']}:{row['channel']}:"
        f"{row['scheduled_for'] or row['created_at'] or 'unscheduled'}"
    )
    return hashlib.sha256(fallback_raw.encode("utf-8")).hexdigest()


def _coerce_utc_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _clean_optional_text(value: object) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _is_missing_scalar(value: object) -> bool:
    if value is None:
        return True
    return isinstance(value, str) and not value.strip()


def _is_missing_json_array(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        stripped = value.strip()
        return stripped in {"", "[]", "null"}
    if isinstance(value, (list, tuple)):
        return len(value) == 0
    return False


def _is_sqlite_engine(engine: Engine) -> bool:
    return engine.dialect.name == "sqlite"
