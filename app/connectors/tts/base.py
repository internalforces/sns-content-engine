"""Interfaces for TTS providers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


class TTSProviderError(RuntimeError):
    """Raised when a TTS provider cannot fulfill a synthesis request."""


@dataclass(frozen=True, slots=True)
class TTSInput:
    """Normalized input payload for TTS synthesis."""

    text: str
    voice_id: str | None = None
    language_code: str = "en"
    speed: float = 1.0


@dataclass(frozen=True, slots=True)
class TTSOutput:
    """Normalized output from a TTS synthesis request."""

    audio_bytes: bytes
    format: str          # "mp3", "wav", "ogg", etc.
    provider: str        # which provider produced this output
    model: str | None = None


class TTSProvider(Protocol):
    """Provider boundary for turning text into audio."""

    def synthesize(self, input: TTSInput) -> TTSOutput:
        """Return synthesized audio for the given text input."""
