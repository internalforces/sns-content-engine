"""HTML article fetch service for finance-source enrichment."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

_DEFAULT_TIMEOUT_SECONDS = 15.0
_DEFAULT_USER_AGENT = "sns-content-engine/finance-local-mvp (+https://example.local)"
_HTML_CONTENT_TYPES = ("text/html", "application/xhtml+xml")


class HtmlResponse(Protocol):
    """Protocol describing the subset of response methods used by the fetcher."""

    headers: object

    def read(self) -> bytes: ...


class HtmlFetcherError(RuntimeError):
    """Raised when article HTML cannot be fetched safely."""

    def __init__(self, *, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True, slots=True)
class HtmlFetchResult:
    """Successful HTML fetch payload."""

    article_url: str
    html: str
    content_type: str | None = None
    final_url: str | None = None


class ArticleHtmlFetcher:
    """Fetch one article web page with conservative network defaults."""

    def __init__(
        self,
        *,
        opener=None,
        timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
        user_agent: str = _DEFAULT_USER_AGENT,
    ) -> None:
        self._opener = opener or _default_urlopen
        self._timeout_seconds = timeout_seconds
        self._user_agent = user_agent.strip() or _DEFAULT_USER_AGENT

    def fetch(self, article_url: str) -> HtmlFetchResult:
        request = Request(article_url, headers={"User-Agent": self._user_agent})
        try:
            response = self._opener(request, timeout=self._timeout_seconds)
            with response:
                content_type = _extract_content_type(response.headers)
                if content_type is not None and not _is_html_content_type(content_type):
                    raise HtmlFetcherError(
                        code="fetch_not_html",
                        message="기사 HTML이 아닌 응답이라 본문 수집을 건너뛰었어요",
                    )
                raw_bytes = response.read()
                html = _decode_html_bytes(raw_bytes, response.headers)
                if not html.strip():
                    raise HtmlFetcherError(
                        code="fetch_empty",
                        message="기사 HTML이 비어 있어 본문 수집을 진행하지 않았어요",
                    )
                final_url = getattr(response, "url", None)
                return HtmlFetchResult(
                    article_url=article_url,
                    html=html,
                    content_type=content_type,
                    final_url=final_url,
                )
        except HtmlFetcherError:
            raise
        except HTTPError as exc:
            code = "fetch_blocked" if exc.code in {401, 403, 429} else "fetch_failed"
            message = (
                "사이트 접근이 차단되었어요"
                if code == "fetch_blocked"
                else f"기사 페이지를 가져오지 못했어요 (HTTP {exc.code})"
            )
            raise HtmlFetcherError(code=code, message=message) from exc
        except URLError as exc:
            raise HtmlFetcherError(
                code="fetch_failed",
                message=f"기사 페이지를 가져오지 못했어요 ({getattr(exc, 'reason', exc)})",
            ) from exc
        except OSError as exc:
            raise HtmlFetcherError(
                code="fetch_failed",
                message=f"기사 페이지를 가져오지 못했어요 ({exc})",
            ) from exc


def _default_urlopen(request: Request, *, timeout: float):
    return urlopen(request, timeout=timeout)


def _extract_content_type(headers) -> str | None:
    if headers is None:
        return None
    getter = getattr(headers, "get_content_type", None)
    if callable(getter):
        content_type = getter()
        return content_type.strip().lower() if content_type else None

    raw_content_type = headers.get("Content-Type") if hasattr(headers, "get") else None
    if raw_content_type is None:
        return None
    return raw_content_type.split(";", maxsplit=1)[0].strip().lower() or None


def _extract_charset(headers) -> str | None:
    if headers is None:
        return None
    getter = getattr(headers, "get_content_charset", None)
    if callable(getter):
        charset = getter()
        return charset.strip() if charset else None

    raw_content_type = headers.get("Content-Type") if hasattr(headers, "get") else None
    if raw_content_type is None:
        return None
    for part in raw_content_type.split(";"):
        if "charset=" not in part.casefold():
            continue
        _, value = part.split("=", maxsplit=1)
        normalized = value.strip().strip('"').strip("'")
        if normalized:
            return normalized
    return None


def _is_html_content_type(content_type: str) -> bool:
    normalized = content_type.strip().lower()
    return any(normalized == allowed for allowed in _HTML_CONTENT_TYPES)


def _decode_html_bytes(raw_bytes: bytes, headers) -> str:
    encodings = []
    encodings.append(_extract_charset(headers))
    encodings.extend(("utf-8", "utf-8-sig", "cp1252"))

    for encoding in encodings:
        if not encoding:
            continue
        try:
            return raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue

    return raw_bytes.decode("utf-8", errors="replace")
