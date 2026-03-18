"""APScheduler runtime wiring for the local operations loop."""

from __future__ import annotations

from functools import partial
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

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
        partial(scheduler_discover, config_dir=config_dir),
        trigger=IntervalTrigger(minutes=discover_interval_minutes, timezone="UTC"),
        id="discover",
        name="discover",
        replace_existing=True,
    )
    runtime.add_job(
        partial(
            backfill_publish_jobs,
            config_dir=config_dir,
            database_url=database_url,
        ),
        trigger=IntervalTrigger(minutes=backfill_interval_minutes, timezone="UTC"),
        id="backfill",
        name="backfill",
        replace_existing=True,
    )
    runtime.add_job(
        partial(
            publish_due_jobs,
            config_dir=config_dir,
            database_url=database_url,
            dry_run=True,
        ),
        trigger=IntervalTrigger(seconds=publish_due_interval_seconds, timezone="UTC"),
        id="publish_due",
        name="publish_due",
        replace_existing=True,
    )
    return runtime
