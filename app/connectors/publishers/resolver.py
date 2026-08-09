"""Config-backed publisher resolution for scheduled publish jobs."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path

from app.config import AccountConfig, load_accounts_config
from app.connectors.publishers.base import Publisher, PublishRequest, PublishResult
from app.connectors.publishers.threads import ThreadsHttpClient, ThreadsPublisher
from app.connectors.publishers.x import XHttpClient, XPublisher


class ConfigPublisherResolver:
    """Resolve live publishers from account/channel config and environment variables."""

    def __init__(
        self,
        *,
        config_dir: Path | str = Path("config"),
        environment: Mapping[str, str] | None = None,
        x_http_client: XHttpClient | None = None,
        threads_http_client: ThreadsHttpClient | None = None,
    ) -> None:
        accounts_file = Path(config_dir) / "accounts.yaml"
        self._accounts: Mapping[str, AccountConfig] = load_accounts_config(accounts_file).accounts
        self._environment = environment if environment is not None else os.environ
        self._x_http_client = x_http_client
        self._threads_http_client = threads_http_client
        self._cache: dict[tuple[str, str], Publisher] = {}

    def has_live_publisher(self, *, account_key: str, channel: str) -> bool:
        """Return whether the account/channel resolves to a live publisher."""

        publisher = self._resolve_account_channel_publisher(account_key=account_key, channel=channel)
        return not isinstance(publisher, _FailurePublisher)

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

        return self._resolve_account_channel_publisher(account_key=account_key, channel=channel)

    def _resolve_account_channel_publisher(
        self,
        *,
        account_key: str,
        channel: str,
    ) -> Publisher:
        cache_key = (account_key, channel)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        provider_name = _provider_name_for_channel(channel)
        if channel not in {"x", "threads"}:
            return _FailurePublisher(
                provider_name=provider_name,
                error_message=f"channel {channel!r} does not support live publishing in the MVP",
            )

        account = self._accounts.get(account_key)
        if account is None:
            return _FailurePublisher(
                provider_name=provider_name,
                error_message=f"account {account_key!r} is not defined in config",
            )

        channel_config = account.channels.get(channel)
        if channel_config is None:
            return _FailurePublisher(
                provider_name=provider_name,
                error_message=f"account {account_key!r} does not define channel {channel!r}",
            )

        publisher_config = channel_config.publisher
        if publisher_config is None:
            return _FailurePublisher(
                provider_name=provider_name,
                error_message=f"account {account_key!r} channel {channel!r} is missing publisher configuration",
            )

        credential_ref = publisher_config.credential_ref
        bundle = _load_credential_bundle(
            environment=self._environment,
            credential_ref=credential_ref,
            provider_name=provider_name,
        )
        if isinstance(bundle, _FailurePublisher):
            return bundle

        try:
            publisher = self._build_publisher(
                channel=channel,
                credential_ref=credential_ref,
                bundle=bundle,
            )
        except ValueError as exc:
            return _FailurePublisher(
                provider_name=provider_name,
                credential_ref=credential_ref,
                error_message=str(exc),
            )

        self._cache[cache_key] = publisher
        return publisher

    def _build_publisher(
        self,
        *,
        channel: str,
        credential_ref: str,
        bundle: Mapping[str, object],
    ) -> Publisher:
        if channel == "x":
            access_token = _require_bundle_string(
                bundle,
                credential_ref=credential_ref,
                field_name="access_token",
            )
            consumer_key = _optional_string(bundle.get("consumer_key"))
            consumer_secret = _optional_string(bundle.get("consumer_secret"))
            access_token_secret = _optional_string(bundle.get("access_token_secret"))
            return XPublisher(
                access_token=access_token,
                consumer_key=consumer_key,
                consumer_secret=consumer_secret,
                access_token_secret=access_token_secret,
                credential_ref=credential_ref,
                http_client=self._x_http_client,
            )

        if channel == "threads":
            access_token = _require_bundle_string(
                bundle,
                credential_ref=credential_ref,
                field_name="access_token",
            )
            threads_user_id = _require_bundle_identifier(
                bundle,
                credential_ref=credential_ref,
                field_name="threads_user_id",
            )
            return ThreadsPublisher(
                access_token=access_token,
                threads_user_id=threads_user_id,
                credential_ref=credential_ref,
                http_client=self._threads_http_client,
            )

        raise ValueError(f"channel {channel!r} does not support live publishing in the MVP")


_ALWAYS_MANUAL_PUBLISH_CHANNELS = frozenset({"ghost", "linkedin"})
_CONFIG_GATED_LIVE_PUBLISH_CHANNELS = frozenset({"threads"})


def channel_requires_manual_publish_handoff(
    *,
    config_dir: Path | str,
    account_key: str,
    channel: str,
    environment: Mapping[str, str] | None = None,
) -> bool:
    """Return whether the current account/channel must stay on manual publish handoff."""

    normalized_channel = channel.strip()
    if normalized_channel in _ALWAYS_MANUAL_PUBLISH_CHANNELS:
        return True
    if normalized_channel not in _CONFIG_GATED_LIVE_PUBLISH_CHANNELS:
        return False

    resolver = ConfigPublisherResolver(
        config_dir=config_dir,
        environment=environment,
    )
    return not resolver.has_live_publisher(
        account_key=account_key,
        channel=normalized_channel,
    )


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


def _load_credential_bundle(
    *,
    environment: Mapping[str, str],
    credential_ref: str,
    provider_name: str,
) -> Mapping[str, object] | _FailurePublisher:
    raw_bundle = environment.get(credential_ref)
    if raw_bundle is None or not raw_bundle.strip():
        return _FailurePublisher(
            provider_name=provider_name,
            credential_ref=credential_ref,
            error_message=f"publisher credential env var {credential_ref!r} is not set",
        )

    try:
        bundle = json.loads(raw_bundle)
    except json.JSONDecodeError:
        return _FailurePublisher(
            provider_name=provider_name,
            credential_ref=credential_ref,
            error_message=(
                f"publisher credential env var {credential_ref!r} does not contain valid JSON"
            ),
        )

    if not isinstance(bundle, dict):
        return _FailurePublisher(
            provider_name=provider_name,
            credential_ref=credential_ref,
            error_message=(
                f"publisher credential env var {credential_ref!r} must decode to a JSON object"
            ),
        )
    return bundle


def _require_bundle_string(
    bundle: Mapping[str, object],
    *,
    credential_ref: str,
    field_name: str,
) -> str:
    value = bundle.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"publisher credential env var {credential_ref!r} is missing {field_name}")
    return value.strip()


def _require_bundle_identifier(
    bundle: Mapping[str, object],
    *,
    credential_ref: str,
    field_name: str,
) -> str:
    value = bundle.get(field_name)
    if isinstance(value, str):
        normalized = value.strip()
        if normalized:
            return normalized
    elif isinstance(value, int):
        return str(value)
    raise ValueError(f"publisher credential env var {credential_ref!r} is missing {field_name}")


def _optional_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None
