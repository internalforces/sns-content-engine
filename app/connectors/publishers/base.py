"""Platform-neutral publishing interfaces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from app.storage import PublishJob

PublishStatus = Literal["published", "failed", "dry_run"]


@dataclass(frozen=True, slots=True)
class PublishRequest:
    """Normalized publish payload passed to channel-specific publishers."""

    publish_job_id: int
    draft_variant_id: int
    account_key: str
    channel: str
    body: str
    idempotency_key: str


@dataclass(frozen=True, slots=True)
class PublishResult:
    """Normalized result returned by publisher adapters."""

    status: PublishStatus
    external_post_id: str | None = None
    error_message: str | None = None
    dry_run: bool = False
    provider: str | None = None
    credential_ref: str | None = None
    provider_payload: dict[str, Any] | None = None


class Publisher(Protocol):
    """Adapter boundary for publishing content to a specific channel."""

    provider_name: str
    credential_ref: str | None

    def publish(self, request: PublishRequest) -> PublishResult:
        """Publish the provided request and return a normalized result."""


class PublisherResolver(Protocol):
    """Resolve the correct publisher for a stored publish job."""

    def resolve(self, publish_job: "PublishJob") -> Publisher:
        """Return the publisher that should handle the given publish job."""

