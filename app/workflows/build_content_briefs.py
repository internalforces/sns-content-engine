"""Workflow for transforming ingested source items into content briefs."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from app.config import AccountConfig, ConfigRegistry
from app.domain import (
    ContentBriefData,
    SourceItemCandidate,
    extract_source_tags,
    select_top_account_candidates,
)
from app.services import AccountMatcher, ContentBriefBuilder, LandingResolver
from app.storage import (
    ContentBrief,
    ContentBriefRepository,
    SourceItem,
    SourceItemRepository,
    SourceItemState,
    create_database_engine,
    create_session_factory,
    ensure_database_schema_is_current,
    session_scope,
)


@dataclass(frozen=True, slots=True)
class BuildContentBriefOutcome:
    """Outcome of attempting to build one account-specific brief."""

    source_item_id: int
    status: str
    account_key: str | None = None
    content_brief_id: int | None = None


@dataclass(frozen=True, slots=True)
class BuildContentBriefsResult:
    """Aggregated content brief creation result for one workflow run."""

    processed_source_item_ids: tuple[int, ...]
    outcomes: tuple[BuildContentBriefOutcome, ...]

    @property
    def processed_count(self) -> int:
        """Return the number of ingested source items considered."""

        return len(self.processed_source_item_ids)

    @property
    def created_count(self) -> int:
        """Return the number of new briefs created."""

        return sum(outcome.status == "created" for outcome in self.outcomes)

    @property
    def existing_count(self) -> int:
        """Return the number of briefs that already existed."""

        return sum(outcome.status == "existing" for outcome in self.outcomes)

    @property
    def no_match_count(self) -> int:
        """Return the number of source items with no eligible account match."""

        return sum(outcome.status == "no_match" for outcome in self.outcomes)

    def counts_by_status(self) -> dict[str, int]:
        """Return outcome counts grouped by status."""

        counts = Counter(outcome.status for outcome in self.outcomes)
        return dict(sorted(counts.items()))


def build_content_briefs(
    config_dir: Path | str = Path("config"),
    *,
    database_url: str | None = None,
    session_factory=None,
) -> BuildContentBriefsResult:
    """Build platform-neutral content briefs for ingested source items."""

    registry = ConfigRegistry.from_directory(Path(config_dir))

    owned_engine = None
    if session_factory is None:
        owned_engine = create_database_engine(database_url)
        ensure_database_schema_is_current(owned_engine)
        session_factory = create_session_factory(owned_engine)
    else:
        bound_engine = _resolve_bound_engine(session_factory)
        if bound_engine is not None:
            ensure_database_schema_is_current(bound_engine)

    try:
        with session_scope(session_factory) as session:
            source_items = SourceItemRepository(session)
            briefs = ContentBriefRepository(session)
            builder = ContentBriefBuilder()
            ingested_items = source_items.list_by_state(SourceItemState.INGESTED)
            outcomes: list[BuildContentBriefOutcome] = []

            for source_item in ingested_items:
                account_pool = _eligible_accounts_for_source(registry, source_item.source_key)
                if not account_pool:
                    outcomes.append(
                        BuildContentBriefOutcome(
                            source_item_id=source_item.id,
                            status="no_match",
                        )
                    )
                    continue

                match_candidates = AccountMatcher(account_pool).match_source_item(
                    _source_item_to_candidate(source_item)
                )
                top_matches = select_top_account_candidates(match_candidates)
                if not top_matches:
                    outcomes.append(
                        BuildContentBriefOutcome(
                            source_item_id=source_item.id,
                            status="no_match",
                        )
                    )
                    continue

                source_tags = extract_source_tags(source_item.raw_payload or {})
                brief_available = False

                for match_candidate in top_matches:
                    account_key = match_candidate.account_key
                    account = account_pool[account_key]
                    landing_decision = LandingResolver(account.landing).resolve(source_tags)
                    brief_data = builder.build(
                        source_item=source_item,
                        account_id=account_key,
                        match_candidate=match_candidate,
                        landing_decision=landing_decision,
                    )
                    stored_brief, was_created = briefs.get_or_create(
                        _content_brief_data_to_model(brief_data)
                    )
                    outcomes.append(
                        BuildContentBriefOutcome(
                            source_item_id=source_item.id,
                            status="created" if was_created else "existing",
                            account_key=account_key,
                            content_brief_id=stored_brief.id,
                        )
                    )
                    brief_available = True

                if brief_available:
                    source_item.state = SourceItemState.BRIEF_CREATED
                    session.flush()
    finally:
        if owned_engine is not None:
            owned_engine.dispose()

    return BuildContentBriefsResult(
        processed_source_item_ids=tuple(item.id for item in ingested_items),
        outcomes=tuple(outcomes),
    )


def _eligible_accounts_for_source(
    registry: ConfigRegistry,
    source_key: str,
) -> dict[str, AccountConfig]:
    eligible_accounts: dict[str, AccountConfig] = {}

    for account_key, account in registry.accounts.items():
        account_sources = {
            source_id
            for source_set_key in account.source_sets
            for source_id in registry.get_source_set(source_set_key).sources
        }
        if source_key in account_sources:
            eligible_accounts[account_key] = account

    return eligible_accounts


def _source_item_to_candidate(source_item: SourceItem) -> SourceItemCandidate:
    return SourceItemCandidate(
        source_id=source_item.source_key,
        external_id=source_item.external_id,
        source_url=source_item.source_url,
        title=source_item.title,
        summary=source_item.summary,
        published_at=source_item.published_at,
        raw_payload=source_item.raw_payload or {},
    )


def _content_brief_data_to_model(brief: ContentBriefData) -> ContentBrief:
    return ContentBrief(
        source_item_id=brief.source_item_id,
        account_key=brief.account_id,
        title=brief.source_title,
        summary=brief.source_summary,
        key_points=list(brief.key_points),
        landing_url=brief.landing_url,
        tags=list(brief.tags),
        angle=brief.angle,
        language=brief.language,
    )


def _resolve_bound_engine(session_factory):
    return getattr(session_factory, "kw", {}).get("bind")
