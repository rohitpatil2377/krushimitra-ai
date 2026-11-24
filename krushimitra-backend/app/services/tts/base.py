from typing import Protocol


class TTSService(Protocol):
    """Text-to-speech. Real impl = Bhashini/AI4Bharat Indic-TTS; returns audio bytes.

    The mock returns None (the app falls back to on-device Expo Speech for read-aloud).
    """

    async def synthesize(self, text: str, lang: str = "mr") -> bytes | None: ...
