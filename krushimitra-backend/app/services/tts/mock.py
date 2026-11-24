class MockTTS:
    """No server-side audio yet; the app reads answers aloud with on-device TTS (Expo Speech)."""

    async def synthesize(self, text: str, lang: str = "mr") -> bytes | None:
        return None
