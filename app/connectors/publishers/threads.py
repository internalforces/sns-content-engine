"""Threads publisher adapter with an isolated HTTP client boundary."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Protocol
from urllib import error, request
from urllib.parse import quote, urlencode

from app.connectors.publishers.base import PublishRequest, PublishResult

_GRAPH_API_BASE_URL = "https://graph.threads.net/v1.0"


@dataclass(frozen=True, slots=True)
class ThreadsHttpResponse:
    """Normalized HTTP response returned by the Threads client boundary."""

    status_code: int
    payload: Any


class ThreadsHttpClient(Protocol):
    """HTTP boundary for the two-step Threads publishing flow."""

    def create_container(
        self,
        *,
        access_token: str,
        threads_user_id: str,
        text: str,
    ) -> ThreadsHttpResponse:
        """Create a text-only Threads media container for the authenticated user."""

    def publish_container(
        self,
        *,
        access_token: str,
        threads_user_id: str,
        creation_id: str,
    ) -> ThreadsHttpResponse:
        """Publish a previously created Threads media container."""


class ThreadsPublisher:
    """Publish text-only posts through the Threads API."""

    provider_name = "threads"

    def __init__(
        self,
        *,
        access_token: str,
        threads_user_id: str,
        credential_ref: str | None = None,
        http_client: ThreadsHttpClient | None = None,
    ) -> None:
        self.credential_ref = credential_ref
        self._access_token = _normalize_required_string("access_token", access_token)
        self._threads_user_id = _normalize_required_string("threads_user_id", threads_user_id)
        self._http_client = http_client or _UrlLibThreadsHttpClient()

    def publish(self, request: PublishRequest) -> PublishResult:
        try:
            create_response = self._http_client.create_container(
                access_token=self._access_token,
                threads_user_id=self._threads_user_id,
                text=request.body,
            )
        except Exception as exc:
            return PublishResult(
                status="failed",
                error_message=f"Threads publish request failed during container creation: {exc}",
                provider=self.provider_name,
                credential_ref=self.credential_ref,
            )

        provider_payload: dict[str, Any] = {
            "create_container": _build_provider_step_payload(create_response),
        }
        if create_response.status_code < 200 or create_response.status_code >= 300:
            return PublishResult(
                status="failed",
                error_message=_extract_error_message(
                    create_response.payload,
                    default=(
                        f"Threads container creation failed with status {create_response.status_code}"
                    ),
                ),
                provider=self.provider_name,
                credential_ref=self.credential_ref,
                provider_payload=provider_payload,
            )

        container_id = _extract_id_from_response(create_response.payload)
        if container_id is None:
            return PublishResult(
                status="failed",
                error_message=_extract_missing_id_message(
                    create_response.payload,
                    missing_id_default="malformed Threads create-container response: missing id",
                    expected_object_default=(
                        "malformed Threads create-container response: expected a JSON object payload"
                    ),
                ),
                provider=self.provider_name,
                credential_ref=self.credential_ref,
                provider_payload=provider_payload,
            )

        provider_payload["container_id"] = container_id

        try:
            publish_response = self._http_client.publish_container(
                access_token=self._access_token,
                threads_user_id=self._threads_user_id,
                creation_id=container_id,
            )
        except Exception as exc:
            return PublishResult(
                status="failed",
                error_message=f"Threads publish request failed during container publish: {exc}",
                provider=self.provider_name,
                credential_ref=self.credential_ref,
                provider_payload=provider_payload,
            )

        provider_payload["publish_container"] = _build_provider_step_payload(publish_response)
        if publish_response.status_code < 200 or publish_response.status_code >= 300:
            return PublishResult(
                status="failed",
                error_message=_extract_error_message(
                    publish_response.payload,
                    default=f"Threads publish failed with status {publish_response.status_code}",
                ),
                provider=self.provider_name,
                credential_ref=self.credential_ref,
                provider_payload=provider_payload,
            )

        external_post_id = _extract_id_from_response(publish_response.payload)
        if external_post_id is None:
            return PublishResult(
                status="failed",
                error_message=_extract_missing_id_message(
                    publish_response.payload,
                    missing_id_default="malformed Threads publish response: missing id",
                    expected_object_default=(
                        "malformed Threads publish response: expected a JSON object payload"
                    ),
                ),
                provider=self.provider_name,
                credential_ref=self.credential_ref,
                provider_payload=provider_payload,
            )

        return PublishResult(
            status="published",
            external_post_id=external_post_id,
            provider=self.provider_name,
            credential_ref=self.credential_ref,
            provider_payload=provider_payload,
        )


class _UrlLibThreadsHttpClient:
    """Minimal urllib-based client for the Threads two-step text publish flow."""

    def __init__(self, *, timeout_seconds: float = 30.0) -> None:
        self._timeout_seconds = timeout_seconds

    def create_container(
        self,
        *,
        access_token: str,
        threads_user_id: str,
        text: str,
    ) -> ThreadsHttpResponse:
        return self._post_form(
            url=_threads_graph_url(threads_user_id, "threads"),
            form_fields={
                "media_type": "TEXT",
                "text": text,
                "access_token": access_token,
            },
        )

    def publish_container(
        self,
        *,
        access_token: str,
        threads_user_id: str,
        creation_id: str,
    ) -> ThreadsHttpResponse:
        return self._post_form(
            url=_threads_graph_url(threads_user_id, "threads_publish"),
            form_fields={
                "creation_id": creation_id,
                "access_token": access_token,
            },
        )

    def _post_form(self, *, url: str, form_fields: dict[str, str]) -> ThreadsHttpResponse:
        payload = urlencode(form_fields).encode("utf-8")
        http_request = request.Request(
            url,
            data=payload,
            method="POST",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "sns-content-engine/0.1.0",
            },
        )

        try:
            with request.urlopen(http_request, timeout=self._timeout_seconds) as response:
                return ThreadsHttpResponse(
                    status_code=response.getcode(),
                    payload=_load_json_payload(response.read()),
                )
        except error.HTTPError as exc:
            return ThreadsHttpResponse(
                status_code=exc.code,
                payload=_load_json_payload(exc.read()),
            )
        except error.URLError as exc:
            raise RuntimeError(f"network error: {exc.reason}") from exc


def _threads_graph_url(threads_user_id: str, endpoint: str) -> str:
    normalized_user_id = quote(threads_user_id, safe="")
    return f"{_GRAPH_API_BASE_URL}/{normalized_user_id}/{endpoint}"


def _normalize_required_string(field_name: str, value: object) -> str:
    if isinstance(value, str):
        normalized = value.strip()
    elif isinstance(value, int):
        normalized = str(value)
    else:
        normalized = ""
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized


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


def _build_provider_step_payload(response: ThreadsHttpResponse) -> dict[str, Any]:
    provider_step_payload: dict[str, Any] = {"http_status": response.status_code}
    normalized_response_payload = _normalize_provider_payload(response.payload)
    if normalized_response_payload is not None:
        provider_step_payload["response"] = normalized_response_payload
    return provider_step_payload


def _extract_id_from_response(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None

    identifier = payload.get("id")
    if isinstance(identifier, str) and identifier.strip():
        return identifier.strip()
    if isinstance(identifier, int):
        return str(identifier)
    if identifier is None:
        return None
    if isinstance(identifier, float) and identifier.is_integer():
        return str(int(identifier))
    return None


def _extract_missing_id_message(
    payload: Any,
    *,
    missing_id_default: str,
    expected_object_default: str,
) -> str:
    if not isinstance(payload, dict):
        return expected_object_default
    if "raw_body" in payload:
        raw_body = payload.get("raw_body")
        if isinstance(raw_body, str) and raw_body.strip():
            return f"{expected_object_default}: {raw_body.strip()}"
    return missing_id_default


def _extract_error_message(payload: Any, *, default: str) -> str:
    if isinstance(payload, dict):
        error_payload = payload.get("error")
        if isinstance(error_payload, dict):
            error_user_message = error_payload.get("error_user_msg")
            if isinstance(error_user_message, str) and error_user_message.strip():
                return error_user_message.strip()

            message = error_payload.get("message")
            if isinstance(message, str) and message.strip():
                return message.strip()

            error_user_title = error_payload.get("error_user_title")
            if isinstance(error_user_title, str) and error_user_title.strip():
                return error_user_title.strip()

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
