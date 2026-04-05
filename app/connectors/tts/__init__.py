"""TTS provider exports."""

from app.connectors.tts.base import (
    TTSInput,
    TTSOutput,
    TTSProvider,
    TTSProviderError,
)
from app.connectors.tts.fake import FakeTTSProvider
from app.connectors.tts.openai_provider import OpenAITTSProvider
from app.connectors.tts.resolver import resolve_tts_provider

__all__ = [
    "FakeTTSProvider",
    "OpenAITTSProvider",
    "TTSInput",
    "TTSOutput",
    "TTSProvider",
    "TTSProviderError",
    "resolve_tts_provider",
]
