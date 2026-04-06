"""Workflow for generating X-ready draft variants from stored content briefs."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from app.config import ConfigRegistry
from app.connectors.llm import DraftGenerationProvider, resolve_draft_generation_provider
from app.services import XDraftGenerator
from app.services.x_draft_generator import build_draft_provenance_snapshot
from app.storage import (
    ContentBriefRepository,
    DraftVariant,
    DraftVariantRepository,
    create_database_engine,
    create_session_factory,
    ensure_database_schema_is_current,
    session_scope,
)


@dataclass(frozen=True, slots=True)
class GenerateDraftOutcome:
    """Outcome of attempting to generate X drafts for one content brief."""

    content_brief_id: int
    status: str
    channel: str | None = None
    draft_variant_ids: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class GenerateDraftsResult:
    """Aggregated draft generation result for one workflow run."""

    processed_content_brief_ids: tuple[int, ...]
    outcomes: tuple[GenerateDraftOutcome, ...]

    @property
    def processed_count(self) -> int:
        """Return the number of content briefs considered."""

        return len(self.processed_content_brief_ids)

    @property
    def created_count(self) -> int:
        """Return the number of briefs that produced new draft sets."""

        return sum(outcome.status == "created" for outcome in self.outcomes)

    @property
    def existing_count(self) -> int:
        """Return the number of briefs that already had X drafts."""

        return sum(outcome.status == "existing" for outcome in self.outcomes)

    @property
    def no_channel_count(self) -> int:
        """Return the number of briefs whose account lacks an X channel."""

        return sum(outcome.status == "no_channel" for outcome in self.outcomes)

    @property
    def missing_account_count(self) -> int:
        """Return the number of briefs whose configured account is no longer present."""

        return sum(outcome.status == "missing_account" for outcome in self.outcomes)

    @property
    def created_variant_count(self) -> int:
        """Return the total number of new draft variants stored."""

        return sum(len(outcome.draft_variant_ids) for outcome in self.outcomes)

    def counts_by_status(self) -> dict[str, int]:
        """Return outcome counts grouped by status."""

        counts = Counter(outcome.status for outcome in self.outcomes)
        return dict(sorted(counts.items()))


def generate_drafts(
    config_dir: Path | str = Path("config"),
    *,
    database_url: str | None = None,
    session_factory=None,
    llm_provider: DraftGenerationProvider | None = None,
    variant_count: int = 3,
) -> GenerateDraftsResult:
    """Generate X-ready draft variants for stored content briefs."""

    if variant_count not in (2, 3):
        raise ValueError("variant_count must be 2 or 3")

    registry = ConfigRegistry.from_directory(Path(config_dir))
    provider = llm_provider or resolve_draft_generation_provider()

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
            briefs = ContentBriefRepository(session)
            drafts = DraftVariantRepository(session)
            generator = XDraftGenerator(provider)
            stored_briefs = briefs.list()
            outcomes: list[GenerateDraftOutcome] = []

            for brief in stored_briefs:
                existing_drafts = drafts.list_by_content_brief_and_channel(brief.id, "x")
                if existing_drafts:
                    outcomes.append(
                        GenerateDraftOutcome(
                            content_brief_id=brief.id,
                            status="existing",
                            channel="x",
                        )
                    )
                    continue

                try:
                    account = registry.get_account(brief.account_key)
                except KeyError:
                    outcomes.append(
                        GenerateDraftOutcome(
                            content_brief_id=brief.id,
                            status="missing_account",
                        )
                    )
                    continue

                if "x" not in account.channels:
                    outcomes.append(
                        GenerateDraftOutcome(
                            content_brief_id=brief.id,
                            status="no_channel",
                        )
                    )
                    continue

                prompt_profile = registry.get_prompt_profile(account.prompt_profile)
                generated_bodies = generator.generate(
                    content_brief=brief,
                    account_key=brief.account_key,
                    account=account,
                    prompt_profile=prompt_profile,
                    variant_count=variant_count,
                )
                created_draft_ids: list[int] = []
                created_any = False
                provenance = build_draft_provenance_snapshot(brief)
                for index, body in enumerate(generated_bodies):
                    stored_draft, was_created = drafts.get_or_create(
                        DraftVariant(
                            content_brief_id=brief.id,
                            channel="x",
                            variant_index=index,
                            body=body,
                            source_name=provenance.source_name,
                            source_url=provenance.source_url,
                            article_url=provenance.article_url,
                            source_published_at=provenance.published_at,
                            source_policy_mode=provenance.policy_mode,
                        )
                    )
                    if was_created:
                        created_any = True
                        created_draft_ids.append(stored_draft.id)

                outcomes.append(
                    GenerateDraftOutcome(
                        content_brief_id=brief.id,
                        status="created" if created_any else "existing",
                        channel="x",
                        draft_variant_ids=tuple(created_draft_ids),
                    )
                )
    finally:
        if owned_engine is not None:
            owned_engine.dispose()

    return GenerateDraftsResult(
        processed_content_brief_ids=tuple(brief.id for brief in stored_briefs),
        outcomes=tuple(outcomes),
    )


def _resolve_bound_engine(session_factory):
    return getattr(session_factory, "kw", {}).get("bind")
