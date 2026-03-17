"""Deterministic account-matching service."""

from __future__ import annotations

from collections.abc import Mapping
import re
from urllib.parse import urlsplit

from app.config import AccountConfig, ConfigRegistry
from app.domain import AccountMatchCandidate, SourceItemCandidate

_NON_WORD_RE = re.compile(r"[^\w\s]")
_MULTISPACE_RE = re.compile(r"\s+")
_TOPIC_STOPWORDS = {
    "a",
    "an",
    "and",
    "daily",
    "for",
    "guide",
    "guides",
    "how",
    "in",
    "news",
    "of",
    "on",
    "the",
    "tips",
    "to",
    "tool",
    "tools",
    "update",
    "updates",
    "workflow",
    "workflows",
}
_INCLUDE_KEYWORD_WEIGHT = 10
_SOURCE_TAG_WEIGHT = 8
_TOPIC_KEYWORD_WEIGHT = 3


class AccountMatcher:
    """Score which accounts a normalized source item belongs to."""

    def __init__(self, accounts: Mapping[str, AccountConfig]) -> None:
        self._accounts = dict(accounts)

    @classmethod
    def from_registry(cls, registry: ConfigRegistry) -> "AccountMatcher":
        """Build a matcher from the loaded config registry."""

        return cls(registry.accounts)

    def match_source_item(
        self,
        item: SourceItemCandidate,
    ) -> tuple[AccountMatchCandidate, ...]:
        """Return scored account candidates sorted from strongest to weakest."""

        item_text = _build_match_text(item)
        item_tags = set(item.source_tags)

        candidates = [
            self._score_account(
                account_key,
                account,
                item_text=item_text,
                item_tags=item_tags,
            )
            for account_key, account in self._accounts.items()
        ]
        return tuple(
            sorted(
                candidates,
                key=lambda candidate: (-candidate.score, candidate.account_key),
            )
        )

    def _score_account(
        self,
        account_key: str,
        account: AccountConfig,
        *,
        item_text: str,
        item_tags: set[str],
    ) -> AccountMatchCandidate:
        include_hits = _find_phrase_hits(account.matching.include_keywords, item_text, item_tags)
        exclude_hits = _find_phrase_hits(account.matching.exclude_keywords, item_text, item_tags)
        source_tag_hits = tuple(
            source_tag
            for source_tag in account.matching.source_tags
            if source_tag in item_tags
        )
        topic_keyword_hits = _find_topic_keyword_hits(account.topic, item_text, item_tags)

        raw_score = (
            len(include_hits) * _INCLUDE_KEYWORD_WEIGHT
            + len(source_tag_hits) * _SOURCE_TAG_WEIGHT
            + len(topic_keyword_hits) * _TOPIC_KEYWORD_WEIGHT
        )
        strict_topic_guard_applied = account.matching.strict_topic_guard
        strict_topic_guard_passed = (
            not strict_topic_guard_applied
            or bool(source_tag_hits)
            or bool(topic_keyword_hits)
        )
        eligible = raw_score > 0 and not exclude_hits and strict_topic_guard_passed

        return AccountMatchCandidate(
            account_key=account_key,
            score=raw_score if eligible else 0,
            eligible=eligible,
            include_keyword_hits=include_hits,
            exclude_keyword_hits=exclude_hits,
            source_tag_hits=source_tag_hits,
            topic_keyword_hits=topic_keyword_hits,
            strict_topic_guard_applied=strict_topic_guard_applied,
            strict_topic_guard_passed=strict_topic_guard_passed,
        )


def _build_match_text(item: SourceItemCandidate) -> str:
    url = urlsplit(item.canonical_url)
    url_text = " ".join(part for part in (url.netloc, url.path, url.query) if part)
    return _normalize_match_text(" ".join(filter(None, (item.title, item.summary, url_text))))


def _find_phrase_hits(
    phrases: tuple[str, ...],
    text: str,
    tags: set[str],
) -> tuple[str, ...]:
    hits: list[str] = []

    for phrase in phrases:
        if _matches_phrase(phrase, text, tags):
            hits.append(phrase)

    return tuple(hits)


def _find_topic_keyword_hits(
    topic: str,
    text: str,
    tags: set[str],
) -> tuple[str, ...]:
    topic_keywords = _topic_keywords(topic)
    hits: list[str] = []

    for keyword in topic_keywords:
        if _matches_phrase(keyword, text, tags):
            hits.append(keyword)

    return tuple(hits)


def _topic_keywords(topic: str) -> tuple[str, ...]:
    normalized_topic = _normalize_match_text(topic)
    topic_keywords: list[str] = []

    for token in normalized_topic.split():
        if token in _TOPIC_STOPWORDS:
            continue
        if len(token) == 1:
            continue
        if token.isdigit():
            continue
        topic_keywords.append(token)

    return tuple(dict.fromkeys(topic_keywords))


def _matches_phrase(phrase: str, text: str, tags: set[str]) -> bool:
    normalized_phrase = _normalize_match_text(phrase)
    if not normalized_phrase:
        return False
    if normalized_phrase in tags:
        return True
    return f" {normalized_phrase} " in f" {text} "


def _normalize_match_text(value: str) -> str:
    normalized = value.casefold().replace("-", " ").replace("_", " ")
    normalized = _NON_WORD_RE.sub(" ", normalized)
    normalized = _MULTISPACE_RE.sub(" ", normalized).strip()
    return normalized
