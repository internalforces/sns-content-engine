"""Typer CLI entrypoint for sns-content-engine."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from app import __version__
from app.storage import DatabaseSchemaError, bootstrap_database
from app.workflows import build_content_briefs, discover_sources, generate_drafts, ingest_sources

app = typer.Typer(
    help="Config-driven multi-account SNS content engine.",
    no_args_is_help=True,
)
db_app = typer.Typer(help="Database bootstrap and inspection commands.")

app.add_typer(db_app, name="db")


@app.command()
def version() -> None:
    """Print the application version."""
    typer.echo(f"sns-content-engine {__version__}")


@app.command()
def healthcheck() -> None:
    """Run a lightweight local healthcheck."""
    typer.echo("status=ok")


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
    except DatabaseSchemaError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"processed {result.processed_count} content briefs")
    typer.echo(f"draft sets created: {result.created_count}")
    typer.echo(f"draft sets existing: {result.existing_count}")
    typer.echo(f"no x channel: {result.no_channel_count}")
    typer.echo(f"missing account: {result.missing_account_count}")
    typer.echo(f"draft variants created: {result.created_variant_count}")


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


def main() -> None:
    """Run the CLI application."""
    app()


if __name__ == "__main__":
    main()
