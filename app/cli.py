"""Typer CLI entrypoint for sns-content-engine."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from app import __version__
from app.connectors.llm import DraftGenerationProviderError
from app.operations import log_workflow_exception, log_workflow_result, run_healthcheck
from app.scheduler import build_scheduler_runtime, backfill_publish_jobs, publish_due_jobs, scheduler_discover
from app.storage import DatabaseSchemaError, bootstrap_database, upgrade_database_schema
from app.workflows import (
    ReviewQueueError,
    approve_draft,
    build_content_briefs,
    discover_sources,
    edit_draft,
    generate_drafts,
    ingest_sources,
    list_pending_review_drafts,
    list_pipeline_failures,
    list_pipeline_runs,
    run_local_pipeline,
    reject_draft,
    schedule_draft,
)

app = typer.Typer(
    help="Config-driven multi-account SNS content engine.",
    no_args_is_help=True,
)
db_app = typer.Typer(help="Database bootstrap and inspection commands.")
review_app = typer.Typer(help="Manual review queue commands.")
scheduler_app = typer.Typer(help="Automated scheduler commands.")
history_app = typer.Typer(help="Readable run and failure history commands.")

app.add_typer(db_app, name="db")
app.add_typer(review_app, name="review")
app.add_typer(scheduler_app, name="scheduler")
app.add_typer(history_app, name="history")


@app.command()
def version() -> None:
    """Print the application version."""
    typer.echo(f"sns-content-engine {__version__}")


@app.command()
def healthcheck(
    config_dir: Annotated[
        Path,
        typer.Option(
            "--config-dir",
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            resolve_path=True,
            help="Directory containing accounts.yaml, prompts.yaml, and sources.yaml.",
        ),
    ] = Path("config"),
    database_url: Annotated[
        str | None,
        typer.Option(
            "--database-url",
            help="Explicit database URL. Falls back to DATABASE_URL, then the project default.",
        ),
    ] = None,
) -> None:
    """Run a strict local readiness healthcheck."""

    result = run_healthcheck(config_dir=config_dir, database_url=database_url)
    for line in result.to_lines(component="cli"):
        typer.echo(line, err=not result.is_ok)
    if not result.is_ok:
        raise typer.Exit(code=1)


@app.command("discover")
def discover_command(
    config_dir: Annotated[
        Path,
        typer.Option(
            "--config-dir",
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            resolve_path=True,
            help="Directory containing accounts.yaml, prompts.yaml, and sources.yaml.",
        ),
    ] = Path("config"),
) -> None:
    """Discover normalized source item candidates from configured sources."""

    result = discover_sources(config_dir)
    typer.echo(
        "discovered "
        f"{result.item_count} source item candidates "
        f"from {len(result.processed_sources)} sources"
    )

    for source_id, count in result.counts_by_source().items():
        typer.echo(f"{source_id}: {count}")

    if result.failure_count == 0:
        return

    typer.echo("failures:", err=True)
    for failure in result.failures:
        typer.echo(f"- {failure.format_for_cli()}", err=True)

    raise typer.Exit(code=1)


@app.command("ingest")
def ingest_command(
    config_dir: Annotated[
        Path,
        typer.Option(
            "--config-dir",
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            resolve_path=True,
            help="Directory containing accounts.yaml, prompts.yaml, and sources.yaml.",
        ),
    ] = Path("config"),
    database_url: Annotated[
        str | None,
        typer.Option(
            "--database-url",
            help="Explicit database URL. Falls back to DATABASE_URL, then the project default.",
        ),
    ] = None,
) -> None:
    """Discover sources and persist only non-duplicate items."""

    try:
        result = ingest_sources(config_dir, database_url=database_url)
    except DatabaseSchemaError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(
        "processed "
        f"{result.discovered_count} discovered candidates "
        f"from {len(result.processed_sources)} sources"
    )
    typer.echo(f"saved: {result.saved_count}")
    typer.echo(f"duplicates blocked: {result.duplicate_count}")

    for reason, count in result.duplicate_counts_by_reason().items():
        typer.echo(f"duplicates[{reason}]: {count}")

    if result.failure_count == 0:
        return

    typer.echo("failures:", err=True)
    for failure in result.failures:
        typer.echo(f"- {failure.format_for_cli()}", err=True)

    raise typer.Exit(code=1)


@app.command("build-briefs")
def build_briefs_command(
    config_dir: Annotated[
        Path,
        typer.Option(
            "--config-dir",
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            resolve_path=True,
            help="Directory containing accounts.yaml, prompts.yaml, and sources.yaml.",
        ),
    ] = Path("config"),
    database_url: Annotated[
        str | None,
        typer.Option(
            "--database-url",
            help="Explicit database URL. Falls back to DATABASE_URL, then the project default.",
        ),
    ] = None,
) -> None:
    """Build platform-neutral content briefs for ingested source items."""

    try:
        result = build_content_briefs(config_dir, database_url=database_url)
    except DatabaseSchemaError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"processed {result.processed_count} ingested source items")
    typer.echo(f"briefs created: {result.created_count}")
    typer.echo(f"briefs existing: {result.existing_count}")
    typer.echo(f"no match: {result.no_match_count}")


@app.command("generate-drafts")
def generate_drafts_command(
    config_dir: Annotated[
        Path,
        typer.Option(
            "--config-dir",
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            resolve_path=True,
            help="Directory containing accounts.yaml, prompts.yaml, and sources.yaml.",
        ),
    ] = Path("config"),
    database_url: Annotated[
        str | None,
        typer.Option(
            "--database-url",
            help="Explicit database URL. Falls back to DATABASE_URL, then the project default.",
        ),
    ] = None,
    variant_count: Annotated[
        int,
        typer.Option(
            "--variant-count",
            min=2,
            max=3,
            help="Number of draft variants to generate per content brief.",
        ),
    ] = 3,
) -> None:
    """Generate X-ready draft variants for stored content briefs."""

    try:
        result = generate_drafts(
            config_dir,
            database_url=database_url,
            variant_count=variant_count,
        )
    except (DatabaseSchemaError, DraftGenerationProviderError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"processed {result.processed_count} content briefs")
    typer.echo(f"draft sets created: {result.created_count}")
    typer.echo(f"draft sets existing: {result.existing_count}")
    typer.echo(f"no x channel: {result.no_channel_count}")
    typer.echo(f"missing account: {result.missing_account_count}")
    typer.echo(f"draft variants created: {result.created_variant_count}")




@app.command("run-local")
def run_local_command(
    config_dir: Annotated[
        Path,
        typer.Option(
            "--config-dir",
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            resolve_path=True,
            help="Directory containing accounts.yaml, prompts.yaml, and sources.yaml.",
        ),
    ] = Path("config"),
    database_url: Annotated[
        str | None,
        typer.Option(
            "--database-url",
            help="Explicit database URL. Falls back to DATABASE_URL, then the project default.",
        ),
    ] = None,
) -> None:
    """Run the local discover->enrich->brief->draft workflow once."""

    try:
        result = run_local_pipeline(config_dir, database_url=database_url)
    except (DatabaseSchemaError, DraftGenerationProviderError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"pipeline run id: {result.pipeline_run_id}")
    typer.echo(f"status: {result.status.value}")
    typer.echo(f"discovered: {result.ingest_discovered_count}")
    typer.echo(f"saved: {result.ingest_saved_count}")
    typer.echo(f"enriched: {result.enrichment_enriched_count}")
    typer.echo(f"briefs created: {result.brief_created_count}")
    typer.echo(f"draft variants created: {result.draft_created_variant_count}")
    typer.echo(f"failures: {result.failure_count}")



def _format_history_run_row(row: object) -> str:
    parts = [
        f"run_id={row.run_id}",
        f"status={row.status}",
        f"discovered={row.discovered_count}",
        f"saved={row.saved_count}",
        f"enriched={row.enriched_count}",
        f"briefs={row.brief_count}",
        f"drafts={row.draft_count}",
        f"failures={row.failure_count}",
        f"policy_skipped={getattr(row, 'policy_skipped_count', 0)}",
        f"attribution_required={getattr(row, 'attribution_required_count', 0)}",
    ]
    policy_mode_counts = getattr(row, "policy_mode_counts", {}) or {}
    if policy_mode_counts:
        parts.append(
            "policy_modes="
            + ",".join(
                f"{policy_mode}:{count}"
                for policy_mode, count in sorted(policy_mode_counts.items())
            )
        )
    rewrite_providers = tuple(getattr(row, "rewrite_providers", ()) or ())
    if rewrite_providers:
        parts.append(f"rewrite_providers={','.join(rewrite_providers)}")
    return " ".join(parts)


def _format_history_failure_row(row: object) -> str:
    return " ".join(
        [
            "type=failure",
            f"source_item_id={row.source_item_id}",
            f"stage={row.failure_stage or 'unknown'}",
            f"code={row.failure_code}",
            f"policy_mode={getattr(row, 'source_policy_mode', 'unknown')}",
            f"attribution_required={_format_cli_bool(getattr(row, 'require_attribution', False))}",
            f"message={row.failure_message}",
        ]
    )


def _format_history_policy_skip_row(row: object) -> str:
    return " ".join(
        [
            "type=policy_skip",
            f"source_item_id={row.source_item_id}",
            f"stage={row.skipped_stage}",
            f"policy_mode={row.source_policy_mode}",
            f"attribution_required={_format_cli_bool(row.require_attribution)}",
            f"reason={row.policy_decision_reason}",
        ]
    )


def _format_cli_bool(value: object) -> str:
    return "true" if bool(value) else "false"


@history_app.command("runs")
def history_runs_command(
    database_url: Annotated[
        str | None,
        typer.Option(
            "--database-url",
            help="Explicit database URL. Falls back to DATABASE_URL, then the project default.",
        ),
    ] = None,
    limit: Annotated[int, typer.Option("--limit", min=1, max=100)] = 20,
) -> None:
    """List recent local pipeline runs."""

    result = list_pipeline_runs(database_url=database_url, limit=limit)
    for row in result.runs:
        typer.echo(_format_history_run_row(row))


@history_app.command("failures")
def history_failures_command(
    database_url: Annotated[
        str | None,
        typer.Option(
            "--database-url",
            help="Explicit database URL. Falls back to DATABASE_URL, then the project default.",
        ),
    ] = None,
    limit: Annotated[int, typer.Option("--limit", min=1, max=100)] = 20,
) -> None:
    """List readable pipeline failures for review or future UI screens."""

    result = list_pipeline_failures(database_url=database_url, limit=limit)
    for row in result.failures:
        typer.echo(_format_history_failure_row(row))
    for row in getattr(result, "policy_skips", ()):
        typer.echo(_format_history_policy_skip_row(row))


@review_app.command("list")
def review_list_command(
    database_url: Annotated[
        str | None,
        typer.Option(
            "--database-url",
            help="Explicit database URL. Falls back to DATABASE_URL, then the project default.",
        ),
    ] = None,
) -> None:
    """List all drafts currently awaiting manual review."""

    try:
        result = list_pending_review_drafts(database_url=database_url)
    except (DatabaseSchemaError, ReviewQueueError) as exc:
        _exit_with_error(exc)

    typer.echo(f"pending drafts: {result.pending_count}")
    for index, draft in enumerate(result.drafts):
        if index:
            typer.echo("")
        typer.echo(f"draft_id: {draft.draft_id}")
        typer.echo(f"account_key: {draft.account_key}")
        typer.echo(f"channel: {draft.channel}")
        typer.echo(f"variant_index: {draft.variant_index}")
        typer.echo(f"created_at: {draft.created_at.isoformat()}")
        typer.echo(f"title: {draft.title}")
        typer.echo(f"body: {draft.body}")


@review_app.command("approve")
def review_approve_command(
    draft_id: Annotated[int, typer.Argument(help="Draft variant id to approve.")],
    config_dir: Annotated[
        Path,
        typer.Option(
            "--config-dir",
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            resolve_path=True,
            help="Directory containing accounts.yaml, prompts.yaml, and sources.yaml.",
        ),
    ] = Path("config"),
    reviewer: Annotated[
        str | None,
        typer.Option("--reviewer", help="Reviewer identity. Falls back to USER or USERNAME."),
    ] = None,
    database_url: Annotated[
        str | None,
        typer.Option(
            "--database-url",
            help="Explicit database URL. Falls back to DATABASE_URL, then the project default.",
        ),
    ] = None,
) -> None:
    """Approve a pending draft."""

    try:
        result = approve_draft(
            draft_id,
            reviewer=reviewer,
            config_dir=config_dir,
            database_url=database_url,
        )
    except (DatabaseSchemaError, ReviewQueueError) as exc:
        _exit_with_error(exc)

    typer.echo(f"approved draft {result.draft_id} as {result.reviewer}")


@review_app.command("reject")
def review_reject_command(
    draft_id: Annotated[int, typer.Argument(help="Draft variant id to reject.")],
    reason: Annotated[
        str,
        typer.Option("--reason", help="Reason recorded with the rejection."),
    ],
    config_dir: Annotated[
        Path,
        typer.Option(
            "--config-dir",
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            resolve_path=True,
            help="Directory containing accounts.yaml, prompts.yaml, and sources.yaml.",
        ),
    ] = Path("config"),
    reviewer: Annotated[
        str | None,
        typer.Option("--reviewer", help="Reviewer identity. Falls back to USER or USERNAME."),
    ] = None,
    database_url: Annotated[
        str | None,
        typer.Option(
            "--database-url",
            help="Explicit database URL. Falls back to DATABASE_URL, then the project default.",
        ),
    ] = None,
) -> None:
    """Reject a pending draft."""

    try:
        result = reject_draft(
            draft_id,
            reason=reason,
            reviewer=reviewer,
            config_dir=config_dir,
            database_url=database_url,
        )
    except (DatabaseSchemaError, ReviewQueueError) as exc:
        _exit_with_error(exc)

    typer.echo(f"rejected draft {result.draft_id} as {result.reviewer}")


@review_app.command("edit")
def review_edit_command(
    draft_id: Annotated[int, typer.Argument(help="Draft variant id to edit.")],
    body: Annotated[
        str,
        typer.Option("--body", help="Replacement body text for the draft."),
    ],
    config_dir: Annotated[
        Path,
        typer.Option(
            "--config-dir",
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            resolve_path=True,
            help="Directory containing accounts.yaml, prompts.yaml, and sources.yaml.",
        ),
    ] = Path("config"),
    reviewer: Annotated[
        str | None,
        typer.Option("--reviewer", help="Reviewer identity. Falls back to USER or USERNAME."),
    ] = None,
    database_url: Annotated[
        str | None,
        typer.Option(
            "--database-url",
            help="Explicit database URL. Falls back to DATABASE_URL, then the project default.",
        ),
    ] = None,
) -> None:
    """Edit a pending draft in place."""

    try:
        result = edit_draft(
            draft_id,
            body=body,
            reviewer=reviewer,
            config_dir=config_dir,
            database_url=database_url,
        )
    except (DatabaseSchemaError, ReviewQueueError) as exc:
        _exit_with_error(exc)

    typer.echo(f"edited draft {result.draft_id} as {result.reviewer}")


@review_app.command("schedule")
def review_schedule_command(
    draft_id: Annotated[int, typer.Argument(help="Draft variant id to schedule.")],
    scheduled_for: Annotated[
        str,
        typer.Option(
            "--scheduled-for",
            help="Timezone-aware ISO 8601 publish time.",
        ),
    ],
    config_dir: Annotated[
        Path,
        typer.Option(
            "--config-dir",
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            resolve_path=True,
            help="Directory containing accounts.yaml, prompts.yaml, and sources.yaml.",
        ),
    ] = Path("config"),
    reviewer: Annotated[
        str | None,
        typer.Option("--reviewer", help="Reviewer identity. Falls back to USER or USERNAME."),
    ] = None,
    database_url: Annotated[
        str | None,
        typer.Option(
            "--database-url",
            help="Explicit database URL. Falls back to DATABASE_URL, then the project default.",
        ),
    ] = None,
) -> None:
    """Create a scheduled publish job for an approved draft."""

    try:
        result = schedule_draft(
            draft_id,
            scheduled_for=scheduled_for,
            reviewer=reviewer,
            config_dir=config_dir,
            database_url=database_url,
        )
    except (DatabaseSchemaError, ReviewQueueError) as exc:
        _exit_with_error(exc)

    typer.echo(
        "scheduled "
        f"draft {result.draft_id} as publish job {result.publish_job_id} "
        f"for {result.scheduled_for.isoformat() if result.scheduled_for else 'unknown'} "
        f"as {result.reviewer}"
    )


@scheduler_app.command("discover")
def scheduler_discover_command(
    config_dir: Annotated[
        Path,
        typer.Option(
            "--config-dir",
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            resolve_path=True,
            help="Directory containing accounts.yaml, prompts.yaml, and sources.yaml.",
        ),
    ] = Path("config"),
) -> None:
    """Run the scheduled discovery job once."""

    try:
        result = scheduler_discover(config_dir=config_dir)
    except Exception as exc:
        log_workflow_exception(component="cli", workflow="discover", error=exc)
        _exit_with_error(exc)

    log_workflow_result(component="cli", workflow="discover", result=result)
    typer.echo(
        "scheduler discover found "
        f"{result.discovered_count} item candidates "
        f"from {len(result.processed_sources)} sources"
    )
    if result.failure_count == 0:
        return

    typer.echo("failures:", err=True)
    for failure_message in result.failure_messages:
        typer.echo(f"- {failure_message}", err=True)
    raise typer.Exit(code=1)


@scheduler_app.command("backfill")
def scheduler_backfill_command(
    config_dir: Annotated[
        Path,
        typer.Option(
            "--config-dir",
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            resolve_path=True,
            help="Directory containing accounts.yaml, prompts.yaml, and sources.yaml.",
        ),
    ] = Path("config"),
    database_url: Annotated[
        str | None,
        typer.Option(
            "--database-url",
            help="Explicit database URL. Falls back to DATABASE_URL, then the project default.",
        ),
    ] = None,
) -> None:
    """Backfill publish jobs up to the configured backlog targets."""

    try:
        result = backfill_publish_jobs(
            config_dir=config_dir,
            database_url=database_url,
        )
    except Exception as exc:
        log_workflow_exception(component="cli", workflow="backfill", error=exc)
        _exit_with_error(exc)

    log_workflow_result(component="cli", workflow="backfill", result=result)
    typer.echo(f"processed backlog channels: {result.processed_channel_count}")
    typer.echo(f"existing future jobs: {result.existing_count}")
    typer.echo(f"created jobs: {result.created_count}")
    typer.echo(f"skipped slots: {result.skipped_count}")


@scheduler_app.command("publish-due")
def scheduler_publish_due_command(
    config_dir: Annotated[
        Path,
        typer.Option(
            "--config-dir",
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            resolve_path=True,
            help="Directory containing accounts.yaml, prompts.yaml, and sources.yaml.",
        ),
    ] = Path("config"),
    database_url: Annotated[
        str | None,
        typer.Option(
            "--database-url",
            help="Explicit database URL. Falls back to DATABASE_URL, then the project default.",
        ),
    ] = None,
    live: Annotated[
        bool,
        typer.Option(
            "--live",
            help="Execute live publishing with configured publisher credentials instead of dry-run mode.",
        ),
    ] = False,
) -> None:
    """Process due publish jobs, defaulting to dry-run unless --live is passed."""

    try:
        result = publish_due_jobs(
            config_dir=config_dir,
            database_url=database_url,
            dry_run=not live,
        )
    except Exception as exc:
        log_workflow_exception(component="cli", workflow="publish_due", error=exc)
        _exit_with_error(exc)

    log_workflow_result(component="cli", workflow="publish_due", result=result)
    if result.dry_run:
        typer.echo(
            f"processed due jobs: {result.processed_count} "
            f"(dry_run={result.dry_run_count}, failed={result.failed_count}, skipped={result.skipped_count})"
        )
        typer.echo("executor mode: fake dry-run (no state changes)")
        if result.failed_count > 0:
            raise typer.Exit(code=1)
        return

    typer.echo(
        f"processed due jobs: {result.processed_count} "
        f"(published={result.published_count}, failed={result.failed_count}, skipped={result.skipped_count})"
    )
    typer.echo("executor mode: live publish via configured publishers")
    if result.failed_count > 0:
        raise typer.Exit(code=1)


@scheduler_app.command("run")
def scheduler_run_command(
    config_dir: Annotated[
        Path,
        typer.Option(
            "--config-dir",
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            resolve_path=True,
            help="Directory containing accounts.yaml, prompts.yaml, and sources.yaml.",
        ),
    ] = Path("config"),
    database_url: Annotated[
        str | None,
        typer.Option(
            "--database-url",
            help="Explicit database URL. Falls back to DATABASE_URL, then the project default.",
        ),
    ] = None,
    discover_interval_minutes: Annotated[
        int,
        typer.Option(
            "--discover-interval-minutes",
            min=1,
            help="Interval in minutes for the discover job.",
        ),
    ] = 30,
    backfill_interval_minutes: Annotated[
        int,
        typer.Option(
            "--backfill-interval-minutes",
            min=1,
            help="Interval in minutes for the backfill job.",
        ),
    ] = 15,
    publish_due_interval_seconds: Annotated[
        int,
        typer.Option(
            "--publish-due-interval-seconds",
            min=1,
            help="Interval in seconds for the publish-due job.",
        ),
    ] = 60,
) -> None:
    """Start the local APScheduler loop for M11 jobs."""

    try:
        scheduler = build_scheduler_runtime(
            config_dir=config_dir,
            database_url=database_url,
            discover_interval_minutes=discover_interval_minutes,
            backfill_interval_minutes=backfill_interval_minutes,
            publish_due_interval_seconds=publish_due_interval_seconds,
        )
    except (DatabaseSchemaError, ReviewQueueError, ValueError) as exc:
        _exit_with_error(exc)
    typer.echo(
        "scheduler registered jobs: "
        "discover, backfill, publish_due "
        f"(discover={discover_interval_minutes}m, "
        f"backfill={backfill_interval_minutes}m, "
        f"publish_due={publish_due_interval_seconds}s, dry_run=true)"
    )
    try:
        scheduler.start()
    except (DatabaseSchemaError, ReviewQueueError, ValueError) as exc:
        _exit_with_error(exc)


@db_app.command("init")
def init_database(
    database_url: Annotated[
        str | None,
        typer.Option(
            "--database-url",
            help="Explicit database URL. Falls back to DATABASE_URL, then the project default.",
        ),
    ] = None,
) -> None:
    """Create the configured database schema."""

    try:
        resolved_url = bootstrap_database(database_url)
    except DatabaseSchemaError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"database initialized: {resolved_url}")


@db_app.command("upgrade")
def upgrade_database_command(
    database_url: Annotated[
        str | None,
        typer.Option(
            "--database-url",
            help="Explicit database URL. Falls back to DATABASE_URL, then the project default.",
        ),
    ] = None,
) -> None:
    """Apply supported SQLite schema upgrades to an existing database."""

    try:
        result = upgrade_database_schema(database_url)
    except DatabaseSchemaError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    if result.was_upgraded:
        typer.echo(
            "database upgraded: "
            f"{result.database_url} "
            f"(schema_version={result.from_version}->{result.to_version})"
        )
        return

    typer.echo(
        "database already current: "
        f"{result.database_url} "
        f"(schema_version={result.to_version})"
    )


def _exit_with_error(exc: Exception) -> None:
    typer.echo(str(exc), err=True)
    raise typer.Exit(code=1) from exc


def main() -> None:
    """Run the CLI application."""
    app()


if __name__ == "__main__":
    main()
