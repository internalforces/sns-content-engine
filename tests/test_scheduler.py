"""Tests for scheduler planning and job execution."""

from __future__ import annotations

from datetime import datetime, timezone
from itertools import count
from pathlib import Path
from textwrap import dedent

import pytest

from app.config import ScheduleConfig
from app.scheduler import (
    FakePublishExecutor,
    SlotPlanner,
    SlotPlanningRequest,
    backfill_publish_jobs,
    publish_due_jobs,
)
from app.storage import (
    ContentBrief,
    ContentBriefRepository,
    DraftVariant,
    DraftVariantRepository,
    DraftVariantState,
    PublishJob,
    PublishJobRepository,
    PublishJobState,
    PublishLogRepository,
    ReviewActionRepository,
    SourceItem,
    SourceItemRepository,
    create_all_tables,
    create_database_engine,
    create_session_factory,
    session_scope,
)

_DRAFT_SOURCE_COUNTER = count()


@pytest.fixture
def session_factory(tmp_path):
    engine = create_database_engine(f"sqlite+pysqlite:///{tmp_path / 'scheduler.db'}")
    create_all_tables(engine)
    factory = create_session_factory(engine)
    yield factory
    engine.dispose()


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    _write_project_config(tmp_path)
    return tmp_path


def test_slot_planner_is_deterministic_for_same_request() -> None:
    planner = SlotPlanner()
    request = SlotPlanningRequest(
        account_key="ai_tools_daily",
        channel="x",
        schedule=ScheduleConfig(
            cron="0 9 * * *",
            window_minutes=30,
            jitter_minutes=10,
            min_gap_minutes=0,
            backlog_target=2,
        ),
        now=datetime(2026, 3, 18, 8, 30, tzinfo=timezone.utc),
        target_slot_count=2,
    )

    first = planner.plan(request)
    second = planner.plan(request)

    assert first == second
    assert len(first.slots) == 2


def test_slot_planner_keeps_account_channel_pairs_independent() -> None:
    planner = SlotPlanner()
    schedule = ScheduleConfig(
        cron="0 9 * * *",
        window_minutes=30,
        jitter_minutes=30,
        min_gap_minutes=0,
        backlog_target=1,
    )
    now = datetime(2026, 3, 18, 8, 0, tzinfo=timezone.utc)

    first = planner.plan(
        SlotPlanningRequest(
            account_key="ai_tools_daily",
            channel="x",
            schedule=schedule,
            now=now,
            target_slot_count=1,
        )
    )
    second = planner.plan(
        SlotPlanningRequest(
            account_key="finance_news_daily",
            channel="x",
            schedule=schedule,
            now=now,
            target_slot_count=1,
        )
    )

    assert len(first.slots) == 1
    assert len(second.slots) == 1
    assert first.slots[0].scheduled_for != second.slots[0].scheduled_for


def test_slot_planner_honors_window_jitter_and_min_gap() -> None:
    planner = SlotPlanner()
    result = planner.plan(
        SlotPlanningRequest(
            account_key="ai_tools_daily",
            channel="x",
            schedule=ScheduleConfig(
                cron="0 9 * * *",
                window_minutes=20,
                jitter_minutes=10,
                min_gap_minutes=5,
                backlog_target=1,
            ),
            now=datetime(2026, 3, 18, 9, 3, tzinfo=timezone.utc),
            occupied_times=(datetime(2026, 3, 18, 9, 7, tzinfo=timezone.utc),),
            target_slot_count=1,
        )
    )

    assert len(result.slots) == 1
    slot = result.slots[0]
    assert slot.window_start == datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc)
    assert slot.window_end == datetime(2026, 3, 18, 9, 20, tzinfo=timezone.utc)
    assert slot.scheduled_for >= datetime(2026, 3, 18, 9, 3, tzinfo=timezone.utc)
    assert slot.scheduled_for <= datetime(2026, 3, 18, 9, 20, tzinfo=timezone.utc)
    assert abs(slot.scheduled_for - datetime(2026, 3, 18, 9, 7, tzinfo=timezone.utc)).total_seconds() >= 300


def test_slot_planner_drops_anchor_when_min_gap_exceeds_window() -> None:
    planner = SlotPlanner()
    result = planner.plan(
        SlotPlanningRequest(
            account_key="ai_tools_daily",
            channel="x",
            schedule=ScheduleConfig(
                cron="0 9 * * *",
                window_minutes=5,
                jitter_minutes=0,
                min_gap_minutes=10,
                backlog_target=1,
            ),
            now=datetime(2026, 3, 18, 8, 0, tzinfo=timezone.utc),
            occupied_times=(datetime(2026, 3, 18, 9, 8, tzinfo=timezone.utc),),
            target_slot_count=1,
        )
    )

    assert len(result.slots) == 1
    assert result.anchors_considered >= 2
    assert result.slots[0].anchor_time == datetime(2026, 3, 19, 9, 0, tzinfo=timezone.utc)


def test_backfill_creates_only_missing_jobs_and_records_schedule_logs(session_factory, config_dir) -> None:
    with session_scope(session_factory) as session:
        approved_early = _create_draft_variant(
            session,
            draft_state=DraftVariantState.APPROVED,
            reviewed_at=datetime(2026, 3, 18, 7, 0, tzinfo=timezone.utc),
        )
        approved_late = _create_draft_variant(
            session,
            draft_state=DraftVariantState.APPROVED,
            reviewed_at=datetime(2026, 3, 18, 7, 30, tzinfo=timezone.utc),
        )
        _create_draft_variant(session, draft_state=DraftVariantState.PENDING_REVIEW)
        with_active_job = _create_draft_variant(
            session,
            draft_state=DraftVariantState.APPROVED,
            reviewed_at=datetime(2026, 3, 18, 7, 45, tzinfo=timezone.utc),
        )
        PublishJobRepository(session).add(
            PublishJob(
                draft_variant=with_active_job,
                channel="x",
                idempotency_key="existing-future-job",
                scheduled_for=datetime(2026, 3, 18, 12, 0, tzinfo=timezone.utc),
            )
        )

    result = backfill_publish_jobs(
        config_dir=config_dir,
        session_factory=session_factory,
        now=datetime(2026, 3, 18, 8, 0, tzinfo=timezone.utc),
    )

    assert result.processed_channel_count == 2
    ai_outcome = next(outcome for outcome in result.outcomes if outcome.account_key == "ai_tools_daily")
    assert ai_outcome.backlog_target == 2
    assert ai_outcome.existing_future_job_count == 1
    assert ai_outcome.created_count == 1
    assert ai_outcome.skipped_slot_count == 0
    assert ai_outcome.eligible_draft_count == 2

    with session_scope(session_factory) as session:
        jobs = PublishJobRepository(session).list_active_for_account_channel("ai_tools_daily", "x")
        logs = PublishLogRepository(session).list()

    assert len(jobs) == 2
    created_job = next(job for job in jobs if job.draft_variant_id == approved_early.id)
    assert created_job.scheduled_for == datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc)
    assert approved_late.id not in [job.draft_variant_id for job in jobs if job.draft_variant_id != created_job.draft_variant_id]
    assert [log.event_type for log in logs] == ["scheduled"]


def test_backfill_skips_channels_with_no_approved_drafts(session_factory, config_dir) -> None:
    result = backfill_publish_jobs(
        config_dir=config_dir,
        session_factory=session_factory,
        now=datetime(2026, 3, 18, 8, 0, tzinfo=timezone.utc),
    )

    finance_outcome = next(outcome for outcome in result.outcomes if outcome.account_key == "finance_news_daily")
    assert finance_outcome.created_count == 0
    assert finance_outcome.skipped_slot_count == 1


def test_publish_due_jobs_marks_jobs_published_with_fake_executor(session_factory) -> None:
    with session_scope(session_factory) as session:
        draft = _create_draft_variant(session, draft_state=DraftVariantState.APPROVED)
        job = PublishJobRepository(session).add(
            PublishJob(
                draft_variant=draft,
                channel="x",
                idempotency_key="due-job",
                scheduled_for=datetime(2026, 3, 18, 8, 0, tzinfo=timezone.utc),
            )
        )
        job_id = job.id

    result = publish_due_jobs(
        session_factory=session_factory,
        now=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
    )

    assert result.dry_run is True
    assert result.published_count == 1
    assert result.failed_count == 0

    with session_scope(session_factory) as session:
        stored_job = PublishJobRepository(session).get(job_id)
        logs = PublishLogRepository(session).list_for_job(job_id)

    assert stored_job is not None
    assert stored_job.state is PublishJobState.PUBLISHED
    assert stored_job.external_post_id == f"dry-run:{job_id}"
    assert stored_job.attempt_count == 1
    assert [log.event_type for log in logs] == ["publishing", "published"]


def test_publish_due_jobs_fail_independently_per_job(session_factory) -> None:
    with session_scope(session_factory) as session:
        failing_draft = _create_draft_variant(session, draft_state=DraftVariantState.APPROVED)
        passing_draft = _create_draft_variant(session, draft_state=DraftVariantState.APPROVED)
        failing_job = PublishJobRepository(session).add(
            PublishJob(
                draft_variant=failing_draft,
                channel="x",
                idempotency_key="failing-job",
                scheduled_for=datetime(2026, 3, 18, 8, 0, tzinfo=timezone.utc),
            )
        )
        passing_job = PublishJobRepository(session).add(
            PublishJob(
                draft_variant=passing_draft,
                channel="x",
                idempotency_key="passing-job",
                scheduled_for=datetime(2026, 3, 18, 8, 5, tzinfo=timezone.utc),
            )
        )

    class MixedExecutor(FakePublishExecutor):
        def execute(self, job: PublishJob):
            if job.id == failing_job.id:
                raise RuntimeError("boom")
            return super().execute(job)

    result = publish_due_jobs(
        session_factory=session_factory,
        executor=MixedExecutor(),
        now=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
    )

    assert result.processed_count == 2
    assert result.published_count == 1
    assert result.failed_count == 1

    with session_scope(session_factory) as session:
        stored_failing_job = PublishJobRepository(session).get(failing_job.id)
        stored_passing_job = PublishJobRepository(session).get(passing_job.id)
        failing_logs = PublishLogRepository(session).list_for_job(failing_job.id)
        passing_logs = PublishLogRepository(session).list_for_job(passing_job.id)

    assert stored_failing_job is not None
    assert stored_failing_job.state is PublishJobState.FAILED
    assert stored_failing_job.last_error == "boom"
    assert [log.event_type for log in failing_logs] == ["publishing", "failed"]

    assert stored_passing_job is not None
    assert stored_passing_job.state is PublishJobState.PUBLISHED
    assert stored_passing_job.external_post_id == f"dry-run:{passing_job.id}"
    assert [log.event_type for log in passing_logs] == ["publishing", "published"]


def _create_draft_variant(
    session,
    *,
    draft_state: DraftVariantState = DraftVariantState.PENDING_REVIEW,
    account_key: str = "ai_tools_daily",
    channel: str = "x",
    reviewed_at: datetime | None = None,
) -> DraftVariant:
    source_id = next(_DRAFT_SOURCE_COUNTER)
    source_item = SourceItemRepository(session).add(
        SourceItem(
            source_key="ai_tools_rss",
            external_id=f"scheduler-draft-{source_id}",
            source_url=f"https://example.com/scheduler/{source_id}",
            title=f"Scheduler draft {source_id}",
            summary="Brief summary",
        )
    )
    brief = ContentBriefRepository(session).add(
        ContentBrief(
            source_item=source_item,
            account_key=account_key,
            title="Brief for scheduler draft",
            summary="Brief summary",
            key_points=["Brief for scheduler draft"],
            landing_url="https://gilgop.cloud/ai-tools",
            tags=["ai"],
            angle="topic_takeaway",
            language="en",
        )
    )
    repository = DraftVariantRepository(session)
    draft = repository.add(
        DraftVariant(
            content_brief=brief,
            channel=channel,
            variant_index=0,
            body="Useful AI automation workflows for operators https://gilgop.cloud/ai-tools",
        )
    )
    if draft_state is DraftVariantState.APPROVED:
        repository.transition_state(
            draft,
            DraftVariantState.APPROVED,
            reviewed_at=reviewed_at or datetime(2026, 3, 18, 7, 0, tzinfo=timezone.utc),
        )
    elif draft_state is DraftVariantState.REJECTED:
        repository.transition_state(
            draft,
            DraftVariantState.REJECTED,
            rejection_reason="Rejected during test setup",
            reviewed_at=reviewed_at or datetime(2026, 3, 18, 7, 0, tzinfo=timezone.utc),
        )
    return draft


def _write_project_config(path: Path) -> None:
    _write_file(
        path / "accounts.yaml",
        """
        accounts:
          ai_tools_daily:
            topic: "AI tools and workflows"
            source_sets:
              - ai_tools_primary
            prompt_profile: ai_tools_default
            landing:
              fallback_url: https://gilgop.cloud/ai-tools
              rules: []
            matching:
              include_keywords:
                - ai
              source_tags:
                - ai
            channels:
              x:
                schedule:
                  cron: "0 9 * * *"
                  window_minutes: 0
                  jitter_minutes: 0
                  min_gap_minutes: 0
                  backlog_target: 2
                render:
                  max_chars: 280
                validation:
                  max_links: 1
                  banned_phrases: []
                  recent_duplicate_window_days: 7
          finance_news_daily:
            topic: "Finance headlines"
            source_sets:
              - ai_tools_primary
            prompt_profile: ai_tools_default
            landing:
              fallback_url: https://gilgop.cloud/finance
              rules: []
            matching:
              include_keywords:
                - finance
              source_tags:
                - finance
            channels:
              x:
                schedule:
                  cron: "0 10 * * *"
                  window_minutes: 0
                  jitter_minutes: 0
                  min_gap_minutes: 0
                  backlog_target: 1
                render:
                  max_chars: 280
                validation:
                  max_links: 1
                  banned_phrases: []
                  recent_duplicate_window_days: 7
        """,
    )
    _write_file(
        path / "prompts.yaml",
        """
        profiles:
          ai_tools_default:
            system_template: "System for {{ account_key }} on {{ channel }}"
            user_template: "Write about {{ title }} and use {{ landing_url }}"
        """,
    )
    _write_file(
        path / "sources.yaml",
        """
        sources:
          ai_tools_rss:
            type: rss
            url: https://example.com/feed.xml

        source_sets:
          ai_tools_primary:
            sources:
              - ai_tools_rss
        """,
    )


def _write_file(path: Path, content: str) -> None:
    path.write_text(dedent(content).strip() + "\n", encoding="utf-8")
