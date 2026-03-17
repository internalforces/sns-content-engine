"""Domain models for deterministic account matching."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True, slots=True)
class AccountMatchCandidate:
    """Scored matching result for one account."""

    account_key: str
    score: int
    eligible: bool
    include_keyword_hits: tuple[str, ...] = ()
    exclude_keyword_hits: tuple[str, ...] = ()
    source_tag_hits: tuple[str, ...] = ()
    topic_keyword_hits: tuple[str, ...] = ()
    strict_topic_guard_applied: bool = False
    strict_topic_guard_passed: bool = True

    @property
    def blocked_by_exclude_keywords(self) -> bool:
        """Return whether exclude keywords blocked an otherwise positive match."""

        return bool(self.exclude_keyword_hits)

    @property
    def blocked_by_topic_guard(self) -> bool:
        """Return whether strict topic guard blocked the match."""

        return self.strict_topic_guard_applied and not self.strict_topic_guard_passed


def select_top_account_candidates(
    candidates: Iterable[AccountMatchCandidate],
) -> tuple[AccountMatchCandidate, ...]:
    """Return the highest-scoring eligible match candidates."""

    eligible_candidates = [candidate for candidate in candidates if candidate.eligible]
    if not eligible_candidates:
        return ()

    top_score = max(candidate.score for candidate in eligible_candidates)
    return tuple(
        sorted(
            (
                candidate
                for candidate in eligible_candidates
                if candidate.score == top_score
            ),
            key=lambda candidate: candidate.account_key,
        )
    )
