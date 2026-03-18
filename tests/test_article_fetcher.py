"""Tests for the article HTML fetch service."""

from __future__ import annotations

from email.message import Message
from urllib.error import HTTPError, URLError

import pytest

from app.services import ArticleHtmlFetcher, HtmlFetcherError


class _FakeResponse:
    def __init__(self, body: bytes, *, content_type: str = "text/html; charset=utf-8", url: str = "https://example.com/final") -> None:
        self._body = body
        self.headers = Message()
        self.headers["Content-Type"] = content_type
        self.url = url

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_article_html_fetcher_returns_html_payload() -> None:
    captured_headers: dict[str, str] = {}

    def fake_open(request, *, timeout: float):
        captured_headers["User-Agent"] = request.headers["User-agent"]
        assert timeout == 15.0
        return _FakeResponse(b"<html><body>markets update</body></html>")

    result = ArticleHtmlFetcher(opener=fake_open).fetch("https://example.com/articles/1")

    assert result.article_url == "https://example.com/articles/1"
    assert result.final_url == "https://example.com/final"
    assert "markets update" in result.html
    assert result.content_type == "text/html"
    assert captured_headers["User-Agent"].startswith("sns-content-engine/finance-local-mvp")


def test_article_html_fetcher_rejects_non_html_content() -> None:
    fetcher = ArticleHtmlFetcher(
        opener=lambda request, timeout: _FakeResponse(b"{}", content_type="application/json")
    )

    with pytest.raises(HtmlFetcherError) as exc_info:
        fetcher.fetch("https://example.com/api/article")

    assert exc_info.value.code == "fetch_not_html"
    assert exc_info.value.message == "기사 HTML이 아닌 응답이라 본문 수집을 건너뛰었어요"


def test_article_html_fetcher_maps_blocked_http_errors_to_readable_failure() -> None:
    def blocked_open(request, *, timeout: float):
        raise HTTPError(request.full_url, 403, "Forbidden", hdrs=None, fp=None)

    with pytest.raises(HtmlFetcherError) as exc_info:
        ArticleHtmlFetcher(opener=blocked_open).fetch("https://example.com/blocked")

    assert exc_info.value.code == "fetch_blocked"
    assert exc_info.value.message == "사이트 접근이 차단되었어요"


def test_article_html_fetcher_maps_network_errors_to_fetch_failed() -> None:
    def offline_open(request, *, timeout: float):
        raise URLError("offline")

    with pytest.raises(HtmlFetcherError) as exc_info:
        ArticleHtmlFetcher(opener=offline_open).fetch("https://example.com/offline")

    assert exc_info.value.code == "fetch_failed"
    assert "offline" in exc_info.value.message
