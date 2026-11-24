"""The voice-first copilot — the one endpoint the app's mic button hits.

Orchestrates: STT (if audio) -> vision (if image) -> copilot LLM -> TTS.
Open (no auth) during early dev so it's easy to test; add `get_current_farmer` before launch.
"""
from fastapi import APIRouter, File, Form, UploadFile

from app.schemas.api import CopilotResponse, DiagnosisOut, SeverityOut
from app.services.llm import CopilotContext, get_copilot
from app.services.stt import get_stt
from app.services.tts import get_tts
from app.services.vision import get_detector, get_severity
from app.services.vision.labels import ALL_LABELS

router = APIRouter(prefix="/copilot", tags=["copilot"])


@router.post("/ask", response_model=CopilotResponse)
async def ask(
    text: str | None = Form(None),
    lang: str = Form("mr"),
    crop: str | None = Form(None),
    crop_cycle_id: int | None = Form(None),
    audio: UploadFile | None = File(None),
    image: UploadFile | None = File(None),
) -> CopilotResponse:
    transcript: str | None = None

    # 1. Voice in -> text
    if audio is not None:
        stt = get_stt()
        result = await stt.transcribe(await audio.read(), lang_hint=lang)
        transcript = result.text
        lang = result.lang
        text = text or transcript

    # 2. Image -> diagnosis + severity
    context = CopilotContext(crop=crop)
    diagnosis_out: DiagnosisOut | None = None
    severity_out: SeverityOut | None = None
    if image is not None:
        img_bytes = await image.read()
        diag = await get_detector().diagnose(img_bytes, crop=crop)
        sev = await get_severity().estimate(img_bytes, diag)
        diagnosis_out = DiagnosisOut(**diag.__dict__)
        severity_out = SeverityOut(**{k: v for k, v in sev.__dict__.items() if k != "model_version"})
        context.crop = diag.crop
        # diag.disease is a canonical slug; the copilot reasons in English, so hand it the
        # English disease name rather than "pomegranate_bacterial_blight".
        label = ALL_LABELS.get(diag.disease)
        context.disease = label.en if label else diag.disease
        context.severity_level = sev.level
        context.severity_pct = sev.severity_pct

    # 3. Generate the answer
    reply_text = await get_copilot().answer(text or "", context, lang=lang)

    # 4. Optional voice out (mock returns None -> app reads aloud on-device)
    await get_tts().synthesize(reply_text, lang=lang)

    return CopilotResponse(
        transcript=transcript,
        reply_text=reply_text,
        reply_audio_url=None,
        lang=lang,
        diagnosis=diagnosis_out,
        severity=severity_out,
    )
