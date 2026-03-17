"""Domain models for platform-neutral content briefs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ContentBriefAngle = Literal[
    "practical_how_to",
    "product_update",
    "trend_insight",
    "topic_takeaway",
]


@dataclass(frozen=True, slots=True)
class ContentBriefData:
    """Platform-neutral brief payload for downstream draft generation."""

    account_id: str
    source_item_id: int
    source_title: str
    source_summary: str | None
    key_points: tuple[str, ...]
    tags: tuple[str, ...]
    angle: ContentBriefAngle
    landing_url: str
    language: str
