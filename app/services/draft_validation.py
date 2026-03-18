"""Draft validation service for manual review workflows."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Literal
import re
from urllib import error, request
from urllib.parse import urlsplit

from app.config import AccountConfig
from app.services.topic_matching import contains_phrase, normalize_match_text, strip_urls, topic_keywords
from app.storage import ContentBrief, DraftVariant, DraftVariantState

DraftValidationSeverity = Literal["error", "warning"]
LandingUrlStatusFetcher = Callable[[str], int]

_WHITESPACE_RE = re.compile(r"\s+")
_URL_RE = re.compile(r"https?://\S+")
_LANDING_URL_TIMEOUT_SECONDS = 10.0


@dataclass(frozen=True, slots=True)
class DraftValidationIssue:
    """A single structured validation finding for a draft body."""

    code: str
    message: str
    severity: DraftValidationSeverity
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DraftValidationResult:
    """Structured validation result with blocking errors and soft warnings."""

    issues: tuple[DraftValidationIssue, ...] = ()

    @property
    def errors(self) -> tuple[DraftValidationIssue, ...]:
        """Return blocking validation issues."""

        return tuple(issue for issue in self.issues if issue.severity == "error")

    @property
    def warnings(self) -> tuple[DraftValidationIssue, ...]:
        """Return non-blocking validation issues."""

        return tuple(issue for issue in self.issues if issue.severity == "warning")

    @property
    def is_valid(self) -> bool:
        """Return whether the draft can proceed despite any warnings."""

        return not self.errors


class DraftValidator:
    """Validate draft bodies using account and channel configuration."""

    def validate(
        self,
        body: str,
        *,
        content_brief: ContentBrief,
        account_key: str,
        account: AccountConfig,
        channel: str,
        recent_drafts: Sequence[DraftVariant] = (),
        draft_id: int | None = None,
        now: datetime | None = None,
        landing_url_status_fetcher: LandingUrlStatusFetcher | None = None,
    ) -> DraftValidationResult:
        if channel not in account.channels:
            raise ValueError(f"account {account_key!r} does not define channel {channel!r}")

        channel_config = account.channels[channel]
        normalized_body = _normalize_body(body)
        issue_list: list[DraftValidationIssue] = []

        issue_list.extend(
            _validate_char_limit(
                normalized_body,
                max_chars=channel_config.render.max_chars,
            )
        )
        issue_list.extend(
            _validate_link_count(
                normalized_body,
                max_links=channel_config.validation.max_links,
            )
        )
        issue_list.extend(
            _validate_banned_phrases(
                normalized_body,
                banned_phrases=channel_config.validation.banned_phrases,
            )
        )
        issue_list.extend(
            _validate_recent_duplicates(
                normalized_body,
                account_key=account_key,
                channel=channel,
                recent_drafts=recent_drafts,
                draft_id=draft_id,
                recent_duplicate_window_days=channel_config.validation.recent_duplicate_window_days,
                now=now,
            )
        )
        issue_list.extend(
            _validate_landing_url_rules(
                normalized_body,
                content_brief=content_brief,
                account=account,
                landing_url_status_fetcher=landing_url_status_fetcher,
            )
        )
        issue_list.extend(
            _validate_profile_rules(
                normalized_body,
                content_brief=content_brief,
                account_key=account_key,
                account=account,
            )
        )

        return DraftValidationResult(issues=tuple(issue_list))


def _validate_char_limit(body: str, *, max_chars: int) -> tuple[DraftValidationIssue, ...]:
    actual_chars = len(body)
    if actual_chars <= max_chars:
        return ()

    return (
        DraftValidationIssue(
            code="max_chars_exceeded",
            message=f"draft exceeds max_chars ({actual_chars} > {max_chars})",
            severity="error",
            metadata={"actual_chars": actual_chars, "max_chars": max_chars},
        ),
    )


def _validate_link_count(body: str, *, max_links: int) -> tuple[DraftValidationIssue, ...]:
    actual_links = len(_URL_RE.findall(body))
    if actual_links <= max_links:
        return ()

    return (
        DraftValidationIssue(
            code="max_links_exceeded",
            message=f"draft exceeds max_links ({actual_links} > {max_links})",
            severity="error",
            metadata={"actual_links": actual_links, "max_links": max_links},
        ),
    )


def _validate_banned_phrases(
    body: str,
    *,
    banned_phrases: tuple[str, ...],
) -> tuple[DraftValidationIssue, ...]:
    normalized_body = normalize_match_text(body)
    issues: list[DraftValidationIssue] = []

    for phrase in banned_phrases:
        if not contains_phrase(phrase, normalized_body):
            continue

        issues.append(
            DraftValidationIssue(
                code="banned_phrase",
                message=f"draft contains banned phrase {phrase!r}",
                severity="error",
                metadata={"phrase": phrase},
            )
        )

    return tuple(issues)


def _validate_recent_duplicates(
    body: str,
    *,
    account_key: str,
    channel: str,
    recent_drafts: Sequence[DraftVariant],
    draft_id: int | None,
    recent_duplicate_window_days: int,
    now: datetime | None,
) -> tuple[DraftValidationIssue, ...]:
    if not recent_drafts:
        return ()

    reference_time = now or datetime.now(timezone.utc)
    created_since = reference_time - timedelta(days=recent_duplicate_window_days)
    normalized_body = _normalize_body(body).casefold()

    for recent_draft in recent_drafts:
        if recent_draft.id == draft_id:
            continue
        if recent_draft.channel != channel:
            continue
        if recent_draft.state is DraftVariantState.REJECTED:
            continue
        if recent_draft.created_at < created_since:
            continue

        brief = recent_draft.content_brief
        if brief is not None and brief.account_key != account_key:
            continue

        if _normalize_body(recent_draft.body).casefold() != normalized_body:
            continue

        return (
            DraftValidationIssue(
                code="recent_duplicate",
                message=f"draft duplicates recent draft {recent_draft.id}",
                severity="error",
                metadata={
                    "matching_draft_id": recent_draft.id,
                    "matching_created_at": recent_draft.created_at.isoformat(),
                },
            ),
        )

    return ()


def _validate_landing_url_rules(
    body: str,
    *,
    content_brief: ContentBrief,
    account: AccountConfig,
    landing_url_status_fetcher: LandingUrlStatusFetcher | None,
) -> tuple[DraftValidationIssue, ...]:
    expected_landing_url = content_brief.landing_url
    body_urls = tuple(_URL_RE.findall(body))
    issues: list[DraftValidationIssue] = []

    if expected_landing_url not in body_urls:
        issue_code = "landing_url_missing" if not body_urls else "landing_url_mismatch"
        message = (
            "draft is missing the expected landing URL"
            if issue_code == "landing_url_missing"
            else "draft uses a landing URL that does not match the content brief"
        )
        issues.append(
            DraftValidationIssue(
                code=issue_code,
                message=message,
                severity="error",
                metadata={
                    "expected_landing_url": expected_landing_url,
                    "body_urls": body_urls,
                },
            )
        )
        return tuple(issues)

    issues.extend(
        _validate_landing_url_prefixes(
            expected_landing_url,
            allowed_url_prefixes=tuple(
                str(prefix) for prefix in account.landing.validation.allowed_url_prefixes
            ),
        )
    )

    if account.landing.validation.require_live_url:
        issues.extend(
            _validate_live_landing_url(
                expected_landing_url,
                landing_url_status_fetcher=landing_url_status_fetcher or fetch_landing_url_status,
            )
        )

    return tuple(issues)


def _validate_landing_url_prefixes(
    landing_url: str,
    *,
    allowed_url_prefixes: tuple[str, ...],
) -> tuple[DraftValidationIssue, ...]:
    if not allowed_url_prefixes:
        return ()

    if any(_url_matches_prefix(landing_url, prefix) for prefix in allowed_url_prefixes):
        return ()

    return (
        DraftValidationIssue(
            code="landing_url_disallowed",
            message="landing URL is outside the allowed landing prefix set",
            severity="error",
            metadata={
                "landing_url": landing_url,
                "allowed_url_prefixes": allowed_url_prefixes,
            },
        ),
    )


def _validate_live_landing_url(
    landing_url: str,
    *,
    landing_url_status_fetcher: LandingUrlStatusFetcher,
) -> tuple[DraftValidationIssue, ...]:
    try:
        status_code = landing_url_status_fetcher(landing_url)
    except OSError as exc:
        return (
            DraftValidationIssue(
                code="landing_url_unreachable",
                message=f"landing URL could not be verified: {exc}",
                severity="error",
                metadata={"landing_url": landing_url},
            ),
        )

    if 200 <= status_code < 400:
        return ()

    return (
        DraftValidationIssue(
            code="landing_url_unreachable",
            message=f"landing URL returned HTTP {status_code}",
            severity="error",
            metadata={"landing_url": landing_url, "status_code": status_code},
        ),
    )


def fetch_landing_url_status(url: str, *, timeout_seconds: float = _LANDING_URL_TIMEOUT_SECONDS) -> int:
    """Return the final HTTP status code for a landing URL."""

    for method in ("HEAD", "GET"):
        try:
            http_request = request.Request(url, method=method)
            with request.urlopen(http_request, timeout=timeout_seconds) as response:
                return response.getcode()
        except error.HTTPError as exc:
            if method == "HEAD" and exc.code in {405, 501}:
                continue
            raise OSError(f"HTTP {exc.code}") from exc
        except error.URLError as exc:
            reason = getattr(exc, "reason", exc)
            raise OSError(str(reason)) from exc
        except OSError as exc:
            raise OSError(str(exc)) from exc

    raise OSError("could not verify landing URL")


def _url_matches_prefix(url: str, prefix: str) -> bool:
    normalized_url = urlsplit(url)
    normalized_prefix = urlsplit(prefix)

    if (
        normalized_url.scheme.casefold() != normalized_prefix.scheme.casefold()
        or normalized_url.netloc.casefold() != normalized_prefix.netloc.casefold()
    ):
        return False

    url_path = normalized_url.path.rstrip("/")
    prefix_path = normalized_prefix.path.rstrip("/")

    if not prefix_path:
        return True
    if url_path == prefix_path:
        return True
    return url_path.startswith(f"{prefix_path}/")


def _validate_profile_rules(
    body: str,
    *,
    content_brief: ContentBrief,
    account_key: str,
    account: AccountConfig,
) -> tuple[DraftValidationIssue, ...]:
    profile_validators = {
        "standard": _validate_standard_profile,
        "finance_strict": _validate_finance_profile,
    }
    return profile_validators[account.validation.profile](
        body,
        content_brief=content_brief,
        account_key=account_key,
        account=account,
    )


def _validate_standard_profile(
    body: str,
    *,
    content_brief: ContentBrief,
    account_key: str,
    account: AccountConfig,
) -> tuple[DraftValidationIssue, ...]:
    return _validate_topic_guard(
        body,
        content_brief=content_brief,
        account_key=account_key,
        account=account,
        hard_failure=account.matching.strict_topic_guard,
    )


def _validate_finance_profile(
    body: str,
    *,
    content_brief: ContentBrief,
    account_key: str,
    account: AccountConfig,
) -> tuple[DraftValidationIssue, ...]:
    return _validate_topic_guard(
        body,
        content_brief=content_brief,
        account_key=account_key,
        account=account,
        hard_failure=True,
    )


def _validate_topic_guard(
    body: str,
    *,
    content_brief: ContentBrief,
    account_key: str,
    account: AccountConfig,
    hard_failure: bool,
) -> tuple[DraftValidationIssue, ...]:
    normalized_body = normalize_match_text(strip_urls(body))
    candidates = _build_topic_candidates(account, content_brief)
    if not candidates or any(contains_phrase(candidate, normalized_body) for candidate in candidates):
        return ()

    severity: DraftValidationSeverity = "error" if hard_failure else "warning"
    return (
        DraftValidationIssue(
            code="topic_guard_failed",
            message=f"draft does not include on-topic keywords for account {account_key!r}",
            severity=severity,
            metadata={"candidates": candidates, "profile": account.validation.profile},
        ),
    )


def _build_topic_candidates(
    account: AccountConfig,
    content_brief: ContentBrief,
) -> tuple[str, ...]:
    candidates = [
        *account.matching.include_keywords,
        *account.matching.source_tags,
        *content_brief.tags,
        *topic_keywords(account.topic),
    ]
    normalized = [normalize_match_text(candidate) for candidate in candidates]
    return tuple(dict.fromkeys(candidate for candidate in normalized if candidate))


def _normalize_body(value: str) -> str:
    return _WHITESPACE_RE.sub(" ", value).strip()
