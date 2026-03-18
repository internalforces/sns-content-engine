"""Deterministic article-summary regeneration for finance content."""

from __future__ import annotations

from dataclasses import dataclass
import re

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_MULTISPACE_RE = re.compile(r"\s+")
_NON_WORD_RE = re.compile(r"[^a-z0-9\s]")
_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "is",
    "it", "of", "on", "or", "that", "the", "to", "was", "were", "with",
}
_FINANCE_PRIORITY_TERMS = {
    "earnings", "market", "markets", "stocks", "shares", "policy", "inflation", "rates",
    "economy", "bond", "bonds", "bank", "banks", "guidance", "revenue", "profit", "federal",
    "central", "treasury", "credit", "demand", "macro",
}
_DISALLOWED_ADVICE_RE = re.compile(r"\b(buy|sell|strong buy|strong sell|price target|guaranteed)\b", re.I)


class SummaryRegenerationError(RuntimeError):
    """Raised when deterministic summary regeneration cannot proceed."""

    def __init__(self, *, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True, slots=True)
class RegeneratedSummary:
    """Deterministic summary payload derived from article text."""

    summary: str
    key_points: tuple[str, ...]
    method: str = "deterministic_finance"


class SummaryRegenerator:
    """Create a short finance-safe summary and key points from article text."""

    def __init__(self, *, minimum_word_count: int = 40, max_key_points: int = 4) -> None:
        self._minimum_word_count = minimum_word_count
        self._max_key_points = max(3, max_key_points)

    def regenerate(
        self,
        *,
        title: str,
        article_text: str,
        rss_description: str | None = None,
    ) -> RegeneratedSummary:
        normalized_text = _normalize_text(article_text)
        if _word_count(normalized_text) < self._minimum_word_count:
            raise SummaryRegenerationError(
                code="content_too_short",
                message="기사 내용이 너무 짧아 요약하지 않았어요",
            )

        sentences = [sentence for sentence in _split_sentences(normalized_text) if sentence]
        if not sentences:
            raise SummaryRegenerationError(
                code="summary_failed",
                message="기사 요약을 만들지 못했어요",
            )

        scored_sentences = sorted(
            sentences,
            key=lambda sentence: _sentence_score(sentence, title=title),
            reverse=True,
        )
        key_points = _dedupe_points(scored_sentences, limit=self._max_key_points)
        if len(key_points) < 3 and rss_description:
            fallback_point = _normalize_point(rss_description)
            if fallback_point and fallback_point not in key_points:
                key_points = (*key_points, fallback_point)
        if len(key_points) < 3:
            raise SummaryRegenerationError(
                code="summary_failed",
                message="기사 요약을 만들지 못했어요",
            )

        summary = _compose_summary(title=title, key_points=key_points)
        return RegeneratedSummary(summary=summary, key_points=key_points[: self._max_key_points])


def _split_sentences(text: str) -> tuple[str, ...]:
    return tuple(_normalize_point(part) for part in _SENTENCE_SPLIT_RE.split(text) if _normalize_point(part))


def _normalize_text(value: str) -> str:
    return _MULTISPACE_RE.sub(" ", value).strip()


def _normalize_point(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = _MULTISPACE_RE.sub(" ", value).strip(" .")
    if not normalized:
        return None
    return _DISALLOWED_ADVICE_RE.sub("", normalized).strip(" ,.") or None


def _word_count(value: str) -> int:
    return len([word for word in value.split(" ") if word])


def _sentence_score(sentence: str, *, title: str) -> tuple[int, int, int]:
    title_terms = _token_set(title)
    sentence_terms = _token_set(sentence)
    overlap = len(title_terms & sentence_terms)
    finance_hits = len(sentence_terms & _FINANCE_PRIORITY_TERMS)
    length_bonus = min(len(sentence.split()), 30)
    return (finance_hits, overlap, length_bonus)


def _token_set(value: str) -> set[str]:
    normalized = _NON_WORD_RE.sub(" ", value.casefold())
    return {token for token in normalized.split() if token and token not in _STOPWORDS}


def _dedupe_points(sentences: list[str], *, limit: int) -> tuple[str, ...]:
    points: list[str] = []
    seen: set[str] = set()
    for sentence in sentences:
        point = _normalize_point(sentence)
        if point is None:
            continue
        key = point.casefold()
        if key in seen:
            continue
        seen.add(key)
        points.append(point)
        if len(points) == limit:
            break
    return tuple(points)


def _compose_summary(*, title: str, key_points: tuple[str, ...]) -> str:
    lead = _normalize_point(title) or "Finance update"
    supporting = "; ".join(key_points[:2])
    summary = f"{lead}: {supporting}."
    normalized = _MULTISPACE_RE.sub(" ", summary).strip()
    return normalized[:320]
