"""Deterministic fake TTS provider used by tests and local workflows."""

from __future__ import annotations

from app.connectors.tts.base import TTSInput, TTSOutput


class FakeTTSProvider:
    """Return silent placeholder audio bytes without external API calls."""

    _SILENT_MP3_HEADER = bytes(
        [
            0xFF, 0xFB, 0x90, 0x00,  # MPEG frame header (silent frame)
            0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00,
        ]
    )

    def synthesize(self, input: TTSInput) -> TTSOutput:
        if not input.text or not input.text.strip():
            from app.connectors.tts.base import TTSProviderError
            raise TTSProviderError("text must not be empty")

        # Return a minimal valid MP3 whose length encodes the text length
        # so tests can assert deterministic behaviour.
        padding = len(input.text.encode("utf-8")) % 256
        audio_bytes = self._SILENT_MP3_HEADER + bytes([padding])

        return TTSOutput(
            audio_bytes=audio_bytes,
            format="mp3",
            provider="fake",
            model=None,
        )
