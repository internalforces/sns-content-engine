"""Typer CLI entrypoint for sns-content-engine."""

from __future__ import annotations

from typing import Annotated

import typer

from app import __version__
from app.storage import bootstrap_database

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

    resolved_url = bootstrap_database(database_url)
    typer.echo(f"database initialized: {resolved_url}")


def main() -> None:
    """Run the CLI application."""
    app()


if __name__ == "__main__":
    main()
