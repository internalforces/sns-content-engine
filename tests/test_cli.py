"""Tests for the bootstrap CLI commands."""

from datetime import datetime, timezone
from pathlib import Path

import app.cli as cli_module
from sqlalchemy import inspect
from sqlalchemy.engine import create_engine
from typer.testing import CliRunner

from app import __version__
from app.cli import app
from app.domain import DuplicateReason, SourceDiscoveryFailure, SourceItemCandidate
from app.scheduler import BackfillResult, PublishDueOutcome, PublishDueResult, SchedulerDiscoverResult
from app.storage import DatabaseSchemaError, DraftVariantState, PublishJobState, ReviewActionType
from app.workflows import (
    BuildContentBriefOutcome,
    BuildContentBriefsResult,
    DiscoverSourcesResult,
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


def test_healthcheck_command_reports_ok_status() -> None:
    result = runner.invoke(app, ["healthcheck"])

    assert result.exit_code == 0
    assert result.stdout.strip() == "status=ok"


def test_db_init_command_bootstraps_the_database(tmp_path: Path) -> None:
    database_path = tmp_path / "cli.db"
    database_url = f"sqlite+pysqlite:///{database_path}"

    result = runner.invoke(app, ["db", "init", "--database-url", database_url])

    assert result.exit_code == 0
    assert result.stdout.strip() == f"database initialized: {database_url}"

    engine = create_engine(database_url)
    try:
        assert set(inspect(engine).get_table_names()) == {
            "content_briefs",
            "draft_variants",
            "publish_jobs",
            "publish_logs",
            "review_actions",
            "source_item_recent_fingerprint_claims",
            "source_items",
        }
    finally:
        engine.dispose()


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
    assert "no x channel: 0" in result.stdout
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
    monkeypatch.setattr(
        cli_module,
        "publish_due_jobs",
        lambda database_url=None: PublishDueResult(
            outcomes=(
                PublishDueOutcome(
                    publish_job_id=42,
                    status="published",
                    state=PublishJobState.PUBLISHED,
                    message="published successfully",
                    external_post_id="dry-run:42",
                ),
            ),
            dry_run=True,
        ),
    )

    result = runner.invoke(app, ["scheduler", "publish-due"])

    assert result.exit_code == 0
    assert "processed due jobs: 1 (published=1, failed=0, skipped=0)" in result.stdout
    assert "executor mode: fake dry-run" in result.stdout


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
    assert "scheduler registered jobs: discover, backfill, publish_due" in result.stdout


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


def test_help_command_is_available() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Usage" in result.stdout
    assert "db" in result.stdout
    assert "build-briefs" in result.stdout
    assert "discover" in result.stdout
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
