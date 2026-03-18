"""Config-backed publisher resolution for scheduled publish jobs."""

from __future__ import annotations

from collections.abc import Mapping
import json
import os
from pathlib import Path

from app.config import AccountConfig, load_accounts_config
from app.connectors.publishers.base import PublishRequest, PublishResult, Publisher
from app.connectors.publishers.x import XHttpClient, XPublisher


class ConfigPublisherResolver:
    """Resolve live publishers from account/channel config and environment variables."""

    def __init__(
        self,
        *,
        config_dir: Path | str = Path("config"),
        environment: Mapping[str, str] | None = None,
        x_http_client: XHttpClient | None = None,
    ) -> None:
        accounts_file = Path(config_dir) / "accounts.yaml"
        self._accounts: Mapping[str, AccountConfig] = load_accounts_config(accounts_file).accounts
        self._environment = environment if environment is not None else os.environ
        self._x_http_client = x_http_client
        self._cache: dict[tuple[str, str], XPublisher] = {}

    def resolve(self, publish_job) -> Publisher:
        draft = getattr(publish_job, "draft_variant", None)
        brief = getattr(draft, "content_brief", None)
        account_key = getattr(brief, "account_key", None)
        channel = getattr(publish_job, "channel", None)

        if not isinstance(account_key, str) or not account_key.strip():
            return _FailurePublisher(
                provider_name=_provider_name_for_channel(channel),
                error_message="publish job is missing an account_key through its content brief",
            )

        if not isinstance(channel, str) or not channel.strip():
            return _FailurePublisher(
                provider_name="unknown",
                error_message="publish job is missing its channel",
            )

        cache_key = (account_key, channel)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        if channel != "x":
            return _FailurePublisher(
                provider_name=_provider_name_for_channel(channel),
                error_message=f"channel {channel!r} does not support live publishing in the MVP",
            )

        account = self._accounts.get(account_key)
        if account is None:
            return _FailurePublisher(
                provider_name="x",
                error_message=f"account {account_key!r} is not defined in config",
            )

        channel_config = account.channels.get(channel)
        if channel_config is None:
            return _FailurePublisher(
                provider_name="x",
                error_message=f"account {account_key!r} does not define channel {channel!r}",
            )

        publisher_config = channel_config.publisher
        if publisher_config is None:
            return _FailurePublisher(
                provider_name="x",
                error_message=f"account {account_key!r} channel {channel!r} is missing publisher configuration",
            )

        credential_ref = publisher_config.credential_ref
        raw_bundle = self._environment.get(credential_ref)
        if raw_bundle is None or not raw_bundle.strip():
            return _FailurePublisher(
                provider_name="x",
                credential_ref=credential_ref,
                error_message=f"publisher credential env var {credential_ref!r} is not set",
            )

        try:
            bundle = json.loads(raw_bundle)
        except json.JSONDecodeError:
            return _FailurePublisher(
                provider_name="x",
                credential_ref=credential_ref,
                error_message=(
                    f"publisher credential env var {credential_ref!r} does not contain valid JSON"
                ),
            )

        if not isinstance(bundle, dict):
            return _FailurePublisher(
                provider_name="x",
                credential_ref=credential_ref,
                error_message=(
                    f"publisher credential env var {credential_ref!r} must decode to a JSON object"
                ),
            )

        access_token = bundle.get("access_token")
        if not isinstance(access_token, str) or not access_token.strip():
            return _FailurePublisher(
                provider_name="x",
                credential_ref=credential_ref,
                error_message=(
                    f"publisher credential env var {credential_ref!r} is missing access_token"
                ),
            )

        publisher = XPublisher(
            access_token=access_token.strip(),
            credential_ref=credential_ref,
            http_client=self._x_http_client,
        )
        self._cache[cache_key] = publisher
        return publisher


class _FailurePublisher:
    """Publisher that converts resolver issues into normalized failed results."""

    def __init__(
        self,
        *,
        provider_name: str,
        error_message: str,
        credential_ref: str | None = None,
    ) -> None:
        self.provider_name = provider_name
        self.credential_ref = credential_ref
        self._error_message = error_message

    def publish(self, request: PublishRequest) -> PublishResult:
        return PublishResult(
            status="failed",
            error_message=self._error_message,
            provider=self.provider_name,
            credential_ref=self.credential_ref,
        )


def _provider_name_for_channel(channel: object) -> str:
    if isinstance(channel, str) and channel.strip():
        return channel.strip()
    return "unknown"
