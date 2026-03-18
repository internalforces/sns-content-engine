"""Deterministic fake publisher used by tests and safe local flows."""

from __future__ import annotations

from dataclasses import replace

from app.connectors.publishers.base import PublishRequest, PublishResult


class FakePublisher:
    """Fake publisher that records requests and returns a configurable result."""

    provider_name = "x"

    def __init__(
        self,
        *,
        result: PublishResult | None = None,
        credential_ref: str | None = "FAKE_X_PUBLISHER_CREDENTIALS",
    ) -> None:
        self.credential_ref = credential_ref
        self._result = result
        self.requests: list[PublishRequest] = []

    def publish(self, request: PublishRequest) -> PublishResult:
        self.requests.append(request)
        result = self._result or PublishResult(
            status="published",
            external_post_id=f"fake:{request.publish_job_id}",
            provider=self.provider_name,
            credential_ref=self.credential_ref,
        )
        return replace(
            result,
            provider=result.provider or self.provider_name,
            credential_ref=(
                result.credential_ref if result.credential_ref is not None else self.credential_ref
            ),
        )

