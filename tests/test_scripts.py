"""Tests for standalone project scripts."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from sqlalchemy import inspect
from sqlalchemy.engine import create_engine

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_create_db_script_bootstraps_the_database(tmp_path: Path) -> None:
    database_path = tmp_path / "script.db"
    database_url = f"sqlite+pysqlite:///{database_path}"

    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts/create_db.py"), "--database-url", database_url],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == f"database initialized: {database_url}"

    engine = create_engine(database_url)
    try:
        assert set(inspect(engine).get_table_names()) == {
            "content_briefs",
            "draft_variants",
            "publish_jobs",
            "publish_logs",
            "source_items",
        }
    finally:
        engine.dispose()
