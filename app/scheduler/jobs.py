"""Scheduler job helpers for discovery, backfill, and due publishing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from app.config import ConfigRegistry
from app.connectors.publishers import (
    ConfigPublisherResolver,
    PublishRequest,
    PublishResult,
    PublisherResolver,
)
from app.operations import RetryPolicy, log_event
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
    def dry_run_count(self) -> int:
        return sum(outcome.status == "dry_run" for outcome in self.outcomes)

    @property
    def skipped_count(self) -> int:
        return sum(outcome.status == "skipped" for outcome in self.outcomes)


@dataclass(frozen=True, slots=True)
class PreparedPublish:
    """Durably claimed publish job context for the external publish step."""

    publish_job_id: int
    publish_request: PublishRequest


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
    config_dir: Path | str = Path("config"),
    database_url: str | None = None,
    session_factory=None,
    executor: PublishExecutor | None = None,
    publisher_resolver: PublisherResolver | None = None,
    now: datetime | None = None,
    dry_run: bool | None = None,
) -> PublishDueResult:
    """Execute due scheduled publish jobs with a swappable executor."""

    normalized_now = _normalize_datetime(now or datetime.now(timezone.utc))
    if executor is not None and publisher_resolver is not None:
        raise ValueError("pass either executor or publisher_resolver, not both")

    resolved_dry_run = (
        dry_run if dry_run is not None else executor is None and publisher_resolver is None
    )
    resolved_publisher_resolver = publisher_resolver
    if not resolved_dry_run and resolved_publisher_resolver is None and executor is None:
        resolved_publisher_resolver = ConfigPublisherResolver(config_dir=config_dir)
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
                    executor=executor,
                    publisher_resolver=resolved_publisher_resolver,
                    now=normalized_now,
                    dry_run=resolved_dry_run,
                )
            )
    finally:
        _dispose_engine(owned_engine)

    return PublishDueResult(
        outcomes=tuple(outcomes),
        dry_run=resolved_dry_run,
    )


def _process_due_job(
    *,
    publish_job_id: int,
    session_factory,
    executor: PublishExecutor | None,
    publisher_resolver: PublisherResolver | None,
    now: datetime,
    dry_run: bool,
) -> PublishDueOutcome:
    if dry_run:
        return _process_due_job_dry_run(
            publish_job_id=publish_job_id,
            session_factory=session_factory,
            executor=executor,
            now=now,
        )

    prepared_or_outcome = _prepare_live_publish(
        publish_job_id=publish_job_id,
        session_factory=session_factory,
        now=now,
    )
    if isinstance(prepared_or_outcome, PublishDueOutcome):
        return prepared_or_outcome

    try:
        publish_result = _execute_live_publish(
            session_factory=session_factory,
            prepared=prepared_or_outcome,
            executor=executor,
            publisher_resolver=publisher_resolver,
        )
    except Exception as exc:
        return _finalize_live_publish_failure(
            publish_job_id=prepared_or_outcome.publish_job_id,
            session_factory=session_factory,
            now=now,
            error_message=str(exc),
            provider=_provider_name_for_channel(prepared_or_outcome.publish_request.channel),
        )

    return _finalize_live_publish_result(
        publish_job_id=prepared_or_outcome.publish_job_id,
        session_factory=session_factory,
        now=now,
        publish_result=publish_result,
    )


def _process_due_job_dry_run(
    *,
    publish_job_id: int,
    session_factory,
    executor: PublishExecutor | None,
    now: datetime,
) -> PublishDueOutcome:
    with session_scope(session_factory) as session:
        jobs = PublishJobRepository(session)
        job = jobs.get(publish_job_id)
        if job is None:
            return PublishDueOutcome(
                publish_job_id=publish_job_id,
                status="skipped",
                state=PublishJobState.CANCELLED,
                message="publish job is no longer claimable",
            )

        if (
            job.state is not PublishJobState.SCHEDULED
            or job.scheduled_for is None
            or job.scheduled_for > now
        ):
            return PublishDueOutcome(
                publish_job_id=publish_job_id,
                status="skipped",
                state=job.state,
                message="publish job is no longer due",
                external_post_id=job.external_post_id,
            )

        execution = (executor or FakePublishExecutor()).execute(job)
        log_event(
            event="publish_job",
            component="publisher",
            status="dry_run",
            workflow="publish_due",
            publish_job_id=job.id,
            account_key=_account_key_for_job(job),
            channel=job.channel,
            attempt_count=job.attempt_count,
            retry_policy=RetryPolicy.MANUAL_RESCHEDULE,
            external_post_id=execution.external_post_id,
        )
        return PublishDueOutcome(
            publish_job_id=job.id,
            status="dry_run",
            state=job.state,
            message="dry-run only; no state changes were applied",
            external_post_id=execution.external_post_id,
        )


def _prepare_live_publish(
    *,
    publish_job_id: int,
    session_factory,
    now: datetime,
) -> PreparedPublish | PublishDueOutcome:
    with session_scope(session_factory) as session:
        jobs = PublishJobRepository(session)
        logs = PublishLogRepository(session)
        job = jobs.claim_due_job(
            publish_job_id,
            as_of=now,
            claimed_at=now,
        )
        if job is None:
            current_job = jobs.get(publish_job_id)
            return PublishDueOutcome(
                publish_job_id=publish_job_id,
                status="skipped",
                state=current_job.state if current_job is not None else PublishJobState.CANCELLED,
                message="publish job is no longer claimable",
                external_post_id=current_job.external_post_id if current_job is not None else None,
            )

        try:
            jobs.ensure_publishable(job)
            publish_request = _build_publish_request(job)
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
                payload=_build_failure_payload(
                    job,
                    error_message=str(exc),
                    provider=_provider_name_for_channel(job.channel),
                ),
            )
            _log_publish_job_event(
                job,
                status="failed",
                error=str(exc),
                provider=_provider_name_for_channel(job.channel),
            )
            return PublishDueOutcome(
                publish_job_id=job.id,
                status="failed",
                state=job.state,
                message=str(exc),
            )

        logs.record(
            publish_job=job,
            event_type="publishing",
            message=f"publishing job {job.id} with idempotency key {job.idempotency_key}",
            payload={
                "idempotency_key": job.idempotency_key,
                "attempt_count": job.attempt_count,
                "account_key": publish_request.account_key,
                "channel": publish_request.channel,
            },
        )
        return PreparedPublish(
            publish_job_id=job.id,
            publish_request=publish_request,
        )


def _finalize_live_publish_result(
    *,
    publish_job_id: int,
    session_factory,
    now: datetime,
    publish_result: PublishResult,
) -> PublishDueOutcome:
    if publish_result.dry_run:
        return _finalize_live_publish_failure(
            publish_job_id=publish_job_id,
            session_factory=session_factory,
            now=now,
            error_message="stateful publish execution requires a non-dry-run executor result",
            provider=publish_result.provider,
            credential_ref=publish_result.credential_ref,
            status=publish_result.status,
            provider_payload=publish_result.provider_payload,
        )

    if publish_result.status == "failed":
        return _finalize_live_publish_failure(
            publish_job_id=publish_job_id,
            session_factory=session_factory,
            now=now,
            error_message=publish_result.error_message or "publisher returned a failed result",
            provider=publish_result.provider,
            credential_ref=publish_result.credential_ref,
            status=publish_result.status,
            provider_payload=publish_result.provider_payload,
        )

    if publish_result.status != "published":
        return _finalize_live_publish_failure(
            publish_job_id=publish_job_id,
            session_factory=session_factory,
            now=now,
            error_message=f"publisher returned unsupported status {publish_result.status!r}",
            provider=publish_result.provider,
            credential_ref=publish_result.credential_ref,
            status=publish_result.status,
            provider_payload=publish_result.provider_payload,
        )

    if publish_result.external_post_id is None:
        return _finalize_live_publish_failure(
            publish_job_id=publish_job_id,
            session_factory=session_factory,
            now=now,
            error_message="publisher returned a published result without external_post_id",
            provider=publish_result.provider,
            credential_ref=publish_result.credential_ref,
            status=publish_result.status,
            provider_payload=publish_result.provider_payload,
        )

    with session_scope(session_factory) as session:
        jobs = PublishJobRepository(session)
        logs = PublishLogRepository(session)
        job = jobs.get(publish_job_id)
        if job is None:
            return PublishDueOutcome(
                publish_job_id=publish_job_id,
                status="skipped",
                state=PublishJobState.CANCELLED,
                message="publish job disappeared before finalization",
                external_post_id=publish_result.external_post_id,
            )
        if job.state is not PublishJobState.PUBLISHING:
            return PublishDueOutcome(
                publish_job_id=job.id,
                status="skipped",
                state=job.state,
                message="publish job is no longer awaiting finalization",
                external_post_id=job.external_post_id or publish_result.external_post_id,
            )

        jobs.transition_state(
            job,
            PublishJobState.PUBLISHED,
            external_post_id=publish_result.external_post_id,
            occurred_at=now,
        )
        logs.record(
            publish_job=job,
            event_type="published",
            message=f"publish job {job.id} published as {publish_result.external_post_id}",
            payload=_build_success_payload(
                job,
                external_post_id=publish_result.external_post_id,
                provider=publish_result.provider or _provider_name_for_channel(job.channel),
                status=publish_result.status,
                provider_payload=publish_result.provider_payload,
            ),
        )
        _log_publish_job_event(
            job,
            status="published",
            external_post_id=publish_result.external_post_id,
            provider=publish_result.provider or _provider_name_for_channel(job.channel),
        )
        return PublishDueOutcome(
            publish_job_id=job.id,
            status="published",
            state=job.state,
            message="published successfully",
            external_post_id=publish_result.external_post_id,
        )


def _finalize_live_publish_failure(
    *,
    publish_job_id: int,
    session_factory,
    now: datetime,
    error_message: str,
    provider: str | None,
    credential_ref: str | None = None,
    status: str = "failed",
    provider_payload: dict | None = None,
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
                message=error_message,
            )
        if job.state is not PublishJobState.PUBLISHING:
            return PublishDueOutcome(
                publish_job_id=job.id,
                status="skipped",
                state=job.state,
                message="publish job is no longer awaiting finalization",
                external_post_id=job.external_post_id,
            )

        jobs.transition_state(
            job,
            PublishJobState.FAILED,
            last_error=error_message,
            occurred_at=now,
        )
        logs.record(
            publish_job=job,
            event_type="failed",
            message=f"publish job {job.id} failed: {error_message}",
            payload=_build_failure_payload(
                job,
                error_message=error_message,
                provider=provider or _provider_name_for_channel(job.channel),
                credential_ref=credential_ref,
                status=status,
                provider_payload=provider_payload,
            ),
        )
        _log_publish_job_event(
            job,
            status="failed",
            error=error_message,
            provider=provider or _provider_name_for_channel(job.channel),
            credential_ref=credential_ref,
        )
        return PublishDueOutcome(
            publish_job_id=job.id,
            status="failed",
            state=job.state,
            message=error_message,
        )


def _build_publish_request(job: PublishJob) -> PublishRequest:
    draft = job.draft_variant
    if draft is None:
        raise ValueError(f"publish job {job.id} is missing its draft variant")

    brief = draft.content_brief
    if brief is None:
        raise ValueError(f"publish job {job.id} is missing its content brief")

    return PublishRequest(
        publish_job_id=job.id,
        draft_variant_id=draft.id,
        account_key=brief.account_key,
        channel=job.channel,
        body=draft.body,
        idempotency_key=job.idempotency_key,
    )


def _execute_live_publish(
    *,
    session_factory,
    prepared: PreparedPublish,
    executor: PublishExecutor | None,
    publisher_resolver: PublisherResolver | None,
) -> PublishResult:
    session = session_factory()
    try:
        jobs = PublishJobRepository(session)
        job = jobs.get(prepared.publish_job_id)
        if job is None:
            raise ValueError(f"publish job {prepared.publish_job_id} disappeared before execution")

        if job.state is not PublishJobState.PUBLISHING:
            raise ValueError(
                f"publish job {prepared.publish_job_id} is not ready for execution from state {job.state.value!r}"
            )

        if executor is not None:
            execution = executor.execute(job)
            return PublishResult(
                status="dry_run" if execution.dry_run else "published",
                external_post_id=execution.external_post_id,
                dry_run=execution.dry_run,
            )

        if publisher_resolver is None:
            raise ValueError("stateful publish execution requires a publisher resolver or executor")

        publisher = publisher_resolver.resolve(job)
        return publisher.publish(prepared.publish_request)
    finally:
        session.close()


def _build_success_payload(
    job: PublishJob,
    *,
    external_post_id: str,
    provider: str,
    status: str,
    provider_payload: dict | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "status": status,
        "external_post_id": external_post_id,
        "attempt_count": job.attempt_count,
        "account_key": _account_key_for_job(job),
        "channel": job.channel,
        "provider": provider,
        "retry_policy": RetryPolicy.MANUAL_RESCHEDULE.value,
    }
    if provider_payload is not None:
        payload["provider_payload"] = provider_payload
    return payload


def _build_failure_payload(
    job: PublishJob,
    *,
    error_message: str,
    provider: str,
    credential_ref: str | None = None,
    status: str = "failed",
    provider_payload: dict | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "status": status,
        "error_message": error_message,
        "attempt_count": job.attempt_count,
        "account_key": _account_key_for_job(job),
        "channel": job.channel,
        "provider": provider,
        "credential_ref": credential_ref,
        "retry_policy": RetryPolicy.MANUAL_RESCHEDULE.value,
    }
    if provider_payload is not None:
        payload["provider_payload"] = provider_payload
    return payload


def _log_publish_job_event(
    job: PublishJob,
    *,
    status: str,
    provider: str,
    external_post_id: str | None = None,
    error: str | None = None,
    credential_ref: str | None = None,
) -> None:
    fields: dict[str, object] = {
        "event": "publish_job",
        "component": "publisher",
        "status": status,
        "workflow": "publish_due",
        "publish_job_id": job.id,
        "account_key": _account_key_for_job(job),
        "channel": job.channel,
        "attempt_count": job.attempt_count,
        "provider": provider,
        "retry_policy": RetryPolicy.MANUAL_RESCHEDULE,
    }
    if credential_ref is not None:
        fields["credential_ref"] = credential_ref
    if external_post_id is not None:
        fields["external_post_id"] = external_post_id
    if error is not None:
        fields["error"] = error
    log_event(**fields)


def _account_key_for_job(job: PublishJob) -> str | None:
    draft = job.draft_variant
    if draft is None:
        return None
    brief = draft.content_brief
    if brief is None:
        return None
    return brief.account_key


def _provider_name_for_channel(channel: str) -> str:
    return channel.strip() or "unknown"


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
