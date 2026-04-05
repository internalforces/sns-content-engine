"""OpenAI-backed TTS provider (tts-1 / tts-1-hd)."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Protocol

from app.connectors.tts.base import TTSInput, TTSOutput, TTSProviderError

DEFAULT_OPENAI_TTS_MODEL = "tts-1"
DEFAULT_OPENAI_TTS_VOICE = "alloy"
DEFAULT_OPENAI_TTS_FORMAT = "mp3"
DEFAULT_OPENAI_TTS_TIMEOUT_SECONDS = 60.0

_ALLOWED_VOICES = frozenset({"alloy", "echo", "fable", "onyx", "nova", "shimmer"})
_ALLOWED_FORMATS = frozenset({"mp3", "opus", "aac", "flac"})


class OpenAIAudioClient(Protocol):
    """HTTP/API boundary for OpenAI Audio API calls."""

    def create_speech(
        self,
        *,
        model: str,
        voice: str,
        input: str,
        response_format: str,
    ) -> bytes:
        """Return raw audio bytes for the given text."""


class OpenAITTSProvider:
    """Synthesize speech through the OpenAI Audio API."""

    def __init__(
        self,
        *,
        client: OpenAIAudioClient,
        model: str = DEFAULT_OPENAI_TTS_MODEL,
        voice: str = DEFAULT_OPENAI_TTS_VOICE,
        response_format: str = DEFAULT_OPENAI_TTS_FORMAT,
    ) -> None:
        normalized_model = model.strip()
        if not normalized_model:
            raise TTSProviderError("OPENAI_TTS_MODEL must not be empty")

        normalized_voice = voice.strip().casefold()
        if normalized_voice not in _ALLOWED_VOICES:
            allowed = ", ".join(sorted(_ALLOWED_VOICES))
            raise TTSProviderError(f"OPENAI_TTS_VOICE must be one of: {allowed}")

        normalized_format = response_format.strip().casefold()
        if normalized_format not in _ALLOWED_FORMATS:
            allowed = ", ".join(sorted(_ALLOWED_FORMATS))
            raise TTSProviderError(f"OPENAI_TTS_FORMAT must be one of: {allowed}")

        self._client = client
        self._model = normalized_model
        self._voice = normalized_voice
        self._response_format = normalized_format

    @classmethod
    def from_environment(
        cls,
        *,
        environment: Mapping[str, str] | None = None,
        client_factory=None,
    ) -> "OpenAITTSProvider":
        """Build a provider from environment variables."""

        resolved_environment = os.environ if environment is None else environment
        api_key = _resolve_required_env_var(resolved_environment, "OPENAI_API_KEY")
        model = _resolve_optional_env_var(
            resolved_environment, "OPENAI_TTS_MODEL", default=DEFAULT_OPENAI_TTS_MODEL
        )
        voice = _resolve_optional_env_var(
            resolved_environment, "OPENAI_TTS_VOICE", default=DEFAULT_OPENAI_TTS_VOICE
        )
        response_format = _resolve_optional_env_var(
            resolved_environment, "OPENAI_TTS_FORMAT", default=DEFAULT_OPENAI_TTS_FORMAT
        )
        timeout_seconds = _resolve_timeout_seconds(resolved_environment)
        resolved_factory = client_factory or _build_default_openai_audio_client
        client = resolved_factory(api_key=api_key, timeout_seconds=timeout_seconds)
        return cls(
            client=client,
            model=model,
            voice=voice,
            response_format=response_format,
        )

    def synthesize(self, input: TTSInput) -> TTSOutput:
        if not input.text or not input.text.strip():
            raise TTSProviderError("text must not be empty")

        try:
            audio_bytes = self._client.create_speech(
                model=self._model,
                voice=self._voice,
                input=input.text,
                response_format=self._response_format,
            )
        except Exception as exc:
            raise TTSProviderError(f"OpenAI TTS request failed: {exc}") from exc

        if not audio_bytes:
            raise TTSProviderError("OpenAI TTS returned empty audio")

        return TTSOutput(
            audio_bytes=audio_bytes,
            format=self._response_format,
            provider="openai",
            model=self._model,
        )


class _SDKOpenAIAudioClient:
    """Minimal adapter around the official OpenAI SDK."""

    def __init__(self, sdk_client: object) -> None:
        self._sdk_client = sdk_client

    def create_speech(
        self,
        *,
        model: str,
        voice: str,
        input: str,
        response_format: str,
    ) -> bytes:
        response = self._sdk_client.audio.speech.create(
            model=model,
            voice=voice,
            input=input,
            response_format=response_format,
        )
        return response.content


def _build_default_openai_audio_client(
    *,
    api_key: str,
    timeout_seconds: float,
) -> OpenAIAudioClient:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise TTSProviderError(
            "The OpenAI Python SDK is not installed. Reinstall project dependencies to enable OpenAI TTS."
        ) from exc

    return _SDKOpenAIAudioClient(OpenAI(api_key=api_key, timeout=timeout_seconds))


def _resolve_required_env_var(environment: Mapping[str, str], name: str) -> str:
    if name not in environment:
        raise TTSProviderError(f"{name} is required")
    value = environment[name].strip()
    if not value:
        raise TTSProviderError(f"{name} is set but empty")
    return value


def _resolve_optional_env_var(
    environment: Mapping[str, str], name: str, *, default: str
) -> str:
    if name not in environment:
        return default
    value = environment[name].strip()
    if not value:
        raise TTSProviderError(f"{name} is set but empty")
    return value


def _resolve_timeout_seconds(environment: Mapping[str, str]) -> float:
    raw = environment.get("OPENAI_TTS_TIMEOUT_SECONDS")
    if raw is None:
        return DEFAULT_OPENAI_TTS_TIMEOUT_SECONDS
    normalized = raw.strip()
    if not normalized:
        raise TTSProviderError("OPENAI_TTS_TIMEOUT_SECONDS is set but empty")
    try:
        value = float(normalized)
    except ValueError as exc:
        raise TTSProviderError("OPENAI_TTS_TIMEOUT_SECONDS must be a positive number") from exc
    if value <= 0:
        raise TTSProviderError("OPENAI_TTS_TIMEOUT_SECONDS must be a positive number")
    return value
