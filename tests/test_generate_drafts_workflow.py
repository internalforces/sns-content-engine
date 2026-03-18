"""Tests for the draft generation workflow."""

from __future__ import annotations

import app.connectors.llm.openai_provider as openai_provider_module
from pathlib import Path
from textwrap import dedent

import pytest

from app.connectors.llm import DraftGenerationProviderError
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


def test_generate_drafts_skips_missing_account_and_continues_processing(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path)
    _write_project_config(tmp_path)

    with session_scope(session_factory) as session:
        missing_brief = _create_content_brief(session, account_key="deleted_daily")
        active_brief = _create_content_brief(session, account_key="ai_tools_daily")
        active_brief_id = active_brief.id

    result = generate_drafts(tmp_path, session_factory=session_factory)

    assert result.processed_content_brief_ids == (missing_brief.id, active_brief_id)
    assert result.created_count == 1
    assert result.existing_count == 0
    assert result.no_channel_count == 0
    assert result.missing_account_count == 1
    assert result.created_variant_count == 3
    assert result.counts_by_status() == {"created": 1, "missing_account": 1}

    with session_scope(session_factory) as session:
        stored_drafts = DraftVariantRepository(session).list_by_content_brief_and_channel(
            active_brief_id,
            "x",
        )

    assert len(stored_drafts) == 3


def test_generate_drafts_rejects_invalid_variant_count(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path)
    _write_project_config(tmp_path)

    with pytest.raises(ValueError, match="variant_count must be 2 or 3"):
        generate_drafts(tmp_path, session_factory=session_factory, variant_count=4)


def test_generate_drafts_uses_fake_provider_when_openai_key_is_absent(
    monkeypatch,
    tmp_path: Path,
) -> None:
    session_factory = _build_session_factory(tmp_path)
    _write_project_config(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with session_scope(session_factory) as session:
        brief = _create_content_brief(session, account_key="ai_tools_daily")
        brief_id = brief.id

    generate_drafts(tmp_path, session_factory=session_factory)

    with session_scope(session_factory) as session:
        stored_drafts = DraftVariantRepository(session).list_by_content_brief_and_channel(brief_id, "x")

    assert len(stored_drafts) == 3
    assert stored_drafts[0].body.startswith("Practical takeaway:")


def test_generate_drafts_uses_openai_provider_when_api_key_is_present(
    monkeypatch,
    tmp_path: Path,
) -> None:
    session_factory = _build_session_factory(tmp_path)
    _write_project_config(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    recording_client = _RecordingOpenAIClient(
        _StubOpenAIResponse(
            '{"variants":['
            '"OpenAI first draft https://gilgop.cloud/ai-tools",'
            '"OpenAI second draft https://gilgop.cloud/ai-tools",'
            '"OpenAI third draft https://gilgop.cloud/ai-tools"'
            "]}"
        )
    )
    monkeypatch.setattr(
        openai_provider_module,
        "_build_default_openai_responses_client",
        lambda **_: recording_client,
    )

    with session_scope(session_factory) as session:
        brief = _create_content_brief(session, account_key="ai_tools_daily")
        brief_id = brief.id

    result = generate_drafts(tmp_path, session_factory=session_factory)

    assert result.created_count == 1

    with session_scope(session_factory) as session:
        stored_drafts = DraftVariantRepository(session).list_by_content_brief_and_channel(brief_id, "x")

    assert [draft.body for draft in stored_drafts] == [
        "OpenAI first draft https://gilgop.cloud/ai-tools",
        "OpenAI second draft https://gilgop.cloud/ai-tools",
        "OpenAI third draft https://gilgop.cloud/ai-tools",
    ]
    assert recording_client.payloads[0]["model"] == "gpt-5.4-mini"


def test_generate_drafts_aborts_when_openai_provider_fails(monkeypatch, tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path)
    _write_project_config(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(
        openai_provider_module,
        "_build_default_openai_responses_client",
        lambda **_: _RecordingOpenAIClient(RuntimeError("boom")),
    )

    with session_scope(session_factory) as session:
        brief = _create_content_brief(session, account_key="ai_tools_daily")
        brief_id = brief.id

    with pytest.raises(DraftGenerationProviderError, match="OpenAI draft generation request failed: boom"):
        generate_drafts(tmp_path, session_factory=session_factory)

    with session_scope(session_factory) as session:
        stored_drafts = DraftVariantRepository(session).list_by_content_brief_and_channel(brief_id, "x")

    assert stored_drafts == []


def _build_session_factory(tmp_path: Path):
    engine = create_database_engine(f"sqlite+pysqlite:///{tmp_path / 'drafts.db'}")
    create_all_tables(engine)
    return create_session_factory(engine)


def _create_content_brief(session, *, account_key: str) -> ContentBrief:
    title = f"Useful AI workflow patterns for {account_key}"
    summary = f"A concise guide for operators working on {account_key}."
    source_item = SourceItemRepository(session).add(
        SourceItem(
            source_key="ai_tools_rss",
            external_id=f"{account_key}-entry",
            source_url=f"https://example.com/{account_key}/post",
            title=title,
            summary=summary,
        )
    )
    return ContentBriefRepository(session).add(
        ContentBrief(
            source_item_id=source_item.id,
            account_key=account_key,
            title=title,
            summary=summary,
            key_points=[
                title,
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


class _StubOpenAIResponse:
    def __init__(self, output_text: str) -> None:
        self.output_text = output_text


class _RecordingOpenAIClient:
    def __init__(self, response_or_exception: object) -> None:
        self._response_or_exception = response_or_exception
        self.payloads: list[object] = []

    def create_response(self, *, payload) -> object:
        self.payloads.append(payload)
        if isinstance(self._response_or_exception, Exception):
            raise self._response_or_exception
        return self._response_or_exception
