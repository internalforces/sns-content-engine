#!/usr/bin/env python3
"""Build a deterministic, credential-free database for the public console demo."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.storage import (
    ArticleEnrichment,
    ContentBrief,
    DraftVariant,
    DraftVariantState,
    PipelineRun,
    PipelineRunStatus,
    PipelineStage,
    PublishJob,
    PublishJobState,
    PublishLog,
    ReviewAction,
    ReviewActionType,
    SourceItem,
    SourcePolicyMode,
    StageExecutionStatus,
    create_all_tables,
    create_database_engine,
    create_session_factory,
    session_scope,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("demo/demo.db"))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        if not args.force:
            parser.error(f"{output} already exists; pass --force to rebuild it")
        output.unlink()
    output.parent.mkdir(parents=True, exist_ok=True)

    engine = create_database_engine(f"sqlite+pysqlite:///{output}")
    create_all_tables(engine)
    session_factory = create_session_factory(engine)
    now = datetime(2026, 8, 9, 9, 0, tzinfo=timezone.utc)
    with session_scope(session_factory) as session:
        session.add_all(_pipeline_runs(now))
        for index, article in enumerate(_articles(), start=1):
            source = SourceItem(
                source_key=article["source_key"],
                external_id=f"public-demo-{index}",
                source_url=article["url"],
                title=article["title"],
                summary=article["summary"],
                policy_mode=article["policy"],
                require_attribution=True,
                created_at=now - timedelta(hours=5 - index),
            )
            session.add(source)
            session.flush()
            failed = index == 4
            session.add(
                ArticleEnrichment(
                    source_item_id=source.id,
                    source_name=article["source_name"],
                    article_url=article["url"],
                    discovered_at=source.created_at,
                    regenerated_summary=None if failed else article["summary"],
                    regenerated_key_points=[] if failed else article["points"],
                    html_fetch_status=(StageExecutionStatus.FAILED if failed else StageExecutionStatus.SUCCEEDED),
                    article_extract_status=(StageExecutionStatus.PENDING if failed else StageExecutionStatus.SUCCEEDED),
                    summary_regenerate_status=(StageExecutionStatus.PENDING if failed else StageExecutionStatus.SUCCEEDED),
                    last_stage=PipelineStage.HTML_FETCH if failed else PipelineStage.SUMMARY_REGENERATE,
                    failure_stage=PipelineStage.HTML_FETCH if failed else None,
                    failure_code="demo_upstream_timeout" if failed else None,
                    failure_message="Public demo of a recoverable upstream timeout" if failed else None,
                    created_at=source.created_at,
                    updated_at=source.created_at,
                )
            )
            if failed:
                continue
            brief = ContentBrief(
                source_item_id=source.id,
                account_key="public_demo_news",
                title=article["title"],
                summary=article["summary"],
                key_points=article["points"],
                landing_url=article["url"],
                tags=["demo", "operations"],
                created_at=source.created_at + timedelta(minutes=10),
            )
            session.add(brief)
            session.flush()
            state = DraftVariantState.PENDING_REVIEW if index < 3 else DraftVariantState.APPROVED
            draft = DraftVariant(
                content_brief_id=brief.id,
                channel="x" if index != 2 else "linkedin",
                variant_index=0,
                body=f"{article['title']} — {article['summary']} {article['url']}",
                source_name=article["source_name"],
                source_url=article["url"],
                article_url=article["url"],
                source_policy_mode=article["policy"],
                state=state,
                reviewed_at=now - timedelta(hours=1) if state is DraftVariantState.APPROVED else None,
                created_at=brief.created_at + timedelta(minutes=5),
            )
            session.add(draft)
            session.flush()
            if state is DraftVariantState.APPROVED:
                job = PublishJob(
                    draft_variant_id=draft.id,
                    channel="x",
                    idempotency_key="public-demo-published-job",
                    scheduled_for=now - timedelta(hours=1),
                    state=PublishJobState.PUBLISHED,
                    attempt_count=1,
                    external_post_id="public-demo-post-001",
                    published_at=now - timedelta(minutes=45),
                    created_at=now - timedelta(hours=2),
                    updated_at=now - timedelta(minutes=45),
                )
                session.add(job)
                session.flush()
                session.add_all(
                    [
                        ReviewAction(
                            draft_variant_id=draft.id,
                            action_type=ReviewActionType.APPROVE,
                            reviewer="demo-editor",
                            before_text=draft.body,
                            after_text=draft.body,
                            draft_state_before=DraftVariantState.PENDING_REVIEW,
                            draft_state_after=DraftVariantState.APPROVED,
                            publish_job_id=job.id,
                            created_at=now - timedelta(hours=1),
                        ),
                        PublishLog(
                            publish_job_id=job.id,
                            event_type="published",
                            message="Public demo publish completed",
                            payload={"provider": "fake", "external_post_id": job.external_post_id},
                            created_at=job.published_at,
                        ),
                    ]
                )
    engine.dispose()
    print(f"Created public demo database: {output}")


def _pipeline_runs(now: datetime) -> list[PipelineRun]:
    return [
        PipelineRun(
            workflow_name="run_local_public_demo",
            status=PipelineRunStatus.SUCCEEDED,
            started_at=now - timedelta(hours=3),
            completed_at=now - timedelta(hours=3) + timedelta(minutes=4),
            source_count=3,
            discovered_count=12,
            saved_count=8,
            enriched_count=7,
            summarized_count=7,
            brief_count=6,
            draft_count=11,
            summary_json={"policy_mode_counts": {"reusable": 8}, "policy_skipped_count": 0},
        ),
        PipelineRun(
            workflow_name="run_local_public_demo",
            status=PipelineRunStatus.PARTIAL,
            started_at=now - timedelta(days=1),
            completed_at=now - timedelta(days=1) + timedelta(minutes=6),
            source_count=3,
            discovered_count=10,
            saved_count=7,
            enriched_count=6,
            summarized_count=6,
            brief_count=5,
            draft_count=9,
            failure_count=1,
            latest_error_code="demo_upstream_timeout",
            summary_json={"policy_mode_counts": {"reusable": 7}, "policy_skipped_count": 0},
        ),
    ]


def _articles() -> list[dict[str, object]]:
    return [
        {
            "source_key": "public_technology",
            "source_name": "Example Technology Desk",
            "url": "https://example.com/demo/agent-workflows",
            "title": "Teams adopt review-first AI workflows",
            "summary": "A practical look at combining automation with accountable editorial review.",
            "points": ["Keep approval explicit", "Measure edits and outcomes"],
            "policy": SourcePolicyMode.REUSABLE,
        },
        {
            "source_key": "public_operations",
            "source_name": "Example Operations Journal",
            "url": "https://example.org/demo/content-operations",
            "title": "Content operations teams measure quality over volume",
            "summary": "Operators are tracking deduplication, edits, approvals, and publish reliability.",
            "points": ["Use stable denominators", "Review metrics over multiple weeks"],
            "policy": SourcePolicyMode.REUSABLE,
        },
        {
            "source_key": "public_product",
            "source_name": "Example Product News",
            "url": "https://example.net/demo/safe-publishing",
            "title": "Safe publishing defaults reduce duplicate posts",
            "summary": "Dry-run defaults and idempotent jobs make external side effects easier to control.",
            "points": ["Dry-run first", "Persist external IDs"],
            "policy": SourcePolicyMode.REUSABLE,
        },
        {
            "source_key": "public_resilience",
            "source_name": "Example Reliability Bulletin",
            "url": "https://example.edu/demo/upstream-resilience",
            "title": "Recovering from a temporary source timeout",
            "summary": "A simulated failure demonstrates operator-visible error context.",
            "points": ["Separate failures from policy skips"],
            "policy": SourcePolicyMode.REUSABLE,
        },
    ]


if __name__ == "__main__":
    main()
