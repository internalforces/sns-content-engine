"""Google Cloud TTS provider."""

from __future__ import annotations

import os
from collections.abc import Mapping

from app.connectors.tts.base import TTSInput, TTSOutput, TTSProviderError

DEFAULT_GOOGLE_TTS_LANGUAGE = "en-US"
DEFAULT_GOOGLE_TTS_VOICE_NAME = "en-US-Standard-C"
DEFAULT_GOOGLE_TTS_AUDIO_FORMAT = "MP3"


class GoogleTTSProvider:
    """Synthesize speech through Google Cloud Text-to-Speech API.

    Requires the 'google-cloud-texttospeech' SDK and either:
    - GOOGLE_APPLICATION_CREDENTIALS env var pointing to a service account JSON, or
    - Application Default Credentials (ADC) configured via 'gcloud auth application-default login'.
    """

    def __init__(
        self,
        *,
        language_code: str = DEFAULT_GOOGLE_TTS_LANGUAGE,
        voice_name: str = DEFAULT_GOOGLE_TTS_VOICE_NAME,
        audio_format: str = DEFAULT_GOOGLE_TTS_AUDIO_FORMAT,
    ) -> None:
        self._language_code = language_code.strip() or DEFAULT_GOOGLE_TTS_LANGUAGE
        self._voice_name = voice_name.strip() or DEFAULT_GOOGLE_TTS_VOICE_NAME
        self._audio_format = audio_format.strip().upper() or DEFAULT_GOOGLE_TTS_AUDIO_FORMAT

    @classmethod
    def from_environment(
        cls,
        *,
        environment: Mapping[str, str] | None = None,
    ) -> "GoogleTTSProvider":
        """Build a provider from environment variables."""

        resolved_environment = os.environ if environment is None else environment
        language_code = _resolve_optional_env_var(
            resolved_environment,
            "GOOGLE_TTS_LANGUAGE_CODE",
            default=DEFAULT_GOOGLE_TTS_LANGUAGE,
        )
        voice_name = _resolve_optional_env_var(
            resolved_environment,
            "GOOGLE_TTS_VOICE_NAME",
            default=DEFAULT_GOOGLE_TTS_VOICE_NAME,
        )
        audio_format = _resolve_optional_env_var(
            resolved_environment,
            "GOOGLE_TTS_AUDIO_FORMAT",
            default=DEFAULT_GOOGLE_TTS_AUDIO_FORMAT,
        )
        return cls(
            language_code=language_code,
            voice_name=voice_name,
            audio_format=audio_format,
        )

    def synthesize(self, input: TTSInput) -> TTSOutput:
        if not input.text or not input.text.strip():
            raise TTSProviderError("text must not be empty")

        try:
            from google.cloud import texttospeech  # type: ignore[import]
        except ImportError as exc:
            raise TTSProviderError(
                "google-cloud-texttospeech is not installed. "
                "Install it with: pip install google-cloud-texttospeech"
            ) from exc

        try:
            client = texttospeech.TextToSpeechClient()
            synthesis_input = texttospeech.SynthesisInput(text=input.text)
            voice = texttospeech.VoiceSelectionParams(
                language_code=input.language_code or self._language_code,
                name=self._voice_name,
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=getattr(
                    texttospeech.AudioEncoding,
                    self._audio_format,
                    texttospeech.AudioEncoding.MP3,
                ),
                speaking_rate=input.speed if input.speed != 1.0 else None,
            )
            response = client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config,
            )
        except TTSProviderError:
            raise
        except Exception as exc:
            raise TTSProviderError(f"Google TTS request failed: {exc}") from exc

        if not response.audio_content:
            raise TTSProviderError("Google TTS returned empty audio")

        fmt = "mp3" if self._audio_format == "MP3" else self._audio_format.lower()
        return TTSOutput(
            audio_bytes=response.audio_content,
            format=fmt,
            provider="google",
            model=self._voice_name,
        )


def _resolve_optional_env_var(
    environment: Mapping[str, str], name: str, *, default: str
) -> str:
    if name not in environment:
        return default
    value = environment[name].strip()
    if not value:
        raise TTSProviderError(f"{name} is set but empty")
    return value
