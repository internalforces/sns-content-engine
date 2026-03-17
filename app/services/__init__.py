"""Service package exports."""

from app.services.deduplication import SourceItemDeduper

__all__ = [
    "SourceItemDeduper",
]
