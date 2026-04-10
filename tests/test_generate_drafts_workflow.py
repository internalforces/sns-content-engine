"""Tests for the draft generation workflow."""

from __future__ import annotations

import app.connectors.llm.openai_provider as openai_provider_module
import app.connectors.llm.codex_wrapper_provider as codex_wrapper_provider_module
from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent

import pytest

from app.connectors.llm import (
    CodexWrapperDraftGenerationProvider,
    DraftGenerationProviderError,
    FakeLLMProvider,
)
from app.storage import (
    ArticleEnrichment,
    ContentBrief,
    ContentBriefRepository,
    DraftVariantRepository,
    DraftVariantState,
    SourceItem,
    SourcePolicyMode,
    SourceItemRepository,
    create_all_tables,
    create_database_engine,
    create_session_factory,
    session_scope,
)
from app.workflows.generate_drafts import generate_drafts


def test_generate_drafts_creates_and_persists_x_variants(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path)
    _write_project_config(tmp_path)

    with session_scope(session_factory) as session:
        brief = _create_content_brief(session, account_key="ai_tools_daily")
        brief_id = brief.id

    result = generate_drafts(
        tmp_path,
        session_factory=session_factory,
        llm_provider=FakeLLMProvider(),
    )

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


def test_generate_drafts_creates_multichannel_variants_for_linkedin_and_threads(tmp_path: Path) -> None:
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
            channels:
              x:
                schedule:
                  cron: "0 9 * * *"
                render:
                  max_chars: 280
              linkedin:
                schedule:
                  cron: "0 10 * * *"
                render:
                  max_chars: 3000
              threads:
                schedule:
                  cron: "0 11 * * *"
                render:
                  max_chars: 10000
        """,
        prompts_yaml="""
        profiles:
          ai_tools_default:
            system_template: "System for {{ account_key }} on {{ channel }}"
            user_template: "Write about {{ title }} and use {{ landing_url }}"
        """,
    )

    with session_scope(session_factory) as session:
        brief = _create_content_brief(
            session,
            account_key="ai_tools_daily",
            article_url="https://example.com/articles/ai-tools-canonical",
        )
        brief_id = brief.id

    result = generate_drafts(
        tmp_path,
        session_factory=session_factory,
        llm_provider=FakeLLMProvider(),
    )

    assert result.processed_content_brief_ids == (brief_id,)
    assert result.created_count == 3
    assert result.existing_count == 0
    assert result.no_channel_count == 0
    assert result.created_variant_count == 9
    assert result.counts_by_status() == {"created": 3}

    with session_scope(session_factory) as session:
        x_drafts = DraftVariantRepository(session).list_by_content_brief_and_channel(brief_id, "x")
        linkedin_drafts = DraftVariantRepository(session).list_by_content_brief_and_channel(
            brief_id,
            "linkedin",
        )
        threads_drafts = DraftVariantRepository(session).list_by_content_brief_and_channel(
            brief_id,
            "threads",
        )

    assert len(x_drafts) == 3
    assert len(linkedin_drafts) == 3
    assert len(threads_drafts) == 3
    assert linkedin_drafts[0].body.startswith("1. One-line summary\n")
    assert "\n2. Key points\n" in linkedin_drafts[0].body
    assert linkedin_drafts[0].body.endswith("https://example.com/articles/ai-tools-canonical")
    assert threads_drafts[0].body.startswith("1. One-line summary\n")
    assert "\n8. URL\nhttps://example.com/articles/ai-tools-canonical" in threads_drafts[0].body


def test_generate_drafts_uses_article_url_when_enrichment_exists(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path)
    _write_project_config(tmp_path)

    with session_scope(session_factory) as session:
        brief = _create_content_brief(
            session,
            account_key="ai_tools_daily",
            article_url="https://example.com/articles/ai-tools-canonical",
        )
        brief_id = brief.id

    result = generate_drafts(
        tmp_path,
        session_factory=session_factory,
        llm_provider=FakeLLMProvider(),
    )

    assert result.created_count == 1

    with session_scope(session_factory) as session:
        stored_drafts = DraftVariantRepository(session).list_by_content_brief_and_channel(
            brief_id,
            "x",
        )

    assert len(stored_drafts) == 3
    assert all("https://example.com/articles/ai-tools-canonical" in draft.body for draft in stored_drafts)


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


def test_generate_drafts_creates_threads_variants_when_account_has_no_x_channel(tmp_path: Path) -> None:
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
                  cron: "0 11 * * *"
                render:
                  max_chars: 10000
        """,
        prompts_yaml="""
        profiles:
          ai_tools_default:
            system_template: "System for {{ account_key }} on {{ channel }}"
            user_template: "Write about {{ title }} and use {{ landing_url }}"
        """,
    )

    with session_scope(session_factory) as session:
        brief = _create_content_brief(session, account_key="threads_only_daily")
        brief_id = brief.id

    result = generate_drafts(
        tmp_path,
        session_factory=session_factory,
        llm_provider=FakeLLMProvider(),
    )

    assert result.processed_content_brief_ids == (brief_id,)
    assert result.created_count == 1
    assert result.existing_count == 0
    assert result.no_channel_count == 0
    assert result.created_variant_count == 3
    assert result.counts_by_status() == {"created": 1}

    with session_scope(session_factory) as session:
        stored_drafts = DraftVariantRepository(session).list_by_content_brief_and_channel(
            brief_id,
            "threads",
        )

    assert len(stored_drafts) == 3
    assert stored_drafts[0].body.startswith("1. One-line summary\n")


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
    assert result.provider_names == ("openai",)
    assert recording_client.payloads[0]["model"] == "gpt-5.4-mini"


def test_generate_drafts_shortens_overlong_openai_variants_before_storing(
    monkeypatch,
    tmp_path: Path,
) -> None:
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
            channels:
              x:
                schedule:
                  cron: "0 9 * * *"
                render:
                  max_chars: 120
        """,
    )
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    recording_client = _RecordingOpenAIClient(
        _StubOpenAIResponse(
            '{"variants":['
            '"This OpenAI draft uses too many words before the required link and needs to be shortened for X '
            'while still keeping the important article reference https://gilgop.cloud/ai-tools with trailing overflow",'
            '"Another OpenAI variant also runs long before it reaches the required link and should be trimmed down '
            'safely for storage https://gilgop.cloud/ai-tools with extra detail",'
            '"A third OpenAI variant stays verbose long enough to exceed the channel limit unless the generator '
            'compacts the supporting copy https://gilgop.cloud/ai-tools with more overflow"'
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

    assert len(stored_drafts) == 3
    assert all(len(draft.body) <= 120 for draft in stored_drafts)
    assert all(draft.body.count("https://gilgop.cloud/ai-tools") == 1 for draft in stored_drafts)
    assert all(draft.body.endswith("https://gilgop.cloud/ai-tools") for draft in stored_drafts)


def test_generate_drafts_honors_providers_yaml_routing_when_present(
    monkeypatch,
    tmp_path: Path,
) -> None:
    session_factory = _build_session_factory(tmp_path)
    _write_project_config(tmp_path)
    _write_file(
        tmp_path / "providers.yaml",
        """
        routes:
          - step: draft_generate
            provider: codex_wrapper
            model: gpt-5.4-mini
            priority: 1
          - step: draft_generate
            provider: openai
            model: gpt-5.4-mini
            priority: 2
        """,
    )
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("CODEX_WRAPPER_API_KEY", "cw-test")
    monkeypatch.setenv("CODEX_WRAPPER_BASE_URL", "https://codex-wrapper.example")
    openai_client = _RecordingOpenAIClient(
        _StubOpenAIResponse(
            '{"variants":['
            '"OpenAI first draft https://gilgop.cloud/ai-tools",'
            '"OpenAI second draft https://gilgop.cloud/ai-tools",'
            '"OpenAI third draft https://gilgop.cloud/ai-tools"'
            "]}"
        )
    )
    codex_client = _RecordingCodexWrapperClient(
        _StubCodexWrapperResponse(
            '{"variants":['
            '"Codex first draft https://gilgop.cloud/ai-tools",'
            '"Codex second draft https://gilgop.cloud/ai-tools",'
            '"Codex third draft https://gilgop.cloud/ai-tools"'
            "]}"
        )
    )
    monkeypatch.setattr(
        openai_provider_module,
        "_build_default_openai_responses_client",
        lambda **_: openai_client,
    )
    monkeypatch.setattr(
        codex_wrapper_provider_module,
        "_build_default_codex_wrapper_chat_client",
        lambda **_: codex_client,
    )

    with session_scope(session_factory) as session:
        brief = _create_content_brief(session, account_key="ai_tools_daily")
        brief_id = brief.id

    result = generate_drafts(tmp_path, session_factory=session_factory)

    assert result.created_count == 1
    assert result.provider_names == ("codex_wrapper",)
    assert openai_client.payloads == []
    assert codex_client.payloads[0]["model"] == "gpt-5.4-mini"

    with session_scope(session_factory) as session:
        stored_drafts = DraftVariantRepository(session).list_by_content_brief_and_channel(
            brief_id,
            "x",
        )

    assert [draft.body for draft in stored_drafts] == [
        "Codex first draft https://gilgop.cloud/ai-tools",
        "Codex second draft https://gilgop.cloud/ai-tools",
        "Codex third draft https://gilgop.cloud/ai-tools",
    ]


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


def test_generate_drafts_accepts_codex_wrapper_provider(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path)
    _write_project_config(tmp_path)
    provider = CodexWrapperDraftGenerationProvider(
        client=_RecordingCodexWrapperClient(
            _StubCodexWrapperResponse(
                '{"variants":['
                '"Codex first draft https://gilgop.cloud/ai-tools",'
                '"Codex second draft https://gilgop.cloud/ai-tools",'
                '"Codex third draft https://gilgop.cloud/ai-tools"'
                "]}"
            )
        )
    )

    with session_scope(session_factory) as session:
        brief = _create_content_brief(session, account_key="ai_tools_daily")
        brief_id = brief.id

    result = generate_drafts(
        tmp_path,
        session_factory=session_factory,
        llm_provider=provider,
    )

    assert result.created_count == 1

    with session_scope(session_factory) as session:
        stored_drafts = DraftVariantRepository(session).list_by_content_brief_and_channel(
            brief_id,
            "x",
        )

    assert [draft.body for draft in stored_drafts] == [
        "Codex first draft https://gilgop.cloud/ai-tools",
        "Codex second draft https://gilgop.cloud/ai-tools",
        "Codex third draft https://gilgop.cloud/ai-tools",
    ]


def test_generate_drafts_persists_source_and_policy_provenance_on_drafts(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path)
    _write_project_config(tmp_path)
    source_published_at = datetime(2026, 3, 18, 8, 30, tzinfo=timezone.utc)
    article_published_at = datetime(2026, 3, 18, 9, 45, tzinfo=timezone.utc)

    with session_scope(session_factory) as session:
        brief = _create_content_brief(
            session,
            account_key="ai_tools_daily",
            policy_mode=SourcePolicyMode.RESTRICTED,
            source_published_at=source_published_at,
            article_url="https://example.com/articles/ai-tools-canonical",
            article_source_name="AI Tools Daily",
            article_published_at=article_published_at,
        )
        brief_id = brief.id

    result = generate_drafts(tmp_path, session_factory=session_factory)

    assert result.created_count == 1

    with session_scope(session_factory) as session:
        stored_drafts = DraftVariantRepository(session).list_by_content_brief_and_channel(
            brief_id,
            "x",
        )

    assert len(stored_drafts) == 3
    assert all(draft.source_name == "AI Tools Daily" for draft in stored_drafts)
    assert all(draft.source_url == "https://example.com/ai_tools_daily/post" for draft in stored_drafts)
    assert all(draft.article_url == "https://example.com/articles/ai-tools-canonical" for draft in stored_drafts)
    assert all(draft.source_published_at == article_published_at for draft in stored_drafts)
    assert all(draft.source_policy_mode is SourcePolicyMode.RESTRICTED for draft in stored_drafts)


def _build_session_factory(tmp_path: Path):
    engine = create_database_engine(f"sqlite+pysqlite:///{tmp_path / 'drafts.db'}")
    create_all_tables(engine)
    return create_session_factory(engine)


def _create_content_brief(
    session,
    *,
    account_key: str,
    policy_mode: SourcePolicyMode = SourcePolicyMode.REUSABLE,
    source_published_at: datetime | None = None,
    article_url: str | None = None,
    article_source_name: str | None = None,
    article_published_at: datetime | None = None,
) -> ContentBrief:
    title = f"Useful AI workflow patterns for {account_key}"
    summary = f"A concise guide for operators working on {account_key}."
    source_item = SourceItemRepository(session).add(
        SourceItem(
            source_key="ai_tools_rss",
            external_id=f"{account_key}-entry",
            source_url=f"https://example.com/{account_key}/post",
            title=title,
            summary=summary,
            published_at=source_published_at,
            policy_mode=policy_mode,
        )
    )
    if article_url is not None or article_source_name is not None or article_published_at is not None:
        source_item.article_enrichment = ArticleEnrichment(
            source_item_id=source_item.id,
            source_name=article_source_name,
            article_url=article_url or source_item.source_url,
            published_at=article_published_at,
            regenerated_summary=summary,
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


def _write_project_config(
    path: Path,
    *,
    accounts_yaml: str | None = None,
    prompts_yaml: str | None = None,
) -> None:
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
        prompts_yaml
        or """
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


class _StubCodexWrapperResponse:
    def __init__(self, output_text: str) -> None:
        self.output_text = output_text
        self.choices = [_StubCodexWrapperChoice(output_text)]


class _StubCodexWrapperChoice:
    def __init__(self, output_text: str) -> None:
        self.message = _StubCodexWrapperMessage(output_text)


class _StubCodexWrapperMessage:
    def __init__(self, output_text: str) -> None:
        self.content = output_text


class _RecordingCodexWrapperClient:
    def __init__(self, response_or_exception: object) -> None:
        self._response_or_exception = response_or_exception
        self.payloads: list[object] = []

    def create_completion(self, *, payload) -> object:
        self.payloads.append(payload)
        if isinstance(self._response_or_exception, Exception):
            raise self._response_or_exception
        return self._response_or_exception
