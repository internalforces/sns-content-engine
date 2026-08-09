"""Tests for the source ingestion workflow with duplicate blocking."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent

from app.domain import SourceConnectorResult, SourceItemCandidate
from app.storage import (
    SourceItem,
    SourceItemRepository,
    SourcePolicyMode,
    create_all_tables,
    create_database_engine,
    create_session_factory,
    session_scope,
)
from app.workflows.ingest_sources import ingest_sources


class StaticSourceConnector:
    """Connector test double that returns preconfigured candidates by source id."""

    def __init__(self, items_by_source: dict[str, tuple[SourceItemCandidate, ...]]) -> None:
        self._items_by_source = items_by_source

    def discover(self, source_id: str, source_config) -> SourceConnectorResult:
        return SourceConnectorResult(items=self._items_by_source.get(source_id, ()))


class StaticConnectorRegistry:
    """Connector registry test double."""

    def __init__(self, items_by_source: dict[str, tuple[SourceItemCandidate, ...]]) -> None:
        self._connector = StaticSourceConnector(items_by_source)

    def get_connector(self, source_config):
        return self._connector


def test_ingest_sources_saves_new_items_and_blocks_canonical_url_duplicates(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path)
    _write_config(tmp_path, duplicate_window_days=7)
    with session_scope(session_factory) as session:
        SourceItemRepository(session).add(
            SourceItem(
                source_key="ai_tools_rss",
                external_id="seed-1",
                source_url="https://example.com/posts/existing",
                title="Existing seed item",
                summary="Original summary",
            )
        )

    result = ingest_sources(
        tmp_path,
        connector_registry=StaticConnectorRegistry(
            {
                "ai_tools_rss": (
                    SourceItemCandidate(
                        source_id="ai_tools_rss",
                        external_id="new-1",
                        source_url="https://example.com/posts/new",
                        title="Fresh discovery",
                        summary="Brand new summary",
                    ),
                    SourceItemCandidate(
                        source_id="ai_tools_rss",
                        external_id="dup-url",
                        source_url="https://example.com/posts/existing?utm_source=x",
                        title="Same page, different feed metadata",
                        summary="Changed summary",
                    ),
                )
            }
        ),
        session_factory=session_factory,
        now=datetime(2026, 3, 17, 9, 0, tzinfo=timezone.utc),
    )

    assert result.saved_count == 1
    assert result.duplicate_count == 1
    assert result.duplicate_counts_by_reason() == {"canonical_url": 1}

    with session_scope(session_factory) as session:
        stored_items = SourceItemRepository(session).list()

    assert len(stored_items) == 2
    assert {item.external_id for item in stored_items} == {"seed-1", "new-1"}


def test_ingest_sources_blocks_normalized_title_hash_duplicates(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path)
    _write_config(tmp_path, duplicate_window_days=7)
    with session_scope(session_factory) as session:
        SourceItemRepository(session).add(
            SourceItem(
                source_key="ai_tools_rss",
                external_id="seed-2",
                source_url="https://example.com/posts/original-title",
                title="AI Tool Launch",
                summary="Original summary",
            )
        )

    result = ingest_sources(
        tmp_path,
        connector_registry=StaticConnectorRegistry(
            {
                "ai_tools_rss": (
                    SourceItemCandidate(
                        source_id="ai_tools_rss",
                        external_id="dup-title",
                        source_url="https://example.com/posts/different-url",
                        title="AI   Tool: Launch!",
                        summary="Different summary",
                    ),
                )
            }
        ),
        session_factory=session_factory,
        now=datetime(2026, 3, 17, 9, 0, tzinfo=timezone.utc),
    )

    assert result.saved_count == 0
    assert result.duplicate_count == 1
    assert result.duplicate_counts_by_reason() == {"normalized_title_hash": 1}


def test_ingest_sources_uses_duplicate_window_for_recent_fingerprint_checks(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path)
    _write_config(tmp_path, duplicate_window_days=7)
    with session_scope(session_factory) as session:
        repository = SourceItemRepository(session)
        repository.add(
            SourceItem(
                source_key="ai_tools_rss",
                external_id="seed-old",
                source_url="https://example.com/posts/old",
                title="Aged GPT Five Launch",
                summary="Shared launch summary",
                created_at=datetime(2026, 3, 1, 9, 0, tzinfo=timezone.utc),
            )
        )
        repository.add(
            SourceItem(
                source_key="ai_tools_rss",
                external_id="seed-recent",
                source_url="https://example.com/posts/recent",
                title="Fast GPT Five Launch",
                summary="Shared launch summary",
                created_at=datetime(2026, 3, 15, 9, 0, tzinfo=timezone.utc),
            )
        )

    result = ingest_sources(
        tmp_path,
        connector_registry=StaticConnectorRegistry(
            {
                "ai_tools_rss": (
                    SourceItemCandidate(
                        source_id="ai_tools_rss",
                        external_id="dup-fingerprint",
                        source_url="https://example.com/posts/brand-new-url",
                        title="Launch GPT Five Fast",
                        summary="Shared launch summary",
                    ),
                )
            }
        ),
        session_factory=session_factory,
        now=datetime(2026, 3, 17, 9, 0, tzinfo=timezone.utc),
    )

    assert result.saved_count == 0
    assert result.duplicate_count == 1
    assert result.duplicate_counts_by_reason() == {"recent_fingerprint": 1}
    assert result.outcomes[0].matched_item_id is not None


def test_ingest_sources_allows_old_fingerprint_matches_outside_window(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path)
    _write_config(tmp_path, duplicate_window_days=7)
    with session_scope(session_factory) as session:
        SourceItemRepository(session).add(
            SourceItem(
                source_key="ai_tools_rss",
                external_id="seed-old",
                source_url="https://example.com/posts/old",
                title="Fast GPT Five Launch",
                summary="Shared launch summary",
                created_at=datetime(2026, 3, 1, 9, 0, tzinfo=timezone.utc),
            )
        )

    result = ingest_sources(
        tmp_path,
        connector_registry=StaticConnectorRegistry(
            {
                "ai_tools_rss": (
                    SourceItemCandidate(
                        source_id="ai_tools_rss",
                        external_id="new-after-window",
                        source_url="https://example.com/posts/brand-new-url",
                        title="Launch GPT Five Fast",
                        summary="Shared launch summary",
                    ),
                )
            }
        ),
        session_factory=session_factory,
        now=datetime(2026, 3, 17, 9, 0, tzinfo=timezone.utc),
    )

    assert result.saved_count == 1
    assert result.duplicate_count == 0


def test_ingest_sources_persists_source_policy_snapshot_from_config(tmp_path: Path) -> None:
    session_factory = _build_session_factory(tmp_path)
    _write_config(
        tmp_path,
        duplicate_window_days=7,
        policy_mode="restricted",
        allow_full_text_fetch=False,
        allow_llm_rewrite=False,
        require_attribution=True,
    )

    result = ingest_sources(
        tmp_path,
        connector_registry=StaticConnectorRegistry(
            {
                "ai_tools_rss": (
                    SourceItemCandidate(
                        source_id="ai_tools_rss",
                        external_id="policy-snapshot-1",
                        source_url="https://example.com/posts/policy-snapshot",
                        title="Policy snapshot item",
                    ),
                )
            }
        ),
        session_factory=session_factory,
        now=datetime(2026, 3, 17, 9, 0, tzinfo=timezone.utc),
    )

    assert result.saved_count == 1

    with session_scope(session_factory) as session:
        stored_items = SourceItemRepository(session).list()

    assert len(stored_items) == 1
    assert stored_items[0].policy_mode is SourcePolicyMode.RESTRICTED
    assert stored_items[0].allow_full_text_fetch is False
    assert stored_items[0].allow_llm_rewrite is False
    assert stored_items[0].require_attribution is True


def _build_session_factory(tmp_path: Path):
    engine = create_database_engine(f"sqlite+pysqlite:///{tmp_path / 'ingest.db'}")
    create_all_tables(engine)
    return create_session_factory(engine)


def _write_config(
    path: Path,
    *,
    duplicate_window_days: int,
    policy_mode: str = "reusable",
    allow_full_text_fetch: bool = True,
    allow_llm_rewrite: bool = True,
    require_attribution: bool = False,
) -> None:
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
            system_template: "system"
            user_template: "user"
        """,
    )
    _write_file(
        path / "sources.yaml",
        f"""
        sources:
          ai_tools_rss:
            type: rss
            url: https://example.com/feed.xml
            duplicate_window_days: {duplicate_window_days}
            policy_mode: {policy_mode}
            allow_full_text_fetch: {str(allow_full_text_fetch).lower()}
            allow_llm_rewrite: {str(allow_llm_rewrite).lower()}
            require_attribution: {str(require_attribution).lower()}

        source_sets:
          ai_tools_primary:
            sources:
              - ai_tools_rss
        """,
    )


def _write_file(path: Path, content: str) -> None:
    path.write_text(dedent(content).strip() + "\n", encoding="utf-8")
