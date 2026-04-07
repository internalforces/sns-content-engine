"""Lightweight HTML article extraction for finance-source enrichment."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from html import unescape
from html.parser import HTMLParser
import re

from app.domain.extraction_selectors import (
    EXTRACTION_SELECTOR_RE,
    normalize_extraction_selector,
)

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


@dataclass(frozen=True, slots=True)
class _SelectorRule:
    tag: str | None
    id_value: str | None
    class_name: str | None

    def matches(
        self,
        *,
        tag: str,
        id_value: str | None,
        class_names: frozenset[str],
    ) -> bool:
        if self.tag is not None and self.tag != tag:
            return False
        if self.id_value is not None and self.id_value != id_value:
            return False
        if self.class_name is not None and self.class_name not in class_names:
            return False
        return True


@dataclass(frozen=True, slots=True)
class _ElementFrame:
    tag: str
    starts_preferred_scope: bool
    starts_excluded_scope: bool


class ArticleExtractor:
    """Extract title, source metadata, and article text from fetched HTML."""

    def __init__(
        self,
        *,
        minimum_word_count: int = 30,
        preferred_selectors: tuple[str, ...] | list[str] = (),
        excluded_selectors: tuple[str, ...] | list[str] = (),
    ) -> None:
        self._minimum_word_count = minimum_word_count
        self._preferred_selectors = tuple(
            parse_extraction_selector(selector) for selector in preferred_selectors
        )
        self._excluded_selectors = tuple(
            parse_extraction_selector(selector) for selector in excluded_selectors
        )

    @property
    def minimum_word_count(self) -> int:
        return self._minimum_word_count

    def extract(self, html: str) -> ArticleExtractResult:
        parser = _ArticleHtmlParser(
            preferred_selectors=self._preferred_selectors,
            excluded_selectors=self._excluded_selectors,
        )
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
    def __init__(
        self,
        *,
        preferred_selectors: tuple[_SelectorRule, ...],
        excluded_selectors: tuple[_SelectorRule, ...],
    ) -> None:
        super().__init__(convert_charrefs=True)
        self.title: str | None = None
        self.source_name: str | None = None
        self.published_at: str | None = None
        self.metadata: dict[str, str] = {}
        self._stack: list[_ElementFrame] = []
        self._ignored_depth = 0
        self._excluded_depth = 0
        self._in_title = False
        self._article_depth = 0
        self._main_depth = 0
        self._preferred_depth = 0
        self._body_text: list[str] = []
        self._article_text: list[str] = []
        self._main_text: list[str] = []
        self._preferred_text: list[str] = []
        self._preferred_selectors = preferred_selectors
        self._excluded_selectors = excluded_selectors

    def handle_starttag(self, tag: str, attrs) -> None:
        normalized_tag = tag.casefold()
        attrs_map = {key.casefold(): value for key, value in attrs if key is not None}
        normalized_id = _normalize_selector_token(attrs_map.get("id"))
        class_names = _normalize_class_names(attrs_map.get("class"))
        starts_preferred_scope = any(
            selector.matches(
                tag=normalized_tag,
                id_value=normalized_id,
                class_names=class_names,
            )
            for selector in self._preferred_selectors
        )
        starts_excluded_scope = any(
            selector.matches(
                tag=normalized_tag,
                id_value=normalized_id,
                class_names=class_names,
            )
            for selector in self._excluded_selectors
        )
        self._stack.append(
            _ElementFrame(
                tag=normalized_tag,
                starts_preferred_scope=starts_preferred_scope,
                starts_excluded_scope=starts_excluded_scope,
            )
        )
        if normalized_tag == "article":
            self._article_depth += 1
        if normalized_tag == "main":
            self._main_depth += 1
        if starts_preferred_scope:
            self._preferred_depth += 1
        if starts_excluded_scope:
            self._excluded_depth += 1

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

    def handle_data(self, data: str) -> None:
        if self._ignored_depth > 0 or self._excluded_depth > 0:
            return
        normalized = _normalize_text(data)
        if not normalized:
            return
        if self._in_title and self.title is None:
            self.title = normalized
        self._body_text.append(normalized)
        if self._article_depth > 0:
            self._article_text.append(normalized)
        if self._main_depth > 0:
            self._main_text.append(normalized)
        if self._preferred_depth > 0:
            self._preferred_text.append(normalized)

    def best_text(self) -> str:
        if self._preferred_text:
            return "\n".join(self._preferred_text)
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
        if self._preferred_text and self._preferred_text[-1] != "\n":
            self._preferred_text.append("\n")

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

    def handle_endtag(self, tag: str) -> None:
        normalized_tag = tag.casefold()
        frame: _ElementFrame | None = None
        if self._stack:
            frame = self._stack.pop()
            if frame.tag == "article" and self._article_depth > 0:
                self._article_depth -= 1
            if frame.tag == "main" and self._main_depth > 0:
                self._main_depth -= 1
            if frame.starts_preferred_scope and self._preferred_depth > 0:
                self._preferred_depth -= 1
            if frame.starts_excluded_scope and self._excluded_depth > 0:
                self._excluded_depth -= 1
        if normalized_tag in _IGNORED_TAGS and self._ignored_depth > 0:
            self._ignored_depth -= 1
            return
        if normalized_tag == "title":
            self._in_title = False
            return
        if normalized_tag in _BLOCK_TAGS:
            self._append_breaks()


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = _MULTISPACE_RE.sub(" ", unescape(value)).strip()
    return normalized or None


def _word_count(text: str) -> int:
    return len([word for word in text.split(" ") if word])


def parse_extraction_selector(value: str) -> _SelectorRule:
    normalized = normalize_extraction_selector(value)
    match = EXTRACTION_SELECTOR_RE.fullmatch(normalized)
    assert match is not None  # normalized values are validated by normalize_extraction_selector
    return _SelectorRule(
        tag=match.group("tag"),
        id_value=match.group("id_value"),
        class_name=match.group("class_name"),
    )


def _normalize_selector_token(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().casefold()
    return normalized or None


def _normalize_class_names(value: str | None) -> frozenset[str]:
    if value is None:
        return frozenset()
    return frozenset(
        token.casefold()
        for token in value.split()
        if token.strip()
    )


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
