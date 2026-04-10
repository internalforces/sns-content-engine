"""Tests for the bootstrap CLI commands."""

from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent

import app.cli as cli_module
from sqlalchemy import inspect
from sqlalchemy.engine import create_engine
from typer.testing import CliRunner

from app import __version__
from app.cli import app
from app.connectors.llm import DraftGenerationProviderError
from app.config import ConfigValidationError
from app.domain import DuplicateReason, SourceDiscoveryFailure, SourceItemCandidate
from app.scheduler import BackfillResult, PublishDueOutcome, PublishDueResult, SchedulerDiscoverResult
from app.storage import (
    DatabaseSchemaError,
    DraftVariantState,
    PipelineStage,
    PublishJobState,
    ReviewActionType,
)
from app.workflows import (
    BuildContentBriefOutcome,
    BuildContentBriefsResult,
    DiscoverSourcesResult,
    EnrichArticleOutcome,
    EnrichArticlesResult,
    GenerateDraftOutcome,
    GenerateDraftsResult,
    IngestSourcesResult,
    PendingReviewDraft,
    PendingReviewDraftsResult,
    ReviewDraftResult,
    ReviewQueueError,
    SourceIngestOutcome,
)

runner = CliRunner()


def test_version_command_outputs_application_version() -> None:
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert result.stdout.strip() == f"sns-content-engine {__version__}"


def test_healthcheck_command_reports_ok_status(tmp_path: Path) -> None:
    _write_minimal_project_config(tmp_path)
    database_url = f"sqlite+pysqlite:///{tmp_path / 'healthcheck-ok.db'}"
    init_result = runner.invoke(app, ["db", "init", "--database-url", database_url])

    assert init_result.exit_code == 0

    result = runner.invoke(
        app,
        ["healthcheck", "--config-dir", str(tmp_path), "--database-url", database_url],
    )

    assert result.exit_code == 0
    assert "event=healthcheck component=cli status=ok check_count=3 failed_check_count=0" in result.stdout
    assert "event=healthcheck component=cli status=ok check=config" in result.stdout
    assert "event=healthcheck component=cli status=ok check=config_readiness" in result.stdout
    assert "event=healthcheck component=cli status=ok check=database" in result.stdout
    assert "database_backend=sqlite" in result.stdout
    assert database_url not in result.stdout


def test_healthcheck_command_reports_config_failure_and_database_success(tmp_path: Path) -> None:
    _write_minimal_project_config(tmp_path)
    (tmp_path / "prompts.yaml").write_text("profiles: []\n", encoding="utf-8")
    database_url = f"sqlite+pysqlite:///{tmp_path / 'healthcheck-config.db'}"
    init_result = runner.invoke(app, ["db", "init", "--database-url", database_url])

    assert init_result.exit_code == 0

    result = runner.invoke(
        app,
        ["healthcheck", "--config-dir", str(tmp_path), "--database-url", database_url],
    )

    assert result.exit_code == 1
    assert "event=healthcheck component=cli status=failed check_count=2 failed_check_count=1" in result.output
    assert "event=healthcheck component=cli status=failed check=config" in result.output
    assert "event=healthcheck component=cli status=ok check=database" in result.output


def test_healthcheck_command_reports_missing_database_schema(tmp_path: Path) -> None:
    _write_minimal_project_config(tmp_path)
    database_path = tmp_path / "healthcheck-missing.db"
    database_url = f"sqlite+pysqlite:///{database_path}"
    assert database_path.exists() is False

    result = runner.invoke(
        app,
        ["healthcheck", "--config-dir", str(tmp_path), "--database-url", database_url],
    )

    assert result.exit_code == 1
    assert "event=healthcheck component=cli status=failed check=database" in result.output
    assert "database file does not exist" in result.output
    assert "Run `sns-engine db init` against a fresh database." in result.output
    assert database_path.exists() is False


def test_healthcheck_command_reports_outdated_database_schema(tmp_path: Path) -> None:
    _write_minimal_project_config(tmp_path)
    database_url = f"sqlite+pysqlite:///{tmp_path / 'healthcheck-outdated.db'}"
    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                """
                CREATE TABLE source_items (
                    id INTEGER PRIMARY KEY,
                    source_key VARCHAR(100) NOT NULL,
                    external_id VARCHAR(255) NOT NULL,
                    source_url VARCHAR(2048) NOT NULL,
                    title VARCHAR(500),
                    summary TEXT,
                    published_at DATETIME,
                    raw_payload JSON,
                    canonical_url VARCHAR(2048),
                    dedupe_fingerprint VARCHAR(64),
                    normalized_title VARCHAR(500),
                    normalized_title_hash VARCHAR(64),
                    state VARCHAR(32) NOT NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                )
                """
            )
    finally:
        engine.dispose()

    result = runner.invoke(
        app,
        ["healthcheck", "--config-dir", str(tmp_path), "--database-url", database_url],
    )

    assert result.exit_code == 1
    assert "event=healthcheck component=cli status=failed check=database" in result.output
    assert "missing required tables" in result.output
    assert "Run `sns-engine db upgrade`" in result.output


def test_healthcheck_command_reports_placeholder_config_not_ready(tmp_path: Path) -> None:
    _write_minimal_project_config(tmp_path, source_url="https://example.com/feed.xml")
    database_url = f"sqlite+pysqlite:///{tmp_path / 'healthcheck-placeholder.db'}"
    init_result = runner.invoke(app, ["db", "init", "--database-url", database_url])

    assert init_result.exit_code == 0

    result = runner.invoke(
        app,
        ["healthcheck", "--config-dir", str(tmp_path), "--database-url", database_url],
    )

    assert result.exit_code == 1
    assert "event=healthcheck component=cli status=failed check=config_readiness" in result.output
    assert "placeholder URLs detected" in result.output
    assert "sources.ai_tools_rss.url (example.com)" in result.output


def test_db_init_command_bootstraps_the_database(tmp_path: Path) -> None:
    database_path = tmp_path / "cli.db"
    database_url = f"sqlite+pysqlite:///{database_path}"

    result = runner.invoke(app, ["db", "init", "--database-url", database_url])

    assert result.exit_code == 0
    assert result.stdout.strip() == f"database initialized: {database_url}"

    engine = create_engine(database_url)
    try:
        assert set(inspect(engine).get_table_names()) == {
            "article_enrichments",
            "content_briefs",
            "draft_variants",
            "pipeline_runs",
            "pipeline_run_stages",
            "publish_jobs",
            "publish_logs",
            "review_actions",
            "schema_migrations",
            "source_item_recent_fingerprint_claims",
            "source_items",
        }
    finally:
        engine.dispose()


def test_db_upgrade_command_upgrades_legacy_sqlite_database(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'cli-upgrade.db'}"
    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            _create_legacy_upgrade_fixture(connection)
    finally:
        engine.dispose()

    result = runner.invoke(app, ["db", "upgrade", "--database-url", database_url])

    assert result.exit_code == 0
    assert result.stdout.strip() == f"database upgraded: {database_url} (schema_version=1->2)"

    engine = create_engine(database_url)
    try:
        assert "schema_migrations" in set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_db_upgrade_command_reports_current_schema(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'cli-upgrade-current.db'}"
    init_result = runner.invoke(app, ["db", "init", "--database-url", database_url])

    assert init_result.exit_code == 0

    result = runner.invoke(app, ["db", "upgrade", "--database-url", database_url])

    assert result.exit_code == 0
    assert result.stdout.strip() == f"database already current: {database_url} (schema_version=2)"


def test_discover_command_reports_summary(monkeypatch) -> None:
    monkeypatch.setattr(
        cli_module,
        "discover_sources",
        lambda _config_dir: DiscoverSourcesResult(
            items=(
                SourceItemCandidate(
                    source_id="ai_tools_rss",
                    external_id="entry-1",
                    source_url="https://example.com/posts/1",
                    title="First AI Tool",
                ),
                SourceItemCandidate(
                    source_id="ai_tools_manual",
                    external_id="csv-1",
                    source_url="https://example.com/manual/1",
                    title="Manual Discovery",
                ),
            ),
            failures=(),
            processed_sources=("ai_tools_manual", "ai_tools_rss"),
        ),
    )

    result = runner.invoke(app, ["discover"])

    assert result.exit_code == 0
    assert "discovered 2 source item candidates from 2 sources" in result.stdout
    assert "ai_tools_manual: 1" in result.stdout
    assert "ai_tools_rss: 1" in result.stdout


def test_discover_command_exits_nonzero_when_failures_are_present(monkeypatch) -> None:
    monkeypatch.setattr(
        cli_module,
        "discover_sources",
        lambda _config_dir: DiscoverSourcesResult(
            items=(),
            failures=(
                SourceDiscoveryFailure(
                    source_id="ai_tools_sitemap",
                    stage="fetch",
                    message="timeout",
                ),
            ),
            processed_sources=("ai_tools_sitemap",),
        ),
    )

    result = runner.invoke(app, ["discover"])

    assert result.exit_code == 1
    assert "failures:" in result.output
    assert "ai_tools_sitemap [fetch] timeout" in result.output


def test_ingest_command_reports_saved_and_duplicate_counts(monkeypatch) -> None:
    monkeypatch.setattr(
        cli_module,
        "ingest_sources",
        lambda _config_dir, database_url=None: IngestSourcesResult(
            outcomes=(
                SourceIngestOutcome(
                    candidate=SourceItemCandidate(
                        source_id="ai_tools_rss",
                        external_id="entry-1",
                        source_url="https://example.com/posts/1",
                        title="Fresh item",
                    ),
                    status="saved",
                    source_item_id=1,
                ),
                SourceIngestOutcome(
                    candidate=SourceItemCandidate(
                        source_id="ai_tools_rss",
                        external_id="entry-2",
                        source_url="https://example.com/posts/2",
                        title="Duplicate item",
                    ),
                    status="duplicate",
                    duplicate_reason=DuplicateReason.CANONICAL_URL,
                    matched_item_id=9,
                ),
            ),
            failures=(),
            processed_sources=("ai_tools_rss",),
        ),
    )

    result = runner.invoke(app, ["ingest"])

    assert result.exit_code == 0
    assert "processed 2 discovered candidates from 1 sources" in result.stdout
    assert "saved: 1" in result.stdout
    assert "duplicates blocked: 1" in result.stdout
    assert "duplicates[canonical_url]: 1" in result.stdout


def test_ingest_command_surfaces_schema_errors_cleanly(monkeypatch) -> None:
    monkeypatch.setattr(
        cli_module,
        "ingest_sources",
        lambda _config_dir, database_url=None: (_ for _ in ()).throw(
            DatabaseSchemaError("database schema is outdated")
        ),
    )

    result = runner.invoke(app, ["ingest"])

    assert result.exit_code == 1
    assert "database schema is outdated" in result.output


def test_enrich_articles_command_reports_summary(monkeypatch) -> None:
    monkeypatch.setattr(
        cli_module,
        "enrich_articles",
        lambda _config_dir, database_url=None: EnrichArticlesResult(
            processed_source_item_ids=(1, 2, 3, 4),
            outcomes=(
                EnrichArticleOutcome(source_item_id=1, status="enriched", article_enrichment_id=10),
                EnrichArticleOutcome(source_item_id=2, status="existing", article_enrichment_id=11),
                EnrichArticleOutcome(source_item_id=3, status="skipped", article_enrichment_id=12),
                EnrichArticleOutcome(
                    source_item_id=4,
                    status="failed",
                    article_enrichment_id=13,
                    failure_code="fetch_blocked",
                    failure_stage=PipelineStage.HTML_FETCH,
                ),
            ),
        ),
    )

    result = runner.invoke(app, ["enrich-articles"])

    assert result.exit_code == 0
    assert "processed 4 ingested source items" in result.stdout
    assert "enriched: 1" in result.stdout
    assert "existing: 1" in result.stdout
    assert "skipped: 1" in result.stdout
    assert "failed: 1" in result.stdout
    assert "failures[html_fetch]: 1" in result.stdout


def test_enrich_articles_command_surfaces_schema_errors_cleanly(monkeypatch) -> None:
    monkeypatch.setattr(
        cli_module,
        "enrich_articles",
        lambda _config_dir, database_url=None: (_ for _ in ()).throw(
            DatabaseSchemaError("database schema is outdated")
        ),
    )

    result = runner.invoke(app, ["enrich-articles"])

    assert result.exit_code == 1
    assert "database schema is outdated" in result.output


def test_build_briefs_command_reports_summary(monkeypatch) -> None:
    monkeypatch.setattr(
        cli_module,
        "build_content_briefs",
        lambda _config_dir, database_url=None: BuildContentBriefsResult(
            processed_source_item_ids=(1, 2, 3),
            outcomes=(
                BuildContentBriefOutcome(
                    source_item_id=1,
                    status="created",
                    account_key="ai_tools_daily",
                    content_brief_id=10,
                ),
                BuildContentBriefOutcome(
                    source_item_id=2,
                    status="existing",
                    account_key="ai_tools_daily",
                    content_brief_id=11,
                ),
                BuildContentBriefOutcome(
                    source_item_id=3,
                    status="no_match",
                ),
            ),
        ),
    )

    result = runner.invoke(app, ["build-briefs"])

    assert result.exit_code == 0
    assert "processed 3 ingested source items" in result.stdout
    assert "briefs created: 1" in result.stdout
    assert "briefs existing: 1" in result.stdout
    assert "no match: 1" in result.stdout


def test_build_briefs_command_surfaces_schema_errors_cleanly(monkeypatch) -> None:
    monkeypatch.setattr(
        cli_module,
        "build_content_briefs",
        lambda _config_dir, database_url=None: (_ for _ in ()).throw(
            DatabaseSchemaError("database schema is outdated")
        ),
    )

    result = runner.invoke(app, ["build-briefs"])

    assert result.exit_code == 1
    assert "database schema is outdated" in result.output


def test_history_runs_command_outputs_recent_runs(monkeypatch) -> None:
    monkeypatch.setattr(
        cli_module,
        "list_pipeline_runs",
        lambda database_url=None, limit=20: type(
            "RunsResult",
            (),
            {
                "runs": (
                    type(
                        "RunRow",
                        (),
                        {
                            "run_id": 5,
                            "status": "partial",
                            "discovered_count": 4,
                            "saved_count": 3,
                            "enriched_count": 2,
                            "brief_count": 2,
                            "draft_count": 6,
                            "failure_count": 1,
                            "policy_mode_counts": {
                                "discovery_only": 1,
                                "reusable": 2,
                            },
                            "policy_skipped_count": 1,
                            "attribution_required_count": 2,
                            "rewrite_providers": ("codex_wrapper", "fake"),
                        },
                    )(),
                )
            },
        )(),
    )

    result = runner.invoke(app, ["history", "runs"])

    assert result.exit_code == 0
    assert (
        "run_id=5 status=partial discovered=4 saved=3 enriched=2 briefs=2 drafts=6 "
        "failures=1 policy_skipped=1 attribution_required=2 "
        "policy_modes=discovery_only:1,reusable:2 rewrite_providers=codex_wrapper,fake"
        in result.stdout
    )



def test_history_failures_command_outputs_readable_failures(monkeypatch) -> None:
    monkeypatch.setattr(
        cli_module,
        "list_pipeline_failures",
        lambda database_url=None, limit=20: type(
            "FailuresResult",
            (),
            {
                "failures": (
                    type(
                        "FailureRow",
                        (),
                        {
                            "source_item_id": 9,
                            "failure_stage": "html_fetch",
                            "failure_code": "fetch_blocked",
                            "source_policy_mode": "restricted",
                            "require_attribution": True,
                            "failure_message": "사이트 접근이 차단되었어요",
                        },
                    )(),
                ),
                "policy_skips": (
                    type(
                        "PolicySkipRow",
                        (),
                        {
                            "source_item_id": 12,
                            "skipped_stage": "html_fetch",
                            "source_policy_mode": "discovery_only",
                            "require_attribution": True,
                            "policy_decision_reason": "Source policy blocks full-text fetch for this item.",
                        },
                    )(),
                ),
            },
        )(),
    )

    result = runner.invoke(app, ["history", "failures"])

    assert result.exit_code == 0
    assert (
        "type=failure source_item_id=9 stage=html_fetch code=fetch_blocked "
        "policy_mode=restricted attribution_required=true message=사이트 접근이 차단되었어요"
        in result.stdout
    )
    assert (
        "type=policy_skip source_item_id=12 stage=html_fetch policy_mode=discovery_only "
        "attribution_required=true reason=Source policy blocks full-text fetch for this item."
        in result.stdout
    )


def test_run_local_command_reports_pipeline_summary(monkeypatch) -> None:
    from app.storage import PipelineRunStatus

    monkeypatch.setattr(
        cli_module,
        "run_local_pipeline",
        lambda _config_dir, database_url=None: type(
            "RunLocalResult",
            (),
            {
                "pipeline_run_id": 77,
                "status": PipelineRunStatus.PARTIAL,
                "ingest_discovered_count": 6,
                "ingest_saved_count": 4,
                "duplicate_count": 2,
                "duplicate_reasons": (("source_identity", 2),),
                "enrichment_enriched_count": 3,
                "brief_created_count": 3,
                "draft_created_variant_count": 9,
                "failure_count": 1,
            },
        )(),
    )

    result = runner.invoke(app, ["run-local"])

    assert result.exit_code == 0
    assert "pipeline run id: 77" in result.stdout
    assert "status: partial" in result.stdout
    assert "discovered: 6" in result.stdout
    assert "saved: 4" in result.stdout
    assert "duplicates blocked: 2" in result.stdout
    assert "duplicates[source_identity]: 2" in result.stdout
    assert "enriched: 3" in result.stdout
    assert "briefs created: 3" in result.stdout
    assert "draft variants created: 9" in result.stdout
    assert "failures: 1" in result.stdout


def test_generate_drafts_command_reports_summary(monkeypatch) -> None:
    monkeypatch.setattr(
        cli_module,
        "generate_drafts",
        lambda _config_dir, database_url=None, variant_count=3: GenerateDraftsResult(
            processed_content_brief_ids=(10, 11),
            outcomes=(
                GenerateDraftOutcome(
                    content_brief_id=10,
                    status="created",
                    channel="x",
                    draft_variant_ids=(101, 102, 103),
                ),
                GenerateDraftOutcome(
                    content_brief_id=11,
                    status="existing",
                    channel="x",
                ),
            ),
        ),
    )

    result = runner.invoke(app, ["generate-drafts"])

    assert result.exit_code == 0
    assert "processed 2 content briefs" in result.stdout
    assert "draft sets created: 1" in result.stdout
    assert "draft sets existing: 1" in result.stdout
    assert "no configured channel: 0" in result.stdout
    assert "missing account: 0" in result.stdout
    assert "draft variants created: 3" in result.stdout


def test_generate_drafts_command_surfaces_schema_errors_cleanly(monkeypatch) -> None:
    monkeypatch.setattr(
        cli_module,
        "generate_drafts",
        lambda _config_dir, database_url=None, variant_count=3: (_ for _ in ()).throw(
            DatabaseSchemaError("database schema is outdated")
        ),
    )

    result = runner.invoke(app, ["generate-drafts"])

    assert result.exit_code == 1
    assert "database schema is outdated" in result.output


def test_generate_drafts_command_surfaces_provider_errors_cleanly(monkeypatch) -> None:
    monkeypatch.setattr(
        cli_module,
        "generate_drafts",
        lambda _config_dir, database_url=None, variant_count=3: (_ for _ in ()).throw(
            DraftGenerationProviderError("OpenAI draft generation request failed: boom")
        ),
    )

    result = runner.invoke(app, ["generate-drafts"])

    assert result.exit_code == 1
    assert "OpenAI draft generation request failed: boom" in result.output


def test_generate_drafts_command_rejects_invalid_variant_count() -> None:
    result = runner.invoke(app, ["generate-drafts", "--variant-count", "4"])

    assert result.exit_code == 2
    assert "--variant-count" in result.output


def test_review_list_command_reports_pending_drafts(monkeypatch) -> None:
    monkeypatch.setattr(
        cli_module,
        "list_pending_review_drafts",
        lambda database_url=None: PendingReviewDraftsResult(
            drafts=(
                PendingReviewDraft(
                    draft_id=42,
                    account_key="ai_tools_daily",
                    channel="x",
                    variant_index=0,
                    created_at=datetime(2026, 3, 17, 9, 0, tzinfo=timezone.utc),
                    title="Useful AI workflow patterns",
                    body="Draft body https://gilgop.cloud/ai-tools",
                ),
            )
        ),
    )

    result = runner.invoke(app, ["review", "list"])

    assert result.exit_code == 0
    assert "pending drafts: 1" in result.stdout
    assert "draft_id: 42" in result.stdout
    assert "account_key: ai_tools_daily" in result.stdout
    assert "body: Draft body https://gilgop.cloud/ai-tools" in result.stdout


def test_review_approve_command_reports_success(monkeypatch) -> None:
    monkeypatch.setattr(
        cli_module,
        "approve_draft",
        lambda draft_id, reviewer=None, config_dir=None, database_url=None: ReviewDraftResult(
            draft_id=draft_id,
            reviewer=reviewer or "ops-user",
            action_type=ReviewActionType.APPROVE,
            draft_state=DraftVariantState.APPROVED,
            action_id=1001,
        ),
    )

    result = runner.invoke(app, ["review", "approve", "42", "--reviewer", "ops-user"])

    assert result.exit_code == 0
    assert result.stdout.strip() == "approved draft 42 as ops-user"


def test_review_schedule_command_surfaces_workflow_errors(monkeypatch) -> None:
    monkeypatch.setattr(
        cli_module,
        "schedule_draft",
        lambda draft_id, scheduled_for, reviewer=None, config_dir=None, database_url=None: (_ for _ in ()).throw(
            ReviewQueueError("scheduled_for must include a timezone offset")
        ),
    )

    result = runner.invoke(
        app,
        ["review", "schedule", "42", "--scheduled-for", "2026-03-18T09:00:00"],
    )

    assert result.exit_code == 1
    assert "scheduled_for must include a timezone offset" in result.output


def test_scheduler_discover_command_reports_summary(monkeypatch) -> None:
    monkeypatch.setattr(
        cli_module,
        "scheduler_discover",
        lambda config_dir=None: SchedulerDiscoverResult(
            discovered_count=2,
            processed_sources=("ai_tools_manual", "ai_tools_rss"),
            failure_messages=(),
        ),
    )

    result = runner.invoke(app, ["scheduler", "discover"])

    assert result.exit_code == 0
    assert "scheduler discover found 2 item candidates from 2 sources" in result.stdout


def test_scheduler_backfill_command_reports_summary(monkeypatch) -> None:
    monkeypatch.setattr(
        cli_module,
        "backfill_publish_jobs",
        lambda config_dir=None, database_url=None: BackfillResult(outcomes=()),
    )

    result = runner.invoke(app, ["scheduler", "backfill"])

    assert result.exit_code == 0
    assert "processed backlog channels: 0" in result.stdout
    assert "existing future jobs: 0" in result.stdout
    assert "created jobs: 0" in result.stdout
    assert "skipped slots: 0" in result.stdout


def test_scheduler_publish_due_command_reports_dry_run_summary(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_publish_due_jobs(
        config_dir=None,
        database_url=None,
        dry_run=True,
        publisher_resolver=None,
        executor=None,
    ):
        captured["config_dir"] = config_dir
        captured["database_url"] = database_url
        captured["dry_run"] = dry_run
        return PublishDueResult(
            outcomes=(
                PublishDueOutcome(
                    publish_job_id=42,
                    status="dry_run",
                    state=PublishJobState.SCHEDULED,
                    message="dry-run only; no state changes were applied",
                    external_post_id="dry-run:42",
                ),
            ),
            dry_run=True,
        )

    monkeypatch.setattr(
        cli_module,
        "publish_due_jobs",
        fake_publish_due_jobs,
    )

    result = runner.invoke(app, ["scheduler", "publish-due"])

    assert result.exit_code == 0
    assert captured["dry_run"] is True
    assert "processed due jobs: 1 (dry_run=1, failed=0, skipped=0)" in result.stdout
    assert "executor mode: fake dry-run (no state changes)" in result.stdout


def test_scheduler_publish_due_command_live_mode_reports_summary(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_publish_due_jobs(
        config_dir=None,
        database_url=None,
        dry_run=True,
        publisher_resolver=None,
        executor=None,
    ):
        captured["config_dir"] = config_dir
        captured["database_url"] = database_url
        captured["dry_run"] = dry_run
        return PublishDueResult(
            outcomes=(
                PublishDueOutcome(
                    publish_job_id=42,
                    status="published",
                    state=PublishJobState.PUBLISHED,
                    message="published successfully",
                    external_post_id="tweet:42",
                ),
                PublishDueOutcome(
                    publish_job_id=43,
                    status="published",
                    state=PublishJobState.PUBLISHED,
                    message="published successfully",
                    external_post_id="tweet:43",
                ),
            ),
            dry_run=False,
        )

    monkeypatch.setattr(cli_module, "publish_due_jobs", fake_publish_due_jobs)

    result = runner.invoke(
        app,
        ["scheduler", "publish-due", "--config-dir", str(tmp_path), "--live"],
    )

    assert result.exit_code == 0
    assert captured["dry_run"] is False
    assert captured["config_dir"] == tmp_path.resolve()
    assert "processed due jobs: 2 (published=2, failed=0, skipped=0)" in result.stdout
    assert "executor mode: live publish via configured publishers" in result.stdout


def test_scheduler_publish_due_command_live_mode_exits_nonzero_when_failures_exist(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        cli_module,
        "publish_due_jobs",
        lambda config_dir=None, database_url=None, dry_run=True, publisher_resolver=None, executor=None: (
            PublishDueResult(
                outcomes=(
                    PublishDueOutcome(
                        publish_job_id=42,
                        status="published",
                        state=PublishJobState.PUBLISHED,
                        message="published successfully",
                        external_post_id="tweet:42",
                    ),
                    PublishDueOutcome(
                        publish_job_id=43,
                        status="failed",
                        state=PublishJobState.FAILED,
                        message="missing access token",
                    ),
                ),
                dry_run=False,
            )
        ),
    )

    result = runner.invoke(
        app,
        ["scheduler", "publish-due", "--config-dir", str(tmp_path), "--live"],
    )

    assert result.exit_code == 1
    assert "processed due jobs: 2 (published=1, failed=1, skipped=0)" in result.stdout
    assert "executor mode: live publish via configured publishers" in result.stdout


def test_scheduler_publish_due_command_live_mode_surfaces_config_errors_cleanly(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        cli_module,
        "publish_due_jobs",
        lambda config_dir=None, database_url=None, dry_run=True, publisher_resolver=None, executor=None: (
            _ for _ in ()
        ).throw(
            ConfigValidationError(
                path=tmp_path / "accounts.yaml",
                errors=("accounts.yaml: accounts.ai_tools_daily.channels.x.schedule.cron: invalid cron expression",),
            )
        ),
    )

    result = runner.invoke(
        app,
        ["scheduler", "publish-due", "--config-dir", str(tmp_path), "--live"],
    )

    assert result.exit_code == 1
    assert "invalid cron expression" in result.output
    assert "executor mode: fake dry-run" not in result.output
    assert "executor mode: live publish via configured publishers" not in result.output


def test_scheduler_run_command_registers_jobs_and_starts_runtime(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeScheduler:
        def start(self) -> None:
            captured["started"] = True

    def fake_build_scheduler_runtime(**kwargs):
        captured.update(kwargs)
        return FakeScheduler()

    monkeypatch.setattr(cli_module, "build_scheduler_runtime", fake_build_scheduler_runtime)

    result = runner.invoke(app, ["scheduler", "run"])

    assert result.exit_code == 0
    assert captured["discover_interval_minutes"] == 30
    assert captured["backfill_interval_minutes"] == 15
    assert captured["publish_due_interval_seconds"] == 60
    assert captured["started"] is True
    assert "scheduler registered jobs: run_local, backfill, publish_due" in result.stdout
    assert "dry_run=true" in result.stdout


def test_db_init_command_surfaces_schema_errors_cleanly(monkeypatch) -> None:
    monkeypatch.setattr(
        cli_module,
        "bootstrap_database",
        lambda database_url=None: (_ for _ in ()).throw(
            DatabaseSchemaError("database schema is outdated")
        ),
    )

    result = runner.invoke(app, ["db", "init"])

    assert result.exit_code == 1
    assert "database schema is outdated" in result.output


def test_db_upgrade_command_surfaces_schema_errors_cleanly(monkeypatch) -> None:
    monkeypatch.setattr(
        cli_module,
        "upgrade_database_schema",
        lambda database_url=None: (_ for _ in ()).throw(
            DatabaseSchemaError("database schema upgrade failed")
        ),
    )

    result = runner.invoke(app, ["db", "upgrade"])

    assert result.exit_code == 1
    assert "database schema upgrade failed" in result.output


def test_help_command_is_available() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Usage" in result.stdout
    assert "db" in result.stdout
    assert "build-briefs" in result.stdout
    assert "discover" in result.stdout
    assert "enrich-articles" in result.stdout
    assert "generate-drafts" in result.stdout
    assert "ingest" in result.stdout
    assert "review" in result.stdout
    assert "scheduler" in result.stdout


def test_main_runs_the_typer_app(monkeypatch) -> None:
    called = False

    def fake_app() -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(cli_module, "app", fake_app)

    cli_module.main()

    assert called is True


def _create_legacy_upgrade_fixture(connection) -> None:
    connection.exec_driver_sql(
        """
        CREATE TABLE source_items (
            id INTEGER PRIMARY KEY,
            source_key VARCHAR(100) NOT NULL,
            external_id VARCHAR(255) NOT NULL,
            source_url VARCHAR(2048) NOT NULL,
            title VARCHAR(500) NOT NULL,
            summary TEXT,
            published_at DATETIME,
            raw_payload JSON,
            state VARCHAR(32) NOT NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        )
        """
    )
    connection.exec_driver_sql(
        """
        INSERT INTO source_items (
            id,
            source_key,
            external_id,
            source_url,
            title,
            summary,
            published_at,
            raw_payload,
            state,
            created_at,
            updated_at
        ) VALUES (
            1,
            'legacy_feed',
            'legacy-1',
            'https://example.com/posts/legacy?utm_source=newsletter',
            'Legacy AI update',
            'Legacy summary',
            '2026-03-18T09:00:00+00:00',
            '{}',
            'INGESTED',
            '2026-03-18T09:05:00+00:00',
            '2026-03-18T09:05:00+00:00'
        )
        """
    )
    connection.exec_driver_sql(
        """
        CREATE TABLE pipeline_runs (
            id INTEGER PRIMARY KEY,
            workflow_name VARCHAR(100) NOT NULL,
            trigger_mode VARCHAR(50) NOT NULL,
            status VARCHAR(32) NOT NULL,
            started_at DATETIME NOT NULL,
            completed_at DATETIME,
            source_count INTEGER NOT NULL,
            discovered_count INTEGER NOT NULL,
            saved_count INTEGER NOT NULL,
            enriched_count INTEGER NOT NULL,
            summarized_count INTEGER NOT NULL,
            draft_count INTEGER NOT NULL,
            failure_count INTEGER NOT NULL,
            latest_error_code VARCHAR(100),
            latest_error_message TEXT,
            summary_json JSON,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        )
        """
    )
    connection.exec_driver_sql(
        """
        CREATE TABLE content_briefs (
            id INTEGER PRIMARY KEY,
            source_item_id INTEGER NOT NULL,
            account_key VARCHAR(100) NOT NULL,
            title VARCHAR(500) NOT NULL,
            summary TEXT,
            landing_url VARCHAR(2048) NOT NULL,
            tags JSON NOT NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        )
        """
    )
    connection.exec_driver_sql(
        """
        INSERT INTO content_briefs (
            id,
            source_item_id,
            account_key,
            title,
            summary,
            landing_url,
            tags,
            created_at,
            updated_at
        ) VALUES (
            1,
            1,
            'ai_tools_daily',
            'Legacy AI update',
            'Legacy summary',
            'https://gilgop.cloud/ai-tools',
            '["ai"]',
            '2026-03-18T09:06:00+00:00',
            '2026-03-18T09:06:00+00:00'
        )
        """
    )
    connection.exec_driver_sql(
        """
        CREATE TABLE draft_variants (
            id INTEGER PRIMARY KEY,
            content_brief_id INTEGER NOT NULL,
            channel VARCHAR(50) NOT NULL,
            variant_index INTEGER NOT NULL,
            body TEXT NOT NULL,
            state VARCHAR(32) NOT NULL,
            rejection_reason TEXT,
            reviewed_at DATETIME,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        )
        """
    )
    connection.exec_driver_sql(
        """
        INSERT INTO draft_variants (
            id,
            content_brief_id,
            channel,
            variant_index,
            body,
            state,
            rejection_reason,
            reviewed_at,
            created_at,
            updated_at
        ) VALUES (
            1,
            1,
            'x',
            0,
            'Legacy draft body',
            'PENDING_REVIEW',
            NULL,
            NULL,
            '2026-03-18T09:07:00+00:00',
            '2026-03-18T09:07:00+00:00'
        )
        """
    )
    connection.exec_driver_sql(
        """
        CREATE TABLE publish_jobs (
            id INTEGER PRIMARY KEY,
            draft_variant_id INTEGER NOT NULL,
            channel VARCHAR(50) NOT NULL,
            scheduled_for DATETIME,
            state VARCHAR(32) NOT NULL,
            attempt_count INTEGER NOT NULL,
            external_post_id VARCHAR(255),
            last_error TEXT,
            published_at DATETIME,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        )
        """
    )
    connection.exec_driver_sql(
        """
        INSERT INTO publish_jobs (
            id,
            draft_variant_id,
            channel,
            scheduled_for,
            state,
            attempt_count,
            external_post_id,
            last_error,
            published_at,
            created_at,
            updated_at
        ) VALUES (
            1,
            1,
            'x',
            '2026-03-20T09:00:00+00:00',
            'SCHEDULED',
            0,
            NULL,
            NULL,
            NULL,
            '2026-03-18T09:08:00+00:00',
            '2026-03-18T09:08:00+00:00'
        )
        """
    )


def _write_minimal_project_config(
    path: Path,
    *,
    source_url: str = "https://gilgop.cloud/feed.xml",
) -> None:
    _write_file(
        path / "accounts.yaml",
        """
        accounts:
          ai_tools_daily:
            topic: "AI tools and workflows"
            source_sets:
              - ai_tools_primary
            prompt_profile: ai_tools_default
            landing:
              fallback_url: https://gilgop.cloud/ai-tools
              rules: []
            channels:
              x:
                schedule:
                  cron: "0 9 * * *"
                render:
                  max_chars: 280
        """,
    )
    _write_file(
        path / "prompts.yaml",
        """
        profiles:
          ai_tools_default:
            system_template: "system"
            user_template: "user"
        """,
    )
    _write_file(
        path / "sources.yaml",
        """
        sources:
          ai_tools_rss:
            type: rss
            url: {source_url}

        source_sets:
          ai_tools_primary:
            sources:
              - ai_tools_rss
        """.format(source_url=source_url),
    )


def _write_file(path: Path, content: str) -> None:
    path.write_text(dedent(content).strip() + "\n", encoding="utf-8")
