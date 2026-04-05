"""ElevenLabs-backed TTS provider."""

from __future__ import annotations

import os
import urllib.error
import urllib.request
from collections.abc import Mapping
from typing import Protocol

from app.connectors.tts.base import TTSInput, TTSOutput, TTSProviderError

DEFAULT_ELEVENLABS_MODEL = "eleven_multilingual_v2"
DEFAULT_ELEVENLABS_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Rachel (ElevenLabs default)
DEFAULT_ELEVENLABS_TIMEOUT_SECONDS = 60.0
_ELEVENLABS_API_BASE = "https://api.elevenlabs.io/v1"


class ElevenLabsHttpClient(Protocol):
    """HTTP boundary for ElevenLabs TTS API calls."""

    def synthesize(
        self,
        *,
        api_key: str,
        voice_id: str,
        model_id: str,
        text: str,
    ) -> bytes:
        """Return MP3 audio bytes for the given text."""


class ElevenLabsTTSProvider:
    """Synthesize speech through the ElevenLabs API."""

    def __init__(
        self,
        *,
        api_key: str,
        voice_id: str = DEFAULT_ELEVENLABS_VOICE_ID,
        model_id: str = DEFAULT_ELEVENLABS_MODEL,
        client: ElevenLabsHttpClient | None = None,
    ) -> None:
        if not api_key.strip():
            raise TTSProviderError("ELEVENLABS_API_KEY must not be empty")

        self._api_key = api_key.strip()
        self._voice_id = voice_id.strip() or DEFAULT_ELEVENLABS_VOICE_ID
        self._model_id = model_id.strip() or DEFAULT_ELEVENLABS_MODEL
        self._client = client or _UrllibElevenLabsClient()

    @classmethod
    def from_environment(
        cls,
        *,
        environment: Mapping[str, str] | None = None,
        client: ElevenLabsHttpClient | None = None,
    ) -> "ElevenLabsTTSProvider":
        """Build a provider from environment variables."""

        resolved_environment = os.environ if environment is None else environment
        api_key = _resolve_required_env_var(resolved_environment, "ELEVENLABS_API_KEY")
        voice_id = _resolve_optional_env_var(
            resolved_environment,
            "ELEVENLABS_VOICE_ID",
            default=DEFAULT_ELEVENLABS_VOICE_ID,
        )
        model_id = _resolve_optional_env_var(
            resolved_environment,
            "ELEVENLABS_MODEL",
            default=DEFAULT_ELEVENLABS_MODEL,
        )
        return cls(api_key=api_key, voice_id=voice_id, model_id=model_id, client=client)

    def synthesize(self, input: TTSInput) -> TTSOutput:
        if not input.text or not input.text.strip():
            raise TTSProviderError("text must not be empty")

        try:
            audio_bytes = self._client.synthesize(
                api_key=self._api_key,
                voice_id=self._voice_id,
                model_id=self._model_id,
                text=input.text,
            )
        except TTSProviderError:
            raise
        except Exception as exc:
            raise TTSProviderError(f"ElevenLabs TTS request failed: {exc}") from exc

        if not audio_bytes:
            raise TTSProviderError("ElevenLabs TTS returned empty audio")

        return TTSOutput(
            audio_bytes=audio_bytes,
            format="mp3",
            provider="elevenlabs",
            model=self._model_id,
        )


class _UrllibElevenLabsClient:
    """stdlib urllib implementation of ElevenLabsHttpClient."""

    def synthesize(
        self,
        *,
        api_key: str,
        voice_id: str,
        model_id: str,
        text: str,
    ) -> bytes:
        import json

        url = f"{_ELEVENLABS_API_BASE}/text-to-speech/{voice_id}"
        payload = json.dumps(
            {
                "text": text,
                "model_id": model_id,
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
            }
        ).encode("utf-8")

        request = urllib.request.Request(
            url,
            data=payload,
            headers={
                "xi-api-key": api_key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=DEFAULT_ELEVENLABS_TIMEOUT_SECONDS) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise TTSProviderError(
                f"ElevenLabs API returned HTTP {exc.code}: {body}"
            ) from exc
        except urllib.error.URLError as exc:
            raise TTSProviderError(f"ElevenLabs API connection failed: {exc.reason}") from exc


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
