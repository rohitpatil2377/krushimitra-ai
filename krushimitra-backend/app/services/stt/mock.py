from app.services.stt.base import STTService, Transcript

_SAMPLES = [
    ("माझ्या कांद्याच्या पानांवर पिवळे डाग आले आहेत.", "mr"),
    ("मेरी सोयाबीन की बढ़वार कम हो गई है.", "hi"),
    ("Leaves are falling from my pomegranate tree.", "en"),
]


class MockSTT:
    """Returns a rotating sample question so the copilot flow works without audio/Bhashini."""

    def __init__(self) -> None:
        self._i = 0

    async def transcribe(self, audio: bytes, lang_hint: str | None = None) -> Transcript:
        text, lang = _SAMPLES[self._i % len(_SAMPLES)]
        self._i += 1
        return Transcript(text=text, lang=lang_hint or lang)


def _check() -> STTService:
    return MockSTT()
