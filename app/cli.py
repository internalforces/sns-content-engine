"""Typer CLI entrypoint for sns-content-engine."""

from __future__ import annotations

import typer

from app import __version__

app = typer.Typer(
    help="Config-driven multi-account SNS content engine.",
    no_args_is_help=True,
)


@app.command()
def version() -> None:
    """Print the application version."""
    typer.echo(f"sns-content-engine {__version__}")


@app.command()
def healthcheck() -> None:
    """Run a lightweight local healthcheck."""
    typer.echo("status=ok")


def main() -> None:
    """Run the CLI application."""
    app()


if __name__ == "__main__":
    main()
