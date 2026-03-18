"""Lightweight HTML article extraction for finance-source enrichment."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from html import unescape
from html.parser import HTMLParser
import re

_MULTISPACE_RE = re.compile(r"\s+")
_IGNORED_TAGS = {"script", "style", "noscript", "svg"}
_BLOCK_TAGS = {
    "article",
    "aside",
    "blockquote",
    "br",
    "div",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "li",
    "main",
    "p",
    "section",
}
_PREFERRED_META_KEYS = (
    "article:published_time",
    "og:published_time",
    "datepublished",
    "date",
    "publishdate",
    "pubdate",
)
_SOURCE_META_KEYS = ("og:site_name", "application-name", "publisher")


class ArticleExtractError(RuntimeError):
    """Raised when article body extraction cannot continue safely."""

    def __init__(self, *, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True, slots=True)
class ArticleExtractResult:
    """Structured extraction output for one HTML article."""

    title: str | None
    source_name: str | None
    published_at: datetime | None
    article_text: str
    metadata: dict[str, str]


class ArticleExtractor:
    """Extract title, source metadata, and article text from fetched HTML."""

    def __init__(self, *, minimum_word_count: int = 30) -> None:
        self._minimum_word_count = minimum_word_count

    def extract(self, html: str) -> ArticleExtractResult:
        parser = _ArticleHtmlParser()
        parser.feed(html)
        parser.close()

        article_text = _normalize_text(parser.best_text())
        if not article_text:
            raise ArticleExtractError(
                code="extract_failed",
                message="기사 본문을 읽지 못했어요",
            )
        if _word_count(article_text) < self._minimum_word_count:
            raise ArticleExtractError(
                code="content_too_short",
                message="기사 내용이 너무 짧아 요약하지 않았어요",
            )

        return ArticleExtractResult(
            title=_normalize_text(parser.title),
            source_name=_normalize_text(parser.source_name),
            published_at=_parse_published_at(parser.published_at),
            article_text=article_text,
            metadata=parser.metadata,
        )


class _ArticleHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title: str | None = None
        self.source_name: str | None = None
        self.published_at: str | None = None
        self.metadata: dict[str, str] = {}
        self._stack: list[str] = []
        self._ignored_depth = 0
        self._in_title = False
        self._body_text: list[str] = []
        self._article_text: list[str] = []
        self._main_text: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        normalized_tag = tag.casefold()
        self._stack.append(normalized_tag)
        attrs_map = {key.casefold(): value for key, value in attrs}

        if normalized_tag in _IGNORED_TAGS:
            self._ignored_depth += 1
            return
        if normalized_tag == "title":
            self._in_title = True
            return
        if normalized_tag == "meta":
            self._handle_meta(attrs_map)
            return
        if normalized_tag in _BLOCK_TAGS:
            self._append_breaks()

    def handle_endtag(self, tag: str) -> None:
        normalized_tag = tag.casefold()
        if self._stack:
            self._stack.pop()
        if normalized_tag in _IGNORED_TAGS and self._ignored_depth > 0:
            self._ignored_depth -= 1
            return
        if normalized_tag == "title":
            self._in_title = False
            return
        if normalized_tag in _BLOCK_TAGS:
            self._append_breaks()

    def handle_data(self, data: str) -> None:
        if self._ignored_depth > 0:
            return
        normalized = _normalize_text(data)
        if not normalized:
            return
        if self._in_title and self.title is None:
            self.title = normalized
        self._body_text.append(normalized)
        if "article" in self._stack:
            self._article_text.append(normalized)
        if "main" in self._stack:
            self._main_text.append(normalized)

    def best_text(self) -> str:
        if self._article_text:
            return "\n".join(self._article_text)
        if self._main_text:
            return "\n".join(self._main_text)
        return "\n".join(self._body_text)

    def _append_breaks(self) -> None:
        if self._body_text and self._body_text[-1] != "\n":
            self._body_text.append("\n")
        if self._article_text and self._article_text[-1] != "\n":
            self._article_text.append("\n")
        if self._main_text and self._main_text[-1] != "\n":
            self._main_text.append("\n")

    def _handle_meta(self, attrs_map: dict[str, str | None]) -> None:
        key = attrs_map.get("property") or attrs_map.get("name") or attrs_map.get("itemprop")
        content = attrs_map.get("content")
        if not key or not content:
            return
        normalized_key = key.casefold()
        normalized_content = _normalize_text(content)
        if not normalized_content:
            return
        self.metadata[normalized_key] = normalized_content
        if self.source_name is None and normalized_key in _SOURCE_META_KEYS:
            self.source_name = normalized_content
        if self.published_at is None and normalized_key in _PREFERRED_META_KEYS:
            self.published_at = normalized_content


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = _MULTISPACE_RE.sub(" ", unescape(value)).strip()
    return normalized or None


def _word_count(text: str) -> int:
    return len([word for word in text.split(" ") if word])


def _parse_published_at(value: str | None) -> datetime | None:
    if not value:
        return None

    normalized = value.strip()
    if not normalized:
        return None
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        for fmt in (
            "%a, %d %b %Y %H:%M:%S %z",
            "%Y-%m-%d %H:%M:%S%z",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ):
            try:
                parsed = datetime.strptime(normalized, fmt)
                break
            except ValueError:
                continue
        else:
            return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
