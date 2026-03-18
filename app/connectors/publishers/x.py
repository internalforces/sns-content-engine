"""X publisher adapter with an isolated HTTP client boundary."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Protocol
from urllib import error, request

from app.connectors.publishers.base import PublishRequest, PublishResult

_CREATE_POST_URL = "https://api.x.com/2/tweets"


@dataclass(frozen=True, slots=True)
class XHttpResponse:
    """Normalized HTTP response returned by the X client boundary."""

    status_code: int
    payload: Any


class XHttpClient(Protocol):
    """HTTP boundary for X API requests."""

    def create_post(self, *, access_token: str, text: str) -> XHttpResponse:
        """Create a text-only X post for the authenticated user."""


class XPublisher:
    """Publish text-only posts through the X API."""

    provider_name = "x"

    def __init__(
        self,
        *,
        access_token: str,
        credential_ref: str | None = None,
        http_client: XHttpClient | None = None,
    ) -> None:
        normalized_access_token = access_token.strip()
        if not normalized_access_token:
            raise ValueError("access_token must not be empty")

        self.credential_ref = credential_ref
        self._access_token = normalized_access_token
        self._http_client = http_client or _UrlLibXHttpClient()

    def publish(self, request: PublishRequest) -> PublishResult:
        try:
            response = self._http_client.create_post(
                access_token=self._access_token,
                text=request.body,
            )
        except Exception as exc:
            return PublishResult(
                status="failed",
                error_message=f"X publish request failed: {exc}",
                provider=self.provider_name,
                credential_ref=self.credential_ref,
            )

        provider_payload = {"http_status": response.status_code}
        normalized_response_payload = _normalize_provider_payload(response.payload)
        if normalized_response_payload is not None:
            provider_payload["response"] = normalized_response_payload

        if response.status_code < 200 or response.status_code >= 300:
            return PublishResult(
                status="failed",
                error_message=_extract_error_message(
                    response.payload,
                    default=f"X publish failed with status {response.status_code}",
                ),
                provider=self.provider_name,
                credential_ref=self.credential_ref,
                provider_payload=provider_payload,
            )

        if not isinstance(response.payload, dict):
            return PublishResult(
                status="failed",
                error_message="malformed X publish response: expected a JSON object payload",
                provider=self.provider_name,
                credential_ref=self.credential_ref,
                provider_payload=provider_payload,
            )

        data = response.payload.get("data")
        if not isinstance(data, dict):
            return PublishResult(
                status="failed",
                error_message="malformed X publish response: missing data object",
                provider=self.provider_name,
                credential_ref=self.credential_ref,
                provider_payload=provider_payload,
            )

        external_post_id = data.get("id")
        if not isinstance(external_post_id, str) or not external_post_id.strip():
            return PublishResult(
                status="failed",
                error_message="malformed X publish response: missing data.id",
                provider=self.provider_name,
                credential_ref=self.credential_ref,
                provider_payload=provider_payload,
            )

        return PublishResult(
            status="published",
            external_post_id=external_post_id.strip(),
            provider=self.provider_name,
            credential_ref=self.credential_ref,
            provider_payload=provider_payload,
        )


class _UrlLibXHttpClient:
    """Minimal urllib-based client for the X create-post endpoint."""

    def __init__(self, *, timeout_seconds: float = 30.0) -> None:
        self._timeout_seconds = timeout_seconds

    def create_post(self, *, access_token: str, text: str) -> XHttpResponse:
        payload = json.dumps({"text": text}).encode("utf-8")
        http_request = request.Request(
            _CREATE_POST_URL,
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "User-Agent": "sns-content-engine/0.1.0",
            },
        )

        try:
            with request.urlopen(http_request, timeout=self._timeout_seconds) as response:
                return XHttpResponse(
                    status_code=response.getcode(),
                    payload=_load_json_payload(response.read()),
                )
        except error.HTTPError as exc:
            return XHttpResponse(
                status_code=exc.code,
                payload=_load_json_payload(exc.read()),
            )
        except error.URLError as exc:
            raise RuntimeError(f"network error: {exc.reason}") from exc


def _load_json_payload(raw_body: bytes) -> Any:
    if not raw_body:
        return {}

    decoded = raw_body.decode("utf-8", errors="replace")
    try:
        return json.loads(decoded)
    except json.JSONDecodeError:
        return {"raw_body": decoded}


def _normalize_provider_payload(payload: Any) -> dict[str, Any] | None:
    if payload is None:
        return None
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, list):
        return {"items": payload}
    return {"raw_body": str(payload)}


def _extract_error_message(payload: Any, *, default: str) -> str:
    if isinstance(payload, dict):
        errors = payload.get("errors")
        if isinstance(errors, list):
            for item in errors:
                if not isinstance(item, dict):
                    continue
                detail = item.get("detail")
                title = item.get("title")
                if isinstance(detail, str) and detail.strip():
                    return detail.strip()
                if isinstance(title, str) and title.strip():
                    return title.strip()

        detail = payload.get("detail")
        if isinstance(detail, str) and detail.strip():
            return detail.strip()

        message = payload.get("message")
        if isinstance(message, str) and message.strip():
            return message.strip()

    return default

