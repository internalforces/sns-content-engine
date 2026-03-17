"""Deterministic builder for platform-neutral content briefs."""

from __future__ import annotations

import re

from app.config import AccountConfig
from app.domain import (
    AccountMatchCandidate,
    ContentBriefData,
    LandingDecision,
    extract_source_tags,
)
from app.storage import SourceItem

_SUMMARY_SPLIT_RE = re.compile(r"[.!?\n]+")
_MULTISPACE_RE = re.compile(r"\s+")
_NON_WORD_RE = re.compile(r"[^\w\s]")
_PRACTICAL_ANGLE_KEYWORDS = ("how to", "guide", "tutorial", "tips", "checklist")
_PRODUCT_ANGLE_KEYWORDS = ("launch", "release", "update", "introduces", "new")
_TREND_ANGLE_KEYWORDS = ("report", "study", "survey", "data", "benchmark")


class ContentBriefBuilder:
    """Build channel-neutral brief data from source and account context."""

    def build(
        self,
        *,
        source_item: SourceItem,
        account_id: str,
        account: AccountConfig,
        match_candidate: AccountMatchCandidate,
        landing_decision: LandingDecision,
    ) -> ContentBriefData:
        source_tags = extract_source_tags(source_item.raw_payload or {})
        if source_item.id is None:
            raise ValueError("source item must be persisted before building a content brief")

        return ContentBriefData(
            account_id=account_id,
            source_item_id=source_item.id,
            source_title=source_item.title,
            source_summary=source_item.summary,
            key_points=_build_key_points(source_item.title, source_item.summary),
            tags=_build_tags(source_tags, match_candidate),
            angle=_select_angle(source_item.title, source_item.summary),
            landing_url=landing_decision.landing_url,
            language="en",
        )


def _build_key_points(title: str, summary: str | None) -> tuple[str, ...]:
    key_points: list[str] = []
    seen: set[str] = set()

    for candidate in (title, *_split_summary(summary)):
        normalized = _normalize_point(candidate)
        if normalized is None:
            continue
        dedupe_key = normalized.casefold()
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        key_points.append(normalized)
        if len(key_points) == 3:
            break

    return tuple(key_points)


def _split_summary(summary: str | None) -> tuple[str, ...]:
    if not summary:
        return ()
    return tuple(_SUMMARY_SPLIT_RE.split(summary))


def _build_tags(
    source_tags: tuple[str, ...],
    match_candidate: AccountMatchCandidate,
) -> tuple[str, ...]:
    if source_tags:
        return source_tags[:5]

    return _dedupe_strings(
        (
            *match_candidate.source_tag_hits,
            *match_candidate.topic_keyword_hits,
            *match_candidate.include_keyword_hits,
        ),
        limit=5,
    )


def _select_angle(title: str, summary: str | None) -> str:
    text = _normalize_search_text(" ".join(part for part in (title, summary) if part))

    if _contains_keyword(text, _PRACTICAL_ANGLE_KEYWORDS):
        return "practical_how_to"
    if _contains_keyword(text, _PRODUCT_ANGLE_KEYWORDS):
        return "product_update"
    if _contains_keyword(text, _TREND_ANGLE_KEYWORDS):
        return "trend_insight"
    return "topic_takeaway"


def _contains_keyword(text: str, keywords: tuple[str, ...]) -> bool:
    padded = f" {text} "
    return any(f" {keyword} " in padded for keyword in keywords)


def _dedupe_strings(values: tuple[str, ...], *, limit: int) -> tuple[str, ...]:
    items: list[str] = []
    seen: set[str] = set()

    for value in values:
        normalized = _normalize_point(value)
        if normalized is None:
            continue
        dedupe_key = normalized.casefold()
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        items.append(normalized)
        if len(items) == limit:
            break

    return tuple(items)


def _normalize_point(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = _MULTISPACE_RE.sub(" ", value).strip()
    if not normalized:
        return None
    return normalized


def _normalize_search_text(value: str) -> str:
    normalized = value.casefold().replace("-", " ").replace("_", " ")
    normalized = _NON_WORD_RE.sub(" ", normalized)
    return _MULTISPACE_RE.sub(" ", normalized).strip()
