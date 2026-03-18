"""Tests for the article enrichment workflow."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.storage import (
    ArticleEnrichment,
    ArticleEnrichmentRepository,
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
from app.workflows import enrich_articles


class _FakeFetcher:
    def __init__(self, html_by_url: dict[str, str]) -> None:
        self._html_by_url = html_by_url

    def fetch(self, article_url: str):
        html = self._html_by_url[article_url]
        return type(
            "FetchResult",
            (),
            {
                "article_url": article_url,
                "final_url": article_url,
                "html": html,
            },
        )()


class _FakeExtractor:
    def extract(self, html: str):
        return type(
            "ExtractResult",
            (),
            {
                "title": "Extracted finance title",
                "source_name": "Finance Feed",
                "published_at": datetime(2026, 3, 18, 8, 0, tzinfo=timezone.utc),
                "article_text": (
                    "Markets rose after policy updates while banks, bonds, and credit spreads stayed in focus. "
                    "Analysts tracked revenue guidance and inflation signals across sectors. "
                    "Treasury yields eased as traders repriced the macro outlook."
                ),
                "metadata": {"og:site_name": "Finance Feed"},
            },
        )()


class _FakeRegenerator:
    def regenerate(self, *, title: str, article_text: str, rss_description: str | None = None):
        assert title == "Extracted finance title"
        return type(
            "Regenerated",
            (),
            {
                "summary": "Extracted finance title: Markets reacted to policy and macro updates.",
                "key_points": (
                    "Markets reacted to policy updates",
                    "Banks and bonds stayed in focus",
                    "Treasury yields eased on macro repricing",
                ),
            },
        )()


class _BlockedFetcher:
    def fetch(self, article_url: str):
        from app.services import HtmlFetcherError

        raise HtmlFetcherError(code="fetch_blocked", message="사이트 접근이 차단되었어요")


def test_enrich_articles_creates_enrichment_records_and_summaries(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path)
    with session_scope(session_factory) as session:
        source_item = SourceItemRepository(session).add(
            SourceItem(
                source_key="finance_rss",
                external_id="entry-1",
                source_url="https://example.com/articles/1",
                title="Feed title",
                summary="Feed summary",
                raw_payload={"feed_title": "Finance Feed", "tags": ["markets", "policy"]},
                state=SourceItemState.INGESTED,
            )
        )
        source_item_id = source_item.id

    result = enrich_articles(
        session_factory=session_factory,
        html_fetcher=_FakeFetcher({"https://example.com/articles/1": "<html>ok</html>"}),
        article_extractor=_FakeExtractor(),
        summary_regenerator=_FakeRegenerator(),
        now=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
    )

    assert result.processed_source_item_ids == (source_item_id,)
    assert result.enriched_count == 1
    assert result.failed_count == 0

    with session_scope(session_factory) as session:
        enrichment = ArticleEnrichmentRepository(session).get_by_source_item_id(source_item_id)

    assert enrichment is not None
    assert enrichment.source_name == "Finance Feed"
    assert enrichment.regenerated_summary == "Extracted finance title: Markets reacted to policy and macro updates."
    assert enrichment.tags == ["markets", "policy"]
    assert enrichment.html_fetch_status is StageExecutionStatus.SUCCEEDED
    assert enrichment.article_extract_status is StageExecutionStatus.SUCCEEDED
    assert enrichment.summary_regenerate_status is StageExecutionStatus.SUCCEEDED
    assert enrichment.last_stage is PipelineStage.SUMMARY_REGENERATE
    assert enrichment.failure_code is None


def test_enrich_articles_persists_readable_failures(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path)
    with session_scope(session_factory) as session:
        source_item = SourceItemRepository(session).add(
            SourceItem(
                source_key="finance_rss",
                external_id="entry-2",
                source_url="https://example.com/articles/2",
                title="Blocked feed item",
                state=SourceItemState.INGESTED,
            )
        )
        source_item_id = source_item.id

    result = enrich_articles(
        session_factory=session_factory,
        html_fetcher=_BlockedFetcher(),
        article_extractor=_FakeExtractor(),
        summary_regenerator=_FakeRegenerator(),
    )

    assert result.failed_count == 1
    assert result.outcomes[0].failure_code == "fetch_blocked"

    with session_scope(session_factory) as session:
        enrichment = ArticleEnrichmentRepository(session).get_by_source_item_id(source_item_id)

    assert enrichment is not None
    assert enrichment.failure_code == "fetch_blocked"
    assert enrichment.failure_message == "사이트 접근이 차단되었어요"
    assert enrichment.failure_stage is PipelineStage.HTML_FETCH
    assert enrichment.html_fetch_status is StageExecutionStatus.FAILED


def test_enrich_articles_skips_existing_completed_enrichment(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path)
    with session_scope(session_factory) as session:
        source_item = SourceItemRepository(session).add(
            SourceItem(
                source_key="finance_rss",
                external_id="entry-3",
                source_url="https://example.com/articles/3",
                title="Done item",
                state=SourceItemState.INGESTED,
            )
        )
        source_item_id = source_item.id
        ArticleEnrichmentRepository(session).add(
            ArticleEnrichment(
                source_item_id=source_item_id,
                source_name="Finance Feed",
                article_url="https://example.com/articles/3",
                article_text="Existing body text for completed enrichment.",
                regenerated_summary="Existing summary",
                regenerated_key_points=["Point one", "Point two", "Point three"],
                html_fetch_status=StageExecutionStatus.SUCCEEDED,
                article_extract_status=StageExecutionStatus.SUCCEEDED,
                summary_regenerate_status=StageExecutionStatus.SUCCEEDED,
                last_stage=PipelineStage.SUMMARY_REGENERATE,
            )
        )

    result = enrich_articles(
        session_factory=session_factory,
        html_fetcher=_FakeFetcher({}),
        article_extractor=_FakeExtractor(),
        summary_regenerator=_FakeRegenerator(),
    )

    assert result.existing_count == 1
    assert result.outcomes[0].status == "existing"


def _build_session_factory(tmp_path: Path):
    engine = create_database_engine(f"sqlite+pysqlite:///{tmp_path / 'enrich.db'}")
    create_all_tables(engine)
    return create_session_factory(engine)
