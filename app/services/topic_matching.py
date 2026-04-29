"""Shared helpers for topic keyword normalization and phrase matching."""

from __future__ import annotations

import re

_NON_WORD_RE = re.compile(r"[^\w\s]")
_MULTISPACE_RE = re.compile(r"\s+")
_URL_RE = re.compile(r"https?://\S+")
_TOPIC_STOPWORDS = {
    "a",
    "an",
    "and",
    "daily",
    "for",
    "global",
    "guide",
    "guides",
    "how",
    "in",
    "news",
    "of",
    "on",
    "reader",
    "readers",
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


def contains_phrase(phrase: str, normalized_text: str) -> bool:
    """Return whether normalized_text contains the normalized phrase."""

    normalized_phrase = normalize_match_text(phrase)
    if not normalized_phrase:
        return False
    return f" {normalized_phrase} " in f" {normalized_text} "


def normalize_match_text(value: str) -> str:
    """Normalize user-facing text for phrase matching."""

    normalized = value.casefold().replace("-", " ").replace("_", " ")
    normalized = _NON_WORD_RE.sub(" ", normalized)
    return _MULTISPACE_RE.sub(" ", normalized).strip()


def strip_urls(value: str) -> str:
    """Remove URL substrings so topic checks only inspect prose content."""

    return _URL_RE.sub(" ", value)


def topic_keywords(topic: str) -> tuple[str, ...]:
    """Derive distinct topic keywords from a configured topic string."""

    keywords: list[str] = []

    for token in normalize_match_text(topic).split():
        if token in _TOPIC_STOPWORDS:
            continue
        if len(token) == 1:
            continue
        if token.isdigit():
            continue
        keywords.append(token)

    return tuple(dict.fromkeys(keywords))
