"""Tests for the content brief builder workflow."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from app.storage import (
    ArticleEnrichment,
    ArticleEnrichmentRepository,
    ContentBrief,
    ContentBriefRepository,
    PipelineStage,
    SourceItem,
    SourceItemRepository,
    SourceItemState,
    StageExecutionStatus,
    create_all_tables,
    create_database_engine,
    create_session_factory,
    session_scope,
)
from app.workflows import build_content_briefs


def test_build_content_briefs_creates_and_persists_a_brief(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path)
    _write_project_config(
        tmp_path,
        accounts_yaml="""
        accounts:
          ai_tools_daily:
            topic: "AI tools and workflows"
            source_sets:
              - ai_tools_primary
            prompt_profile: ai_tools_default
            landing:
              fallback_url: https://gilgop.cloud/ai-tools
              rules:
                - when_tags_any:
                    - automation
                  url: https://gilgop.cloud/ai-automation
            matching:
              include_keywords:
                - automation
              source_tags:
                - automation
              strict_topic_guard: true
            channels:
              x:
                schedule:
                  cron: "0 9 * * *"
                render:
                  max_chars: 280
        """,
    )
    with session_scope(session_factory) as session:
        source_item = SourceItemRepository(session).add(
            SourceItem(
                source_key="ai_tools_rss",
                external_id="entry-1",
                source_url="https://example.com/posts/1",
                title="Automation guide for niche content teams",
                summary="A practical tutorial for repeatable review. Second point for editors.",
                raw_payload={"tags": ["automation", "ai"]},
                state=SourceItemState.INGESTED,
            )
        )
        source_item_id = source_item.id

    result = build_content_briefs(tmp_path, session_factory=session_factory)

    assert result.processed_source_item_ids == (source_item_id,)
    assert result.created_count == 1
    assert result.existing_count == 0
    assert result.no_match_count == 0
    assert result.counts_by_status() == {"created": 1}

    with session_scope(session_factory) as session:
        stored_item = SourceItemRepository(session).get(source_item_id)
        stored_briefs = ContentBriefRepository(session).list()

    assert stored_item is not None
    assert stored_item.state is SourceItemState.BRIEF_CREATED
    assert len(stored_briefs) == 1
    assert stored_briefs[0].account_key == "ai_tools_daily"
    assert stored_briefs[0].landing_url == "https://gilgop.cloud/ai-automation"
    assert stored_briefs[0].key_points == [
        "Automation guide for niche content teams",
        "A practical tutorial for repeatable review",
        "Second point for editors",
    ]
    assert stored_briefs[0].tags == ["automation", "ai"]
    assert stored_briefs[0].angle == "practical_how_to"
    assert stored_briefs[0].language == "en"


def test_build_content_briefs_creates_briefs_for_all_tied_top_matches(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path)
    _write_project_config(
        tmp_path,
        accounts_yaml="""
        accounts:
          automation_alpha:
            topic: "Automation pipelines"
            source_sets:
              - ai_tools_primary
            prompt_profile: ai_tools_default
            landing:
              fallback_url: https://gilgop.cloud/alpha
              rules: []
            matching:
              include_keywords:
                - automation
              source_tags:
                - automation
              strict_topic_guard: true
            channels:
              x:
                schedule:
                  cron: "0 9 * * *"
                render:
                  max_chars: 280
          automation_beta:
            topic: "Automation operations"
            source_sets:
              - ai_tools_primary
            prompt_profile: ai_tools_default
            landing:
              fallback_url: https://gilgop.cloud/beta
              rules: []
            matching:
              include_keywords:
                - automation
              source_tags:
                - automation
              strict_topic_guard: true
            channels:
              x:
                schedule:
                  cron: "0 9 * * *"
                render:
                  max_chars: 280
        """,
    )
    with session_scope(session_factory) as session:
        source_item = SourceItemRepository(session).add(
            SourceItem(
                source_key="ai_tools_rss",
                external_id="entry-tie",
                source_url="https://example.com/posts/tie",
                title="Automation guide for operators",
                summary="A short automation playbook.",
                raw_payload={"tags": ["automation"]},
                state=SourceItemState.INGESTED,
            )
        )
        source_item_id = source_item.id

    result = build_content_briefs(tmp_path, session_factory=session_factory)

    assert result.created_count == 2
    assert result.no_match_count == 0

    with session_scope(session_factory) as session:
        stored_briefs = ContentBriefRepository(session).list()
        stored_item = SourceItemRepository(session).get(source_item_id)

    assert stored_item is not None
    assert stored_item.state is SourceItemState.BRIEF_CREATED
    assert {brief.account_key for brief in stored_briefs} == {
        "automation_alpha",
        "automation_beta",
    }


def test_build_content_briefs_prefers_regenerated_summary_and_key_points(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path)
    _write_project_config(
        tmp_path,
        accounts_yaml="""
        accounts:
          finance_insights_daily:
            topic: "Finance market insights"
            source_sets:
              - ai_tools_primary
            prompt_profile: ai_tools_default
            landing:
              fallback_url: https://gilgop.cloud/finance
              rules: []
            matching:
              include_keywords:
                - market
              source_tags:
                - markets
              strict_topic_guard: true
            channels:
              x:
                schedule:
                  cron: "0 9 * * *"
                render:
                  max_chars: 280
        """,
    )
    with session_scope(session_factory) as session:
        source_item = SourceItemRepository(session).add(
            SourceItem(
                source_key="ai_tools_rss",
                external_id="entry-enriched",
                source_url="https://example.com/posts/markets",
                title="Market outlook resets after policy meeting",
                summary="Old RSS summary that should be replaced.",
                raw_payload={"tags": ["markets"]},
                state=SourceItemState.INGESTED,
            )
        )
        ArticleEnrichmentRepository(session).add(
            ArticleEnrichment(
                source_item_id=source_item.id,
                source_name="Finance Feed",
                article_url="https://example.com/posts/markets",
                regenerated_summary="Updated article summary built from the extracted body.",
                regenerated_key_points=[
                    "Policy comments shifted market expectations",
                    "Bond yields eased after the meeting",
                    "Banks stayed in focus for credit signals",
                ],
                tags=["markets", "policy"],
                html_fetch_status=StageExecutionStatus.SUCCEEDED,
                article_extract_status=StageExecutionStatus.SUCCEEDED,
                summary_regenerate_status=StageExecutionStatus.SUCCEEDED,
                last_stage=PipelineStage.SUMMARY_REGENERATE,
            )
        )
        source_item_id = source_item.id

    result = build_content_briefs(tmp_path, session_factory=session_factory)

    assert result.processed_source_item_ids == (source_item_id,)
    assert result.created_count == 1

    with session_scope(session_factory) as session:
        stored_brief = ContentBriefRepository(session).list()[0]

    assert stored_brief.summary == "Updated article summary built from the extracted body."
    assert stored_brief.key_points == [
        "Policy comments shifted market expectations",
        "Bond yields eased after the meeting",
        "Banks stayed in focus for credit signals",
    ]
    assert stored_brief.tags == ["markets", "policy"]



def test_build_content_briefs_records_no_match_without_changing_source_state(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path)
    _write_project_config(
        tmp_path,
        accounts_yaml="""
        accounts:
          finance_news_daily:
            topic: "Finance markets and investing"
            source_sets:
              - ai_tools_primary
            prompt_profile: ai_tools_default
            landing:
              fallback_url: https://gilgop.cloud/finance
              rules: []
            matching:
              include_keywords:
                - earnings
              source_tags:
                - finance
              strict_topic_guard: true
            channels:
              x:
                schedule:
                  cron: "0 9 * * *"
                render:
                  max_chars: 280
        """,
    )
    with session_scope(session_factory) as session:
        source_item = SourceItemRepository(session).add(
            SourceItem(
                source_key="ai_tools_rss",
                external_id="entry-no-match",
                source_url="https://example.com/posts/no-match",
                title="Automation workflow for editorial teams",
                summary="Operators document repeatable review flows.",
                raw_payload={"tags": ["automation"]},
                state=SourceItemState.INGESTED,
            )
        )
        source_item_id = source_item.id

    result = build_content_briefs(tmp_path, session_factory=session_factory)

    assert result.created_count == 0
    assert result.existing_count == 0
    assert result.no_match_count == 1
    assert result.counts_by_status() == {"no_match": 1}

    with session_scope(session_factory) as session:
        stored_item = SourceItemRepository(session).get(source_item_id)
        stored_briefs = ContentBriefRepository(session).list()

    assert stored_item is not None
    assert stored_item.state is SourceItemState.INGESTED
    assert stored_briefs == []


def test_build_content_briefs_reports_existing_brief_without_duplication(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path)
    _write_project_config(
        tmp_path,
        accounts_yaml="""
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
                - automation
              source_tags:
                - automation
              strict_topic_guard: true
            channels:
              x:
                schedule:
                  cron: "0 9 * * *"
                render:
                  max_chars: 280
        """,
    )
    with session_scope(session_factory) as session:
        source_item = SourceItemRepository(session).add(
            SourceItem(
                source_key="ai_tools_rss",
                external_id="entry-existing",
                source_url="https://example.com/posts/existing",
                title="Automation workflow for editorial teams",
                summary="Operators document repeatable review flows.",
                raw_payload={"tags": ["automation"]},
                state=SourceItemState.INGESTED,
            )
        )
        ContentBriefRepository(session).add(
            ContentBrief(
                source_item_id=source_item.id,
                account_key="ai_tools_daily",
                title=source_item.title,
                summary=source_item.summary,
                key_points=[source_item.title],
                landing_url="https://gilgop.cloud/ai-tools",
                tags=["automation"],
                angle="topic_takeaway",
                language="en",
            )
        )
        source_item_id = source_item.id

    result = build_content_briefs(tmp_path, session_factory=session_factory)

    assert result.created_count == 0
    assert result.existing_count == 1
    assert result.no_match_count == 0

    with session_scope(session_factory) as session:
        stored_item = SourceItemRepository(session).get(source_item_id)
        stored_briefs = ContentBriefRepository(session).list()

    assert stored_item is not None
    assert stored_item.state is SourceItemState.BRIEF_CREATED
    assert len(stored_briefs) == 1


def test_build_content_briefs_filters_accounts_by_source_set_membership(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path)
    _write_project_config(
        tmp_path,
        accounts_yaml="""
        accounts:
          connected_daily:
            topic: "Automation pipelines"
            source_sets:
              - ai_tools_primary
            prompt_profile: ai_tools_default
            landing:
              fallback_url: https://gilgop.cloud/connected
              rules: []
            matching:
              include_keywords:
                - automation
              source_tags:
                - automation
              strict_topic_guard: true
            channels:
              x:
                schedule:
                  cron: "0 9 * * *"
                render:
                  max_chars: 280
          disconnected_daily:
            topic: "Automation pipelines"
            source_sets:
              - finance_primary
            prompt_profile: ai_tools_default
            landing:
              fallback_url: https://gilgop.cloud/disconnected
              rules: []
            matching:
              include_keywords:
                - automation
              source_tags:
                - automation
              strict_topic_guard: true
            channels:
              x:
                schedule:
                  cron: "0 9 * * *"
                render:
                  max_chars: 280
        """,
        sources_yaml="""
        sources:
          ai_tools_rss:
            type: rss
            url: https://example.com/ai.xml
          finance_rss:
            type: rss
            url: https://example.com/finance.xml

        source_sets:
          ai_tools_primary:
            sources:
              - ai_tools_rss
          finance_primary:
            sources:
              - finance_rss
        """,
    )
    with session_scope(session_factory) as session:
        SourceItemRepository(session).add(
            SourceItem(
                source_key="ai_tools_rss",
                external_id="entry-filter",
                source_url="https://example.com/posts/filter",
                title="Automation guide for operators",
                summary="A short automation playbook.",
                raw_payload={"tags": ["automation"]},
                state=SourceItemState.INGESTED,
            )
        )

    result = build_content_briefs(tmp_path, session_factory=session_factory)

    assert result.created_count == 1

    with session_scope(session_factory) as session:
        stored_briefs = ContentBriefRepository(session).list()

    assert [brief.account_key for brief in stored_briefs] == ["connected_daily"]


def _build_session_factory(tmp_path: Path):
    engine = create_database_engine(f"sqlite+pysqlite:///{tmp_path / 'briefs.db'}")
    create_all_tables(engine)
    return create_session_factory(engine)


def _write_project_config(
    path: Path,
    *,
    accounts_yaml: str,
    sources_yaml: str | None = None,
    prompts_yaml: str | None = None,
) -> None:
    _write_file(path / "accounts.yaml", accounts_yaml)
    _write_file(
        path / "prompts.yaml",
        prompts_yaml
        or """
        profiles:
          ai_tools_default:
            system_template: "system"
            user_template: "user"
        """,
    )
    _write_file(
        path / "sources.yaml",
        sources_yaml
        or """
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
