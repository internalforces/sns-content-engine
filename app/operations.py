"""Operational helpers for logging, healthchecks, and retry policy."""

from __future__ import annotations

import json
import logging
import sqlite3
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.engine import URL, make_url

from app.config import ConfigRegistry
from app.storage import ensure_database_schema_is_current, resolve_database_url

_OPERATIONS_LOGGER_NAME = "sns_engine.operations"
_SAFE_LOG_CHARS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._/:")


class RetryPolicy(str, Enum):
    """Supported operational retry policies."""

    MANUAL_RESCHEDULE = "manual_reschedule"


@dataclass(frozen=True, slots=True)
class HealthcheckCheck:
    """One readiness check outcome."""

    name: str
    status: str
    message: str


@dataclass(frozen=True, slots=True)
class HealthcheckResult:
    """Aggregated readiness output."""

    checks: tuple[HealthcheckCheck, ...]

    @property
    def failed_check_count(self) -> int:
        """Return the number of failed checks."""

        return sum(check.status != "ok" for check in self.checks)

    @property
    def status(self) -> str:
        """Return the overall readiness status."""

        return "ok" if self.failed_check_count == 0 else "failed"

    @property
    def is_ok(self) -> bool:
        """Return whether all readiness checks passed."""

        return self.failed_check_count == 0

    def to_lines(self, *, component: str = "cli") -> tuple[str, ...]:
        """Render the result as key=value lines."""

        lines = [
            format_log_line(
                event="healthcheck",
                component=component,
                status=self.status,
                check_count=len(self.checks),
                failed_check_count=self.failed_check_count,
            )
        ]
        for check in self.checks:
            lines.append(
                format_log_line(
                    event="healthcheck",
                    component=component,
                    status=check.status,
                    check=check.name,
                    message=check.message,
                )
            )
        return tuple(lines)


def run_healthcheck(
    *,
    config_dir: Path | str = Path("config"),
    database_url: str | None = None,
) -> HealthcheckResult:
    """Run config and database readiness checks."""

    checks: list[HealthcheckCheck] = []
    normalized_config_dir = Path(config_dir).resolve()

    try:
        registry = ConfigRegistry.from_directory(normalized_config_dir)
    except Exception as exc:
        checks.append(
            HealthcheckCheck(
                name="config",
                status="failed",
                message=str(exc),
            )
        )
    else:
        checks.append(
            HealthcheckCheck(
                name="config",
                status="ok",
                message=(
                    f"loaded accounts={len(registry.accounts)} "
                    f"profiles={len(registry.profiles)} "
                    f"sources={len(registry.sources)} "
                    f"config_dir={normalized_config_dir}"
                ),
            )
        )

    resolved_database_url = resolve_database_url(database_url)
    try:
        database_message = _run_database_healthcheck(resolved_database_url)
    except Exception as exc:
        checks.append(
            HealthcheckCheck(
                name="database",
                status="failed",
                message=str(exc),
            )
        )
    else:
        checks.append(
            HealthcheckCheck(
                name="database",
                status="ok",
                message=database_message,
            )
        )

    return HealthcheckResult(checks=tuple(checks))


def get_operations_logger() -> logging.Logger:
    """Return the shared operations logger."""

    logger = logging.getLogger(_OPERATIONS_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    handler = next(
        (candidate for candidate in logger.handlers if getattr(candidate, "_sns_engine_ops_handler", False)),
        None,
    )
    if handler is None or getattr(handler, "stream", None) is not sys.stderr:
        if handler is not None:
            logger.removeHandler(handler)
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("%(message)s"))
        setattr(handler, "_sns_engine_ops_handler", True)
        logger.addHandler(handler)

    return logger


def log_event(*, level: int = logging.INFO, **fields: Any) -> None:
    """Emit one operational log line."""

    get_operations_logger().log(level, format_log_line(**fields))


def log_workflow_start(*, component: str, workflow: str, **fields: Any) -> None:
    """Log the start of an operational workflow."""

    log_event(
        level=logging.INFO,
        event="workflow",
        component=component,
        status="started",
        workflow=workflow,
        **fields,
    )


def log_workflow_exception(
    *,
    component: str,
    workflow: str,
    error: Exception,
    **fields: Any,
) -> None:
    """Log a workflow exception."""

    log_event(
        level=logging.ERROR,
        event="workflow",
        component=component,
        status="failed",
        workflow=workflow,
        error=str(error),
        error_type=type(error).__name__,
        **fields,
    )


def log_workflow_result(*, component: str, workflow: str, result: Any) -> None:
    """Log a workflow summary using the shared operational format."""

    status, summary_fields = summarize_workflow_result(workflow=workflow, result=result)
    level = logging.ERROR if status == "failed" else logging.INFO
    log_event(
        level=level,
        event="workflow",
        component=component,
        status=status,
        workflow=workflow,
        **summary_fields,
    )


def summarize_workflow_result(*, workflow: str, result: Any) -> tuple[str, dict[str, Any]]:
    """Return an operational status and summary fields for a workflow result."""

    if workflow == "discover":
        failure_count = getattr(result, "failure_count", 0)
        return (
            "failed" if failure_count else "ok",
            {
                "discovered_count": getattr(result, "discovered_count", getattr(result, "item_count", 0)),
                "processed_source_count": len(getattr(result, "processed_sources", ())),
                "failure_count": failure_count,
            },
        )

    if workflow == "backfill":
        return (
            "ok",
            {
                "processed_channel_count": getattr(result, "processed_channel_count", 0),
                "existing_count": getattr(result, "existing_count", 0),
                "created_count": getattr(result, "created_count", 0),
                "skipped_count": getattr(result, "skipped_count", 0),
            },
        )

    if workflow == "publish_due":
        failed_count = getattr(result, "failed_count", 0)
        summary: dict[str, Any] = {
            "processed_count": getattr(result, "processed_count", 0),
            "failed_count": failed_count,
            "skipped_count": getattr(result, "skipped_count", 0),
            "dry_run": getattr(result, "dry_run", False),
        }
        if getattr(result, "dry_run", False):
            summary["dry_run_count"] = getattr(result, "dry_run_count", 0)
        else:
            summary["published_count"] = getattr(result, "published_count", 0)
        return ("failed" if failed_count else "ok", summary)

    return ("ok", {})


def format_log_line(**fields: Any) -> str:
    """Format a consistent key=value operations log line."""

    ordered_fields: list[tuple[str, Any]] = []
    for key in ("event", "component", "status", "workflow", "check"):
        if key in fields:
            ordered_fields.append((key, fields.pop(key)))
    ordered_fields.extend(fields.items())
    return " ".join(f"{key}={_format_log_value(value)}" for key, value in ordered_fields)


def _format_log_value(value: Any) -> str:
    if isinstance(value, Enum):
        return _format_log_value(value.value)
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, Path):
        return _format_log_value(str(value))

    text = str(value)
    if text and all(character in _SAFE_LOG_CHARS for character in text):
        return text
    return json.dumps(text, ensure_ascii=True)


def _run_database_healthcheck(database_url: str) -> str:
    url = make_url(database_url)
    engine = None
    try:
        engine = _create_healthcheck_engine(url)
        ensure_database_schema_is_current(engine)
    finally:
        if engine is not None:
            engine.dispose()

    backend, target = _describe_database_target(url)
    return f"schema_current database_backend={backend} database_target={target}"


def _create_healthcheck_engine(url: URL):
    if _is_file_backed_sqlite_url(url):
        database_path = _resolve_sqlite_database_path(url)
        if not database_path.exists():
            raise RuntimeError(
                f"database file does not exist: {database_path}. "
                "Run `sns-engine db init` against a fresh database."
            )

        readonly_uri = f"{database_path.as_uri()}?mode=ro"
        return create_engine(
            "sqlite+pysqlite://",
            creator=lambda: sqlite3.connect(readonly_uri, uri=True),
            future=True,
            pool_pre_ping=True,
        )

    return create_engine(url, future=True, pool_pre_ping=True)


def _describe_database_target(url: URL) -> tuple[str, str]:
    backend = url.drivername.split("+", 1)[0]
    if backend == "sqlite":
        return backend, _describe_sqlite_target(url)

    host = url.host or "unknown"
    port = f":{url.port}" if url.port is not None else ""
    database = f"/{url.database}" if url.database else ""
    return backend, f"{host}{port}{database}"


def _describe_sqlite_target(url: URL) -> str:
    database = url.database
    if not database:
        return "memory"
    if database == ":memory:":
        return ":memory:"
    if database.startswith("file:"):
        return "sqlite_uri"
    return str(Path(database).expanduser().resolve())


def _is_file_backed_sqlite_url(url: URL) -> bool:
    backend = url.drivername.split("+", 1)[0]
    if backend != "sqlite":
        return False

    database = url.database
    if not database:
        return False
    if database == ":memory:":
        return False
    if database.startswith("file:"):
        return False
    return True


def _resolve_sqlite_database_path(url: URL) -> Path:
    database = url.database or ""
    return Path(database).expanduser().resolve()
