"""Tests for the one-shot local finance pipeline workflow."""

from __future__ import annotations

import app.connectors.llm.codex_wrapper_provider as codex_wrapper_provider_module
import app.connectors.llm.openai_provider as openai_provider_module
from datetime import datetime, timezone
from pathlib import Path

from app.connectors.llm import FakeLLMProvider
from app.domain import SourceConnectorResult, SourceItemCandidate
from app.storage import (
    DraftVariantRepository,
    PipelineRunRepository,
    PipelineRunStageRepository,
    PipelineRunStatus,
    SourceItem,
    SourceItemRepository,
    create_all_tables,
    create_database_engine,
    create_session_factory,
    session_scope,
)
from app.workflows.run_local_pipeline import run_local_pipeline


class _FakeFetcher:
    def fetch(self, article_url: str):
        return type("FetchResult", (), {"article_url": article_url, "final_url": article_url, "html": "<html>finance</html>"})()


class _FakeExtractor:
    def extract(self, html: str):
        return type("ExtractResult", (), {
            "title": "Central bank update shifts markets",
            "source_name": "Finance Feed",
            "published_at": datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
            "article_text": "Markets reacted to policy signals while bonds, banks, inflation, revenue, and credit all stayed in focus for the next session.",
            "metadata": {"og:site_name": "Finance Feed"},
        })()


class _FakeRegenerator:
    def regenerate(self, *, title: str, article_text: str, rss_description: str | None = None):
        return type("Regenerated", (), {
            "summary": "Central bank update shifts markets: Policy signals reset the near-term outlook.",
            "key_points": (
                "Policy signals reset the near-term outlook",
                "Bonds and banks stayed in focus",
                "Inflation and credit shaped the reaction",
            ),
        })()


class _StaticSourceConnector:
    def __init__(self, items_by_source: dict[str, tuple[SourceItemCandidate, ...]]) -> None:
        self._items_by_source = items_by_source

    def discover(self, source_id: str, source_config) -> SourceConnectorResult:
        return SourceConnectorResult(items=self._items_by_source.get(source_id, ()))


class _StaticConnectorRegistry:
    def __init__(self, items_by_source: dict[str, tuple[SourceItemCandidate, ...]]) -> None:
        self._connector = _StaticSourceConnector(items_by_source)

    def get_connector(self, source_config):
        return self._connector


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


def test_run_local_pipeline_records_run_history_and_generates_pending_review_drafts(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path)
    _write_project_config(tmp_path)

    result = run_local_pipeline(
        tmp_path,
        session_factory=session_factory,
        connector_registry=_StaticConnectorRegistry(
            {
                "finance_rss": (
                    SourceItemCandidate(
                        source_id="finance_rss",
                        external_id="finance-1",
                        source_url="https://example.com/articles/finance-1",
                        title="Central bank update shifts markets",
                        summary="RSS summary that will be superseded.",
                        raw_payload={"feed_title": "Finance Feed", "tags": ["markets", "policy"]},
                    ),
                )
            }
        ),
        llm_provider=FakeLLMProvider(),
        html_fetcher=_FakeFetcher(),
        article_extractor=_FakeExtractor(),
        summary_regenerator=_FakeRegenerator(),
        now=datetime(2026, 3, 18, 10, 0, tzinfo=timezone.utc),
    )

    assert result.status is PipelineRunStatus.SUCCEEDED
    assert result.ingest_discovered_count == 1
    assert result.ingest_saved_count == 1
    assert result.enrichment_enriched_count == 1
    assert result.brief_created_count == 1
    assert result.draft_created_variant_count == 3
    assert result.failure_count == 0

    with session_scope(session_factory) as session:
        pipeline_runs = PipelineRunRepository(session).list()
        stage_rows = PipelineRunStageRepository(session).list_for_run(pipeline_runs[0].id)
        source_items = SourceItemRepository(session).list()

    assert len(pipeline_runs) == 1
    assert pipeline_runs[0].workflow_name == "run_local_finance"
    assert len(stage_rows) >= 5
    assert len(source_items) == 1


def test_run_local_pipeline_honors_providers_yaml_for_draft_generation(
    monkeypatch,
    tmp_path: Path,
) -> None:
    session_factory = _build_session_factory(tmp_path)
    _write_project_config(tmp_path)
    (tmp_path / "providers.yaml").write_text(
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
""".strip() + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("CODEX_WRAPPER_API_KEY", "cw-test")
    monkeypatch.setenv("CODEX_WRAPPER_BASE_URL", "https://codex-wrapper.example")
    openai_client = _RecordingOpenAIClient(
        _StubOpenAIResponse(
            '{"variants":['
            '"OpenAI run-local first https://example.com/articles/finance-1",'
            '"OpenAI run-local second https://example.com/articles/finance-1",'
            '"OpenAI run-local third https://example.com/articles/finance-1"'
            "]}"
        )
    )
    codex_client = _RecordingCodexWrapperClient(
        _StubCodexWrapperResponse(
            '{"variants":['
            '"Codex run-local first https://example.com/articles/finance-1",'
            '"Codex run-local second https://example.com/articles/finance-1",'
            '"Codex run-local third https://example.com/articles/finance-1"'
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

    result = run_local_pipeline(
        tmp_path,
        session_factory=session_factory,
        connector_registry=_StaticConnectorRegistry(
            {
                "finance_rss": (
                    SourceItemCandidate(
                        source_id="finance_rss",
                        external_id="finance-1",
                        source_url="https://example.com/articles/finance-1",
                        title="Central bank update shifts markets",
                        summary="RSS summary that will be superseded.",
                        raw_payload={"feed_title": "Finance Feed", "tags": ["markets", "policy"]},
                    ),
                )
            }
        ),
        html_fetcher=_FakeFetcher(),
        article_extractor=_FakeExtractor(),
        summary_regenerator=_FakeRegenerator(),
        now=datetime(2026, 3, 18, 10, 0, tzinfo=timezone.utc),
    )

    assert result.status is PipelineRunStatus.SUCCEEDED
    assert result.draft_created_variant_count == 3
    assert openai_client.payloads == []
    assert codex_client.payloads[0]["model"] == "gpt-5.4-mini"

    with session_scope(session_factory) as session:
        pipeline_runs = PipelineRunRepository(session).list()
        stored_drafts = DraftVariantRepository(session).list()

    assert pipeline_runs[0].summary_json["rewrite_providers"] == ["codex_wrapper"]
    assert [draft.body for draft in stored_drafts] == [
        "Codex run-local first https://example.com/articles/finance-1",
        "Codex run-local second https://example.com/articles/finance-1",
        "Codex run-local third https://example.com/articles/finance-1",
    ]


def _build_session_factory(tmp_path: Path):
    engine = create_database_engine(f"sqlite+pysqlite:///{tmp_path / 'run-local.db'}")
    create_all_tables(engine)
    return create_session_factory(engine)


def _write_project_config(tmp_path: Path) -> None:
    (tmp_path / "accounts.yaml").write_text(
        """
accounts:
  finance_insights_daily:
    topic: "Finance market insights"
    source_sets:
      - finance_primary
    prompt_profile: finance_default
    landing:
      fallback_url: https://gilgop.cloud/finance
      rules: []
    matching:
      include_keywords:
        - market
        - policy
      source_tags:
        - markets
        - policy
      strict_topic_guard: true
    channels:
      x:
        schedule:
          cron: "0 9 * * *"
        render:
          max_chars: 280
""".strip() + "\n",
        encoding="utf-8",
    )
    (tmp_path / "prompts.yaml").write_text(
        """
profiles:
  finance_default:
    system_template: |
      You are the editor for {{ account_key }} using {{ source_name }} context.
    user_template: |
      Write about {{ title }} using {{ summary }} and cite {{ source_url }}.
""".strip() + "\n",
        encoding="utf-8",
    )
    (tmp_path / "sources.yaml").write_text(
        """
sources:
  finance_rss:
    type: rss
    url: https://example.com/feed.xml
source_sets:
  finance_primary:
    sources:
      - finance_rss
""".strip() + "\n",
        encoding="utf-8",
    )
