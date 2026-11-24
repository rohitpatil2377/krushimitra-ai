"""TTS factory. Mock returns no audio (app uses on-device read-aloud)."""
from app.services.tts.base import TTSService
from app.services.tts.mock import MockTTS

__all__ = ["TTSService", "get_tts"]


def get_tts() -> TTSService:
    # TODO: return a Bhashini Indic-TTS implementation when voice_live.
    return MockTTS()
