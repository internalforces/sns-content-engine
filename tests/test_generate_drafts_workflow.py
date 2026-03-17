"""Tests for the draft generation workflow."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from app.storage import (
    ContentBrief,
    ContentBriefRepository,
    DraftVariantRepository,
    DraftVariantState,
    SourceItem,
    SourceItemRepository,
    create_all_tables,
    create_database_engine,
    create_session_factory,
    session_scope,
)
from app.workflows import generate_drafts


def test_generate_drafts_creates_and_persists_x_variants(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path)
    _write_project_config(tmp_path)

    with session_scope(session_factory) as session:
        brief = _create_content_brief(session, account_key="ai_tools_daily")
        brief_id = brief.id

    result = generate_drafts(tmp_path, session_factory=session_factory)

    assert result.processed_content_brief_ids == (brief_id,)
    assert result.created_count == 1
    assert result.existing_count == 0
    assert result.no_channel_count == 0
    assert result.created_variant_count == 3
    assert result.counts_by_status() == {"created": 1}

    with session_scope(session_factory) as session:
        stored_drafts = DraftVariantRepository(session).list_by_content_brief_and_channel(brief_id, "x")

    assert len(stored_drafts) == 3
    assert [draft.variant_index for draft in stored_drafts] == [0, 1, 2]
    assert all(draft.state is DraftVariantState.PENDING_REVIEW for draft in stored_drafts)
    assert all("https://gilgop.cloud/ai-tools" in draft.body for draft in stored_drafts)


def test_generate_drafts_is_idempotent_when_x_drafts_already_exist(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path)
    _write_project_config(tmp_path)

    with session_scope(session_factory) as session:
        brief = _create_content_brief(session, account_key="ai_tools_daily")
        brief_id = brief.id

    first = generate_drafts(tmp_path, session_factory=session_factory)
    second = generate_drafts(tmp_path, session_factory=session_factory)

    assert first.created_count == 1
    assert first.created_variant_count == 3
    assert second.created_count == 0
    assert second.existing_count == 1
    assert second.created_variant_count == 0
    assert second.counts_by_status() == {"existing": 1}

    with session_scope(session_factory) as session:
        stored_drafts = DraftVariantRepository(session).list_by_content_brief_and_channel(brief_id, "x")

    assert len(stored_drafts) == 3


def test_generate_drafts_reports_no_channel_when_account_lacks_x(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path)
    _write_project_config(
        tmp_path,
        accounts_yaml="""
        accounts:
          threads_only_daily:
            topic: "AI tools and workflows"
            source_sets:
              - ai_tools_primary
            prompt_profile: ai_tools_default
            landing:
              fallback_url: https://gilgop.cloud/ai-tools
              rules: []
            channels:
              threads:
                schedule:
                  cron: "0 9 * * *"
                render:
                  max_chars: 280
        """,
    )

    with session_scope(session_factory) as session:
        brief = _create_content_brief(session, account_key="threads_only_daily")
        brief_id = brief.id

    result = generate_drafts(tmp_path, session_factory=session_factory)

    assert result.processed_content_brief_ids == (brief_id,)
    assert result.created_count == 0
    assert result.existing_count == 0
    assert result.no_channel_count == 1
    assert result.created_variant_count == 0
    assert result.counts_by_status() == {"no_channel": 1}

    with session_scope(session_factory) as session:
        stored_drafts = DraftVariantRepository(session).list()

    assert stored_drafts == []


def test_generate_drafts_rejects_invalid_variant_count(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path)
    _write_project_config(tmp_path)

    with pytest.raises(ValueError, match="variant_count must be 2 or 3"):
        generate_drafts(tmp_path, session_factory=session_factory, variant_count=4)


def _build_session_factory(tmp_path: Path):
    engine = create_database_engine(f"sqlite+pysqlite:///{tmp_path / 'drafts.db'}")
    create_all_tables(engine)
    return create_session_factory(engine)


def _create_content_brief(session, *, account_key: str) -> ContentBrief:
    source_item = SourceItemRepository(session).add(
        SourceItem(
            source_key="ai_tools_rss",
            external_id=f"{account_key}-entry",
            source_url=f"https://example.com/{account_key}/post",
            title="Useful AI workflow patterns",
            summary="A concise guide for operators.",
        )
    )
    return ContentBriefRepository(session).add(
        ContentBrief(
            source_item_id=source_item.id,
            account_key=account_key,
            title="Useful AI workflow patterns",
            summary="A concise guide for operators.",
            key_points=[
                "Useful AI workflow patterns",
                "Tight review loops",
                "Better scheduling",
            ],
            landing_url="https://gilgop.cloud/ai-tools",
            tags=["ai", "automation"],
            angle="practical_how_to",
            language="en",
        )
    )


def _write_project_config(path: Path, *, accounts_yaml: str | None = None) -> None:
    _write_file(
        path / "accounts.yaml",
        accounts_yaml
        or """
        accounts:
          ai_tools_daily:
            topic: "AI tools and workflows"
            source_sets:
              - ai_tools_primary
            prompt_profile: ai_tools_default
            landing:
              fallback_url: https://gilgop.cloud/ai-tools
              rules: []
            channels:
              x:
                schedule:
                  cron: "0 9 * * *"
                render:
                  max_chars: 280
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
