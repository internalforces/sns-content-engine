"""APScheduler runtime wiring for the local operations loop."""

from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import Callable

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.operations import log_workflow_exception, log_workflow_result, log_workflow_start
from app.scheduler.jobs import backfill_publish_jobs, publish_due_jobs, scheduler_discover


def build_scheduler_runtime(
    *,
    config_dir: Path | str = Path("config"),
    database_url: str | None = None,
    discover_interval_minutes: int = 30,
    backfill_interval_minutes: int = 15,
    publish_due_interval_seconds: int = 60,
    scheduler: BlockingScheduler | None = None,
) -> BlockingScheduler:
    """Build a blocking APScheduler instance with dry-run publish execution."""

    runtime = scheduler or BlockingScheduler(timezone="UTC")
    runtime.add_job(
        _build_logged_job(
            workflow="discover",
            runner=partial(scheduler_discover, config_dir=config_dir),
        ),
        trigger=IntervalTrigger(minutes=discover_interval_minutes, timezone="UTC"),
        id="discover",
        name="discover",
        replace_existing=True,
    )
    runtime.add_job(
        _build_logged_job(
            workflow="backfill",
            runner=partial(
                backfill_publish_jobs,
                config_dir=config_dir,
                database_url=database_url,
            ),
        ),
        trigger=IntervalTrigger(minutes=backfill_interval_minutes, timezone="UTC"),
        id="backfill",
        name="backfill",
        replace_existing=True,
    )
    runtime.add_job(
        _build_logged_job(
            workflow="publish_due",
            runner=partial(
                publish_due_jobs,
                config_dir=config_dir,
                database_url=database_url,
                dry_run=True,
            ),
        ),
        trigger=IntervalTrigger(seconds=publish_due_interval_seconds, timezone="UTC"),
        id="publish_due",
        name="publish_due",
        replace_existing=True,
    )
    return runtime


def _build_logged_job(*, workflow: str, runner: Callable[[], object]) -> Callable[[], object | None]:
    """Wrap a scheduler job with operational logging and failure isolation."""

    def _run_logged_job() -> object | None:
        log_workflow_start(component="scheduler", workflow=workflow)
        try:
            result = runner()
        except Exception as exc:
            log_workflow_exception(component="scheduler", workflow=workflow, error=exc)
            return None

        log_workflow_result(component="scheduler", workflow=workflow, result=result)
        return result

    return _run_logged_job
