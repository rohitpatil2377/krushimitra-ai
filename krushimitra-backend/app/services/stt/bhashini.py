from app.core.config import settings
from app.services.stt.base import Transcript

# Real Marathi/Hindi/English speech-to-text via Bhashini (AI4Bharat).
# TODO (voice pass): call the Bhashini ASR pipeline with settings.bhashini_api_key,
# detect language, return the recognized text. Until then the factory uses MockSTT.


class BhashiniSTT:
    async def transcribe(self, audio: bytes, lang_hint: str | None = None) -> Transcript:
        if not settings.bhashini_api_key:
            raise RuntimeError("BHASHINI_API_KEY not set")
        raise NotImplementedError("Bhashini STT not implemented yet — wire in the voice pass.")
