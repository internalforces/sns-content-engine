"""Tests for the X publisher adapter and config-backed resolver."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from app.connectors.publishers import ConfigPublisherResolver, PublishRequest, XHttpResponse, XPublisher


class StubXHttpClient:
    """Simple stub client for X publisher tests."""

    def __init__(self, response: XHttpResponse) -> None:
        self._response = response
        self.calls: list[tuple[str, str]] = []

    def create_post(self, *, access_token: str, text: str) -> XHttpResponse:
        self.calls.append((access_token, text))
        return self._response


def test_x_publisher_normalizes_successful_response() -> None:
    client = StubXHttpClient(
        XHttpResponse(
            status_code=201,
            payload={"data": {"id": "tweet-123", "text": "Published text"}},
        )
    )
    publisher = XPublisher(
        access_token="secret-token",
        credential_ref="X_TEST_CREDENTIALS",
        http_client=client,
    )

    result = publisher.publish(_sample_publish_request())

    assert result.status == "published"
    assert result.external_post_id == "tweet-123"
    assert result.provider == "x"
    assert result.credential_ref == "X_TEST_CREDENTIALS"
    assert result.dry_run is False
    assert client.calls == [("secret-token", "Useful AI workflows https://gilgop.cloud/ai-tools")]


def test_x_publisher_normalizes_non_2xx_response() -> None:
    publisher = XPublisher(
        access_token="secret-token",
        credential_ref="X_TEST_CREDENTIALS",
        http_client=StubXHttpClient(
            XHttpResponse(
                status_code=401,
                payload={"errors": [{"detail": "Unauthorized"}]},
            )
        ),
    )

    result = publisher.publish(_sample_publish_request())

    assert result.status == "failed"
    assert result.error_message == "Unauthorized"
    assert result.provider == "x"
    assert result.provider_payload == {
        "http_status": 401,
        "response": {"errors": [{"detail": "Unauthorized"}]},
    }


def test_x_publisher_rejects_malformed_success_payload() -> None:
    publisher = XPublisher(
        access_token="secret-token",
        credential_ref="X_TEST_CREDENTIALS",
        http_client=StubXHttpClient(
            XHttpResponse(
                status_code=201,
                payload={"data": {"text": "Missing id"}},
            )
        ),
    )

    result = publisher.publish(_sample_publish_request())

    assert result.status == "failed"
    assert result.error_message == "malformed X publish response: missing data.id"


def test_config_publisher_resolver_builds_x_publisher_from_env_json(tmp_path: Path) -> None:
    config_dir = _write_project_config(tmp_path)
    resolver = ConfigPublisherResolver(
        config_dir=config_dir,
        environment={
            "X_TEST_CREDENTIALS": '{"access_token":"user-token","ignored":"extra"}',
        },
        x_http_client=StubXHttpClient(
            XHttpResponse(
                status_code=201,
                payload={"data": {"id": "tweet-456"}},
            )
        ),
    )

    publisher = resolver.resolve(_sample_publish_job())
    result = publisher.publish(_sample_publish_request())

    assert result.status == "published"
    assert result.external_post_id == "tweet-456"
    assert result.provider == "x"
    assert result.credential_ref == "X_TEST_CREDENTIALS"


def test_config_publisher_resolver_reports_missing_env_var(tmp_path: Path) -> None:
    config_dir = _write_project_config(tmp_path)
    resolver = ConfigPublisherResolver(config_dir=config_dir, environment={})

    publisher = resolver.resolve(_sample_publish_job())
    result = publisher.publish(_sample_publish_request())

    assert result.status == "failed"
    assert result.error_message == "publisher credential env var 'X_TEST_CREDENTIALS' is not set"
    assert result.provider == "x"
    assert result.credential_ref == "X_TEST_CREDENTIALS"


def test_config_publisher_resolver_reports_invalid_json_credentials(tmp_path: Path) -> None:
    config_dir = _write_project_config(tmp_path)
    resolver = ConfigPublisherResolver(
        config_dir=config_dir,
        environment={"X_TEST_CREDENTIALS": "not-json"},
    )

    publisher = resolver.resolve(_sample_publish_job())
    result = publisher.publish(_sample_publish_request())

    assert result.status == "failed"
    assert (
        result.error_message
        == "publisher credential env var 'X_TEST_CREDENTIALS' does not contain valid JSON"
    )
    assert result.provider == "x"


def test_config_publisher_resolver_reports_missing_access_token(tmp_path: Path) -> None:
    config_dir = _write_project_config(tmp_path)
    resolver = ConfigPublisherResolver(
        config_dir=config_dir,
        environment={"X_TEST_CREDENTIALS": '{"refresh_token":"missing-access-token"}'},
    )

    publisher = resolver.resolve(_sample_publish_job())
    result = publisher.publish(_sample_publish_request())

    assert result.status == "failed"
    assert result.error_message == "publisher credential env var 'X_TEST_CREDENTIALS' is missing access_token"
    assert result.provider == "x"
    assert result.credential_ref == "X_TEST_CREDENTIALS"


def _sample_publish_request() -> PublishRequest:
    return PublishRequest(
        publish_job_id=42,
        draft_variant_id=101,
        account_key="ai_tools_daily",
        channel="x",
        body="Useful AI workflows https://gilgop.cloud/ai-tools",
        idempotency_key="job-42-x",
    )


def _sample_publish_job():
    brief = type("Brief", (), {"account_key": "ai_tools_daily"})()
    draft = type("Draft", (), {"content_brief": brief})()
    return type("PublishJobStub", (), {"channel": "x", "draft_variant": draft})()


def _write_project_config(tmp_path: Path) -> Path:
    _write_file(
        tmp_path / "accounts.yaml",
        """
        accounts:
          ai_tools_daily:
            topic: "AI tools and workflows"
            source_sets:
              - ai_tools_primary
            prompt_profile: ai_tools_default
            landing:
              fallback_url: https://gilgop.cloud/ai-tools
              rules: []
            channels:
              x:
                schedule:
                  cron: "0 9 * * *"
                render:
                  max_chars: 280
                publisher:
                  credential_ref: X_TEST_CREDENTIALS
        """,
    )
    _write_file(
        tmp_path / "prompts.yaml",
        """
        profiles:
          ai_tools_default:
            system_template: "System prompt"
            user_template: "User prompt"
        """,
    )
    _write_file(
        tmp_path / "sources.yaml",
        """
        sources:
          ai_tools_rss:
            type: rss
            url: https://example.com/feed.xml

        source_sets:
          ai_tools_primary:
            sources:
              - ai_tools_rss
        """,
    )
    return tmp_path


def _write_file(path: Path, content: str) -> None:
    path.write_text(dedent(content).strip() + "\n", encoding="utf-8")
