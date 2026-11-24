"""STT factory: real Bhashini when configured, else mock."""
from app.core.config import settings
from app.services.stt.base import STTService, Transcript
from app.services.stt.mock import MockSTT

__all__ = ["STTService", "Transcript", "get_stt"]


def get_stt() -> STTService:
    if settings.voice_live:
        from app.services.stt.bhashini import BhashiniSTT

        return BhashiniSTT()
    return MockSTT()
