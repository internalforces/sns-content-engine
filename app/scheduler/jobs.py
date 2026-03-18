"""Scheduler job helpers for discovery, backfill, and due publishing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from app.config import ConfigRegistry
from app.scheduler.planner import SlotPlanner, SlotPlanningRequest
from app.storage import (
    PublishJob,
    PublishJobRepository,
    PublishJobState,
    PublishLogRepository,
    build_publish_job_idempotency_key,
    create_database_engine,
    create_session_factory,
    ensure_database_schema_is_current,
    session_scope,
)
from app.workflows.discover_sources import discover_sources


@dataclass(frozen=True, slots=True)
class SchedulerDiscoverResult:
    """Summary of a scheduled discover run."""

    discovered_count: int
    processed_sources: tuple[str, ...]
    failure_messages: tuple[str, ...]

    @property
    def failure_count(self) -> int:
        return len(self.failure_messages)


@dataclass(frozen=True, slots=True)
class BackfillChannelResult:
    """Backfill summary for one account/channel pair."""

    account_key: str
    channel: str
    backlog_target: int
    existing_future_job_count: int
    eligible_draft_count: int
    planned_slot_count: int
    created_job_ids: tuple[int, ...]
    skipped_slot_count: int

    @property
    def created_count(self) -> int:
        return len(self.created_job_ids)


@dataclass(frozen=True, slots=True)
class BackfillResult:
    """Aggregated backfill result."""

    outcomes: tuple[BackfillChannelResult, ...]

    @property
    def processed_channel_count(self) -> int:
        return len(self.outcomes)

    @property
    def created_count(self) -> int:
        return sum(outcome.created_count for outcome in self.outcomes)

    @property
    def existing_count(self) -> int:
        return sum(outcome.existing_future_job_count for outcome in self.outcomes)

    @property
    def skipped_count(self) -> int:
        return sum(outcome.skipped_slot_count for outcome in self.outcomes)


@dataclass(frozen=True, slots=True)
class PublishExecutionResult:
    """Normalized executor result for one publish attempt."""

    external_post_id: str
    dry_run: bool = True


class PublishExecutor(Protocol):
    """Executor contract for due publish jobs."""

    def execute(self, job: PublishJob) -> PublishExecutionResult:
        """Execute the publish action for one job."""


class FakePublishExecutor:
    """Deterministic fake executor used until a real publisher exists."""

    def execute(self, job: PublishJob) -> PublishExecutionResult:
        return PublishExecutionResult(external_post_id=f"dry-run:{job.id}", dry_run=True)


@dataclass(frozen=True, slots=True)
class PublishDueOutcome:
    """Result for one due publish job."""

    publish_job_id: int
    status: str
    state: PublishJobState
    message: str
    external_post_id: str | None = None


@dataclass(frozen=True, slots=True)
class PublishDueResult:
    """Aggregated publish-due run result."""

    outcomes: tuple[PublishDueOutcome, ...]
    dry_run: bool

    @property
    def processed_count(self) -> int:
        return len(self.outcomes)

    @property
    def published_count(self) -> int:
        return sum(outcome.status == "published" for outcome in self.outcomes)

    @property
    def failed_count(self) -> int:
        return sum(outcome.status == "failed" for outcome in self.outcomes)

    @property
    def skipped_count(self) -> int:
        return sum(outcome.status == "skipped" for outcome in self.outcomes)


def scheduler_discover(
    config_dir: Path | str = Path("config"),
) -> SchedulerDiscoverResult:
    """Run the configured discover workflow for scheduler use."""

    result = discover_sources(config_dir)
    return SchedulerDiscoverResult(
        discovered_count=result.item_count,
        processed_sources=result.processed_sources,
        failure_messages=tuple(failure.format_for_cli() for failure in result.failures),
    )


def backfill_publish_jobs(
    *,
    config_dir: Path | str = Path("config"),
    database_url: str | None = None,
    session_factory=None,
    now: datetime | None = None,
) -> BackfillResult:
    """Create missing scheduled publish jobs up to each channel backlog target."""

    normalized_now = _normalize_datetime(now or datetime.now(timezone.utc))
    registry = ConfigRegistry.from_directory(Path(config_dir))
    planner = SlotPlanner()
    owned_engine, resolved_session_factory = _resolve_session_factory(
        database_url=database_url,
        session_factory=session_factory,
    )
    outcomes: list[BackfillChannelResult] = []

    try:
        for account_key in sorted(registry.accounts):
            account = registry.get_account(account_key)
            for channel in sorted(account.channels):
                channel_config = account.channels[channel]
                backlog_target = channel_config.schedule.backlog_target
                if backlog_target <= 0:
                    continue

                with session_scope(resolved_session_factory) as session:
                    jobs = PublishJobRepository(session)
                    logs = PublishLogRepository(session)

                    active_jobs = jobs.list_active_for_account_channel(account_key, channel)
                    future_active_jobs = [
                        job
                        for job in active_jobs
                        if job.scheduled_for is not None and job.scheduled_for >= normalized_now
                    ]
                    missing_slots = max(0, backlog_target - len(future_active_jobs))
                    eligible_drafts = jobs.list_approved_without_active_job(account_key, channel)
                    occupied_times = tuple(
                        _job_reference_time(job) for job in active_jobs if _job_reference_time(job) is not None
                    )
                    planning = planner.plan(
                        SlotPlanningRequest(
                            account_key=account_key,
                            channel=channel,
                            schedule=channel_config.schedule,
                            now=normalized_now,
                            occupied_times=occupied_times,
                            target_slot_count=missing_slots,
                        )
                    )

                    created_job_ids: list[int] = []
                    for draft, slot in zip(eligible_drafts, planning.slots, strict=False):
                        job = jobs.add(
                            PublishJob(
                                draft_variant=draft,
                                channel=channel,
                                scheduled_for=slot.scheduled_for,
                                idempotency_key=build_publish_job_idempotency_key(
                                    draft_variant_id=draft.id,
                                    channel=channel,
                                    scheduled_for=slot.scheduled_for,
                                ),
                            )
                        )
                        logs.record(
                            publish_job=job,
                            event_type="scheduled",
                            message=(
                                f"scheduled {account_key}/{channel} draft {draft.id} "
                                f"for {job.scheduled_for.isoformat()}"
                            ),
                            payload={
                                "account_key": account_key,
                                "channel": channel,
                                "draft_variant_id": draft.id,
                                "scheduled_for": job.scheduled_for.isoformat() if job.scheduled_for else None,
                                "idempotency_key": job.idempotency_key,
                            },
                        )
                        created_job_ids.append(job.id)

                created_count = len(created_job_ids)
                skipped_slot_count = max(0, missing_slots - created_count)
                outcomes.append(
                    BackfillChannelResult(
                        account_key=account_key,
                        channel=channel,
                        backlog_target=backlog_target,
                        existing_future_job_count=len(future_active_jobs),
                        eligible_draft_count=len(eligible_drafts),
                        planned_slot_count=len(planning.slots),
                        created_job_ids=tuple(created_job_ids),
                        skipped_slot_count=skipped_slot_count,
                    )
                )
    finally:
        _dispose_engine(owned_engine)

    return BackfillResult(outcomes=tuple(outcomes))


def publish_due_jobs(
    *,
    database_url: str | None = None,
    session_factory=None,
    executor: PublishExecutor | None = None,
    now: datetime | None = None,
) -> PublishDueResult:
    """Execute due scheduled publish jobs with a swappable executor."""

    normalized_now = _normalize_datetime(now or datetime.now(timezone.utc))
    resolved_executor = executor or FakePublishExecutor()
    owned_engine, resolved_session_factory = _resolve_session_factory(
        database_url=database_url,
        session_factory=session_factory,
    )
    outcomes: list[PublishDueOutcome] = []

    try:
        with session_scope(resolved_session_factory) as session:
            due_job_ids = [
                job.id
                for job in PublishJobRepository(session).list_due_scheduled(as_of=normalized_now)
            ]

        for job_id in due_job_ids:
            outcomes.append(
                _process_due_job(
                    publish_job_id=job_id,
                    session_factory=resolved_session_factory,
                    executor=resolved_executor,
                    now=normalized_now,
                )
            )
    finally:
        _dispose_engine(owned_engine)

    return PublishDueResult(
        outcomes=tuple(outcomes),
        dry_run=isinstance(resolved_executor, FakePublishExecutor),
    )


def _process_due_job(
    *,
    publish_job_id: int,
    session_factory,
    executor: PublishExecutor,
    now: datetime,
) -> PublishDueOutcome:
    with session_scope(session_factory) as session:
        jobs = PublishJobRepository(session)
        logs = PublishLogRepository(session)
        job = jobs.get(publish_job_id)
        if job is None:
            return PublishDueOutcome(
                publish_job_id=publish_job_id,
                status="skipped",
                state=PublishJobState.CANCELLED,
                message="publish job no longer exists",
            )

        if job.state is not PublishJobState.SCHEDULED or job.scheduled_for is None or job.scheduled_for > now:
            return PublishDueOutcome(
                publish_job_id=publish_job_id,
                status="skipped",
                state=job.state,
                message="publish job is no longer due",
                external_post_id=job.external_post_id,
            )

        try:
            jobs.transition_state(job, PublishJobState.PUBLISHING, occurred_at=now)
            logs.record(
                publish_job=job,
                event_type="publishing",
                message=f"publishing job {job.id} with idempotency key {job.idempotency_key}",
                payload={"idempotency_key": job.idempotency_key, "attempt_count": job.attempt_count},
            )

            execution = executor.execute(job)
        except Exception as exc:
            jobs.transition_state(
                job,
                PublishJobState.FAILED,
                last_error=str(exc),
                occurred_at=now,
            )
            logs.record(
                publish_job=job,
                event_type="failed",
                message=f"publish job {job.id} failed: {exc}",
                payload={"error_message": str(exc), "attempt_count": job.attempt_count},
            )
            return PublishDueOutcome(
                publish_job_id=job.id,
                status="failed",
                state=job.state,
                message=str(exc),
            )

        jobs.transition_state(
            job,
            PublishJobState.PUBLISHED,
            external_post_id=execution.external_post_id,
            occurred_at=now,
        )
        logs.record(
            publish_job=job,
            event_type="published",
            message=f"publish job {job.id} published as {execution.external_post_id}",
            payload={
                "external_post_id": execution.external_post_id,
                "attempt_count": job.attempt_count,
                "dry_run": execution.dry_run,
            },
        )
        return PublishDueOutcome(
            publish_job_id=job.id,
            status="published",
            state=job.state,
            message="published successfully",
            external_post_id=execution.external_post_id,
        )


def _job_reference_time(job: PublishJob) -> datetime | None:
    if job.state is PublishJobState.PUBLISHED and job.published_at is not None:
        return _normalize_datetime(job.published_at)
    if job.scheduled_for is not None:
        return _normalize_datetime(job.scheduled_for)
    return None


def _resolve_session_factory(*, database_url: str | None, session_factory):
    owned_engine = None
    if session_factory is None:
        owned_engine = create_database_engine(database_url)
        ensure_database_schema_is_current(owned_engine)
        return owned_engine, create_session_factory(owned_engine)

    bound_engine = getattr(session_factory, "kw", {}).get("bind")
    if bound_engine is not None:
        ensure_database_schema_is_current(bound_engine)
    return owned_engine, session_factory


def _dispose_engine(engine) -> None:
    if engine is not None:
        engine.dispose()


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
