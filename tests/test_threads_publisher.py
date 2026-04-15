"""Tests for the Threads publisher adapter and resolver."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from app.connectors.publishers import (
    ConfigPublisherResolver,
    PublishRequest,
    ThreadsHttpResponse,
    ThreadsPublisher,
)


class StubThreadsHttpClient:
    """Simple stub client for Threads publisher tests."""

    def __init__(
        self,
        *,
        create_response: ThreadsHttpResponse | None = None,
        publish_response: ThreadsHttpResponse | None = None,
        create_exception: Exception | None = None,
        publish_exception: Exception | None = None,
    ) -> None:
        self._create_response = create_response
        self._publish_response = publish_response
        self._create_exception = create_exception
        self._publish_exception = publish_exception
        self.calls: list[tuple[str, str, str, str]] = []

    def create_container(
        self,
        *,
        access_token: str,
        threads_user_id: str,
        text: str,
    ) -> ThreadsHttpResponse:
        self.calls.append(("create", access_token, threads_user_id, text))
        if self._create_exception is not None:
            raise self._create_exception
        assert self._create_response is not None
        return self._create_response

    def publish_container(
        self,
        *,
        access_token: str,
        threads_user_id: str,
        creation_id: str,
    ) -> ThreadsHttpResponse:
        self.calls.append(("publish", access_token, threads_user_id, creation_id))
        if self._publish_exception is not None:
            raise self._publish_exception
        assert self._publish_response is not None
        return self._publish_response


def test_threads_publisher_normalizes_successful_two_step_publish() -> None:
    client = StubThreadsHttpClient(
        create_response=ThreadsHttpResponse(
            status_code=200,
            payload={"id": "container-123"},
        ),
        publish_response=ThreadsHttpResponse(
            status_code=200,
            payload={"id": "thread-456"},
        ),
    )
    publisher = ThreadsPublisher(
        access_token="threads-user-token",
        threads_user_id="threads-user-1",
        credential_ref="THREADS_TEST_CREDENTIALS",
        http_client=client,
    )

    result = publisher.publish(_sample_publish_request())

    assert result.status == "published"
    assert result.external_post_id == "thread-456"
    assert result.provider == "threads"
    assert result.credential_ref == "THREADS_TEST_CREDENTIALS"
    assert result.provider_payload == {
        "create_container": {
            "http_status": 200,
            "response": {"id": "container-123"},
        },
        "container_id": "container-123",
        "publish_container": {
            "http_status": 200,
            "response": {"id": "thread-456"},
        },
    }
    assert client.calls == [
        (
            "create",
            "threads-user-token",
            "threads-user-1",
            "Useful AI workflows https://gilgop.cloud/ai-tools",
        ),
        (
            "publish",
            "threads-user-token",
            "threads-user-1",
            "container-123",
        ),
    ]


def test_threads_publisher_normalizes_non_2xx_container_creation_failure() -> None:
    publisher = ThreadsPublisher(
        access_token="threads-user-token",
        threads_user_id="threads-user-1",
        credential_ref="THREADS_TEST_CREDENTIALS",
        http_client=StubThreadsHttpClient(
            create_response=ThreadsHttpResponse(
                status_code=401,
                payload={"error": {"message": "Invalid OAuth access token."}},
            ),
        ),
    )

    result = publisher.publish(_sample_publish_request())

    assert result.status == "failed"
    assert result.error_message == "Invalid OAuth access token."
    assert result.provider == "threads"
    assert result.provider_payload == {
        "create_container": {
            "http_status": 401,
            "response": {"error": {"message": "Invalid OAuth access token."}},
        }
    }


def test_threads_publisher_rejects_malformed_container_creation_response() -> None:
    publisher = ThreadsPublisher(
        access_token="threads-user-token",
        threads_user_id="threads-user-1",
        credential_ref="THREADS_TEST_CREDENTIALS",
        http_client=StubThreadsHttpClient(
            create_response=ThreadsHttpResponse(
                status_code=200,
                payload={"status": "ok"},
            ),
        ),
    )

    result = publisher.publish(_sample_publish_request())

    assert result.status == "failed"
    assert result.error_message == "malformed Threads create-container response: missing id"


def test_threads_publisher_normalizes_non_2xx_publish_failure() -> None:
    publisher = ThreadsPublisher(
        access_token="threads-user-token",
        threads_user_id="threads-user-1",
        credential_ref="THREADS_TEST_CREDENTIALS",
        http_client=StubThreadsHttpClient(
            create_response=ThreadsHttpResponse(
                status_code=200,
                payload={"id": "container-123"},
            ),
            publish_response=ThreadsHttpResponse(
                status_code=400,
                payload={"error": {"message": "Media not ready"}},
            ),
        ),
    )

    result = publisher.publish(_sample_publish_request())

    assert result.status == "failed"
    assert result.error_message == "Media not ready"
    assert result.provider_payload == {
        "create_container": {
            "http_status": 200,
            "response": {"id": "container-123"},
        },
        "container_id": "container-123",
        "publish_container": {
            "http_status": 400,
            "response": {"error": {"message": "Media not ready"}},
        },
    }


def test_threads_publisher_rejects_malformed_publish_response() -> None:
    publisher = ThreadsPublisher(
        access_token="threads-user-token",
        threads_user_id="threads-user-1",
        credential_ref="THREADS_TEST_CREDENTIALS",
        http_client=StubThreadsHttpClient(
            create_response=ThreadsHttpResponse(
                status_code=200,
                payload={"id": "container-123"},
            ),
            publish_response=ThreadsHttpResponse(
                status_code=200,
                payload={"status": "ok"},
            ),
        ),
    )

    result = publisher.publish(_sample_publish_request())

    assert result.status == "failed"
    assert result.error_message == "malformed Threads publish response: missing id"


def test_threads_publisher_reports_publish_request_exceptions() -> None:
    publisher = ThreadsPublisher(
        access_token="threads-user-token",
        threads_user_id="threads-user-1",
        credential_ref="THREADS_TEST_CREDENTIALS",
        http_client=StubThreadsHttpClient(
            create_response=ThreadsHttpResponse(
                status_code=200,
                payload={"id": "container-123"},
            ),
            publish_exception=RuntimeError("network error: timed out"),
        ),
    )

    result = publisher.publish(_sample_publish_request())

    assert result.status == "failed"
    assert (
        result.error_message
        == "Threads publish request failed during container publish: network error: timed out"
    )
    assert result.provider_payload == {
        "create_container": {
            "http_status": 200,
            "response": {"id": "container-123"},
        },
        "container_id": "container-123",
    }


def test_threads_publisher_rejects_empty_required_credentials() -> None:
    with pytest.raises(ValueError, match="access_token must not be empty"):
        ThreadsPublisher(
            access_token="  ",
            threads_user_id="threads-user-1",
        )

    with pytest.raises(ValueError, match="threads_user_id must not be empty"):
        ThreadsPublisher(
            access_token="threads-user-token",
            threads_user_id="  ",
        )


def test_config_publisher_resolver_builds_threads_publisher_from_env_json(tmp_path: Path) -> None:
    config_dir = _write_threads_accounts_only_config(tmp_path)
    client = StubThreadsHttpClient(
        create_response=ThreadsHttpResponse(
            status_code=200,
            payload={"id": "container-456"},
        ),
        publish_response=ThreadsHttpResponse(
            status_code=200,
            payload={"id": "thread-789"},
        ),
    )
    resolver = ConfigPublisherResolver(
        config_dir=config_dir,
        environment={
            "THREADS_TEST_CREDENTIALS": (
                '{"access_token":"threads-user-token","threads_user_id":"threads-user-1","ignored":"extra"}'
            ),
        },
        threads_http_client=client,
    )

    publisher = resolver.resolve(_sample_threads_publish_job())
    cached_publisher = resolver.resolve(_sample_threads_publish_job())
    result = publisher.publish(_sample_publish_request())

    assert publisher is cached_publisher
    assert result.status == "published"
    assert result.external_post_id == "thread-789"
    assert result.provider == "threads"
    assert result.credential_ref == "THREADS_TEST_CREDENTIALS"
    assert client.calls == [
        (
            "create",
            "threads-user-token",
            "threads-user-1",
            "Useful AI workflows https://gilgop.cloud/ai-tools",
        ),
        (
            "publish",
            "threads-user-token",
            "threads-user-1",
            "container-456",
        ),
    ]


def test_config_publisher_resolver_reports_missing_threads_env_var(tmp_path: Path) -> None:
    config_dir = _write_threads_accounts_only_config(tmp_path)
    resolver = ConfigPublisherResolver(config_dir=config_dir, environment={})

    publisher = resolver.resolve(_sample_threads_publish_job())
    result = publisher.publish(_sample_publish_request())

    assert result.status == "failed"
    assert result.error_message == "publisher credential env var 'THREADS_TEST_CREDENTIALS' is not set"
    assert result.provider == "threads"
    assert result.credential_ref == "THREADS_TEST_CREDENTIALS"


def test_config_publisher_resolver_reports_invalid_threads_json_credentials(
    tmp_path: Path,
) -> None:
    config_dir = _write_threads_accounts_only_config(tmp_path)
    resolver = ConfigPublisherResolver(
        config_dir=config_dir,
        environment={"THREADS_TEST_CREDENTIALS": "not-json"},
    )

    publisher = resolver.resolve(_sample_threads_publish_job())
    result = publisher.publish(_sample_publish_request())

    assert result.status == "failed"
    assert (
        result.error_message
        == "publisher credential env var 'THREADS_TEST_CREDENTIALS' does not contain valid JSON"
    )
    assert result.provider == "threads"


def test_config_publisher_resolver_reports_missing_threads_access_token(tmp_path: Path) -> None:
    config_dir = _write_threads_accounts_only_config(tmp_path)
    resolver = ConfigPublisherResolver(
        config_dir=config_dir,
        environment={"THREADS_TEST_CREDENTIALS": '{"threads_user_id":"threads-user-1"}'},
    )

    publisher = resolver.resolve(_sample_threads_publish_job())
    result = publisher.publish(_sample_publish_request())

    assert result.status == "failed"
    assert (
        result.error_message
        == "publisher credential env var 'THREADS_TEST_CREDENTIALS' is missing access_token"
    )
    assert result.provider == "threads"
    assert result.credential_ref == "THREADS_TEST_CREDENTIALS"


def test_config_publisher_resolver_reports_missing_threads_user_id(tmp_path: Path) -> None:
    config_dir = _write_threads_accounts_only_config(tmp_path)
    resolver = ConfigPublisherResolver(
        config_dir=config_dir,
        environment={"THREADS_TEST_CREDENTIALS": '{"access_token":"threads-user-token"}'},
    )

    publisher = resolver.resolve(_sample_threads_publish_job())
    result = publisher.publish(_sample_publish_request())

    assert result.status == "failed"
    assert (
        result.error_message
        == "publisher credential env var 'THREADS_TEST_CREDENTIALS' is missing threads_user_id"
    )
    assert result.provider == "threads"
    assert result.credential_ref == "THREADS_TEST_CREDENTIALS"


def _sample_publish_request() -> PublishRequest:
    return PublishRequest(
        publish_job_id=42,
        draft_variant_id=101,
        account_key="ai_tools_daily",
        channel="threads",
        body="Useful AI workflows https://gilgop.cloud/ai-tools",
        idempotency_key="job-42-threads",
    )


def _sample_threads_publish_job():
    brief = type("Brief", (), {"account_key": "ai_tools_daily"})()
    draft = type("Draft", (), {"content_brief": brief})()
    return type("PublishJobStub", (), {"channel": "threads", "draft_variant": draft})()


def _write_threads_accounts_only_config(tmp_path: Path) -> Path:
    _write_file(
        tmp_path / "accounts.yaml",
        """
        accounts:
          ai_tools_daily:
            topic: "AI tools and workflows"
            source_sets:
              - any_source_set_name
            prompt_profile: any_prompt_name
            landing:
              fallback_url: https://gilgop.cloud/ai-tools
              rules: []
            channels:
              threads:
                schedule:
                  cron: "0 9 * * *"
                render:
                  max_chars: 500
                publisher:
                  credential_ref: THREADS_TEST_CREDENTIALS
        """,
    )
    return tmp_path


def _write_file(path: Path, content: str) -> None:
    path.write_text(dedent(content).strip() + "\n", encoding="utf-8")
