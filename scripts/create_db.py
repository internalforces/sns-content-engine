#!/usr/bin/env python3
"""Thin wrapper around the shared database bootstrap helper."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.storage import DatabaseSchemaError, bootstrap_database


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for the bootstrap script."""

    parser = argparse.ArgumentParser(description="Initialize the sns-content-engine database schema.")
    parser.add_argument(
        "--database-url",
        dest="database_url",
        help="Explicit database URL. Falls back to DATABASE_URL, then the project default.",
    )
    return parser


def main() -> None:
    """Run the bootstrap script."""

    args = build_parser().parse_args()
    try:
        resolved_url = bootstrap_database(args.database_url)
    except DatabaseSchemaError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
    print(f"database initialized: {resolved_url}")


if __name__ == "__main__":
    main()
