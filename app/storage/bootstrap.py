"""Database bootstrap helpers."""

from __future__ import annotations

from sqlalchemy import inspect
from sqlalchemy.engine import Engine

from app.storage.database import Base, create_database_engine, resolve_database_url
import app.storage.models  # noqa: F401

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

    for table_name, required_indexes in sorted(_REQUIRED_UNIQUE_INDEXES.items()):
        actual_indexes = {
            index["name"]
            for index in inspector.get_indexes(table_name)
            if index.get("name") and index.get("unique")
        }
        missing_indexes = sorted(required_indexes - actual_indexes)
        if missing_indexes:
            mismatches.append(f"{table_name}: missing unique indexes {', '.join(missing_indexes)}")

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
