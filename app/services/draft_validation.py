"""Draft validation service for manual review workflows."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Literal
import re

from app.config import AccountConfig
from app.storage import ContentBrief, DraftVariant, DraftVariantState

DraftValidationSeverity = Literal["error", "warning"]

_WHITESPACE_RE = re.compile(r"\s+")
_NON_WORD_RE = re.compile(r"[^\w\s]")
_URL_RE = re.compile(r"https?://\S+")
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
    normalized_body = _normalize_match_text(body)
    issues: list[DraftValidationIssue] = []

    for phrase in banned_phrases:
        if not _matches_phrase(phrase, normalized_body):
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
    normalized_body = _normalize_match_text(body)
    candidates = _build_topic_candidates(account, content_brief)
    if not candidates or any(_matches_phrase(candidate, normalized_body) for candidate in candidates):
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
        *_topic_keywords(account.topic),
    ]
    normalized = [_normalize_match_text(candidate) for candidate in candidates]
    return tuple(dict.fromkeys(candidate for candidate in normalized if candidate))


def _topic_keywords(topic: str) -> tuple[str, ...]:
    keywords: list[str] = []

    for token in _normalize_match_text(topic).split():
        if token in _TOPIC_STOPWORDS:
            continue
        if len(token) == 1:
            continue
        if token.isdigit():
            continue
        keywords.append(token)

    return tuple(dict.fromkeys(keywords))


def _matches_phrase(phrase: str, normalized_text: str) -> bool:
    normalized_phrase = _normalize_match_text(phrase)
    if not normalized_phrase:
        return False
    return f" {normalized_phrase} " in f" {normalized_text} "


def _normalize_body(value: str) -> str:
    return _WHITESPACE_RE.sub(" ", value).strip()


def _normalize_match_text(value: str) -> str:
    normalized = _normalize_body(value).casefold().replace("-", " ").replace("_", " ")
    normalized = _NON_WORD_RE.sub(" ", normalized)
    return _WHITESPACE_RE.sub(" ", normalized).strip()
