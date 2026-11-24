from dataclasses import dataclass
from typing import Protocol


@dataclass
class Transcript:
    text: str
    lang: str  # detected/used language: mr|hi|en


class STTService(Protocol):
    """Speech-to-text. Real impl = Bhashini/IndicWhisper; mock = canned text."""

    async def transcribe(self, audio: bytes, lang_hint: str | None = None) -> Transcript: ...
