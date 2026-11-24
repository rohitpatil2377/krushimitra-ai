"""Disease detection endpoints — the product's wedge.

The composition here is deliberate and is where the honesty rules are enforced:

    detector -> severity -> ABSTAIN GATE -> knowledge lookup BY DISEASE -> capture

Two defects this replaces:
  1. Advice was looked up by CROP, so any onion photo got the purple-blotch treatment even when
     the model said Stemphylium blight. It is now keyed by the detected disease slug.
  2. Nothing ever abstained. A low-confidence guess was presented to the farmer with the same
     authority as a confident one. Below `VISION_MIN_CONFIDENCE` the endpoint now returns
     `identified=false` with no treatment and no severity, plus how to retake the photo.
"""
import base64
import logging

from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.schemas.api import (
    DiagnoseFeedbackIn,
    DiagnoseRequest,
    FeedbackAck,
    RichDiagnosisOut,
    SeverityOut,
)
from app.services import capture
from app.services.knowledge import DOSE_NOTE, lookup
from app.services.vision import MockDetector, MockSeverity, get_detector, get_severity
from app.services.vision.base import Diagnosis, Severity
from app.services.vision.labels import ALL_LABELS, NOT_A_PLANT, UNKNOWN, resolve

log = logging.getLogger(__name__)
router = APIRouter(prefix="/vision", tags=["vision"])

MAX_IMAGE_BYTES = 12 * 1024 * 1024  # a phone photo at quality 0.5 is ~0.3-2 MB


@router.post("/diagnose", response_model=RichDiagnosisOut)
async def diagnose(body: DiagnoseRequest) -> RichDiagnosisOut:
    """Analyse a crop photo: disease + severity + Marathi advice, or an honest "not sure"."""
    try:
        img = base64.b64decode(body.image_base64, validate=True)
    except Exception:
        raise HTTPException(status_code=422, detail="image_base64 is not valid base64") from None
    if not img:
        raise HTTPException(status_code=422, detail="image is empty")
    if len(img) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="image too large — send a compressed photo")

    crop = body.crop or None

    # --- Analyse, degrading to the mock rather than failing in the farmer's hand ---
    diag: Diagnosis
    sev: Severity
    try:
        diag = await get_detector().diagnose(img, crop=crop)
        sev = await get_severity().estimate(img, diag)
    except Exception as exc:
        # Graceful degradation (the repo convention) — but labelled, so the app badges it as
        # sample data instead of passing a placeholder off as a real analysis.
        log.warning("[vision] %s failed, serving mock: %s", settings.active_vision_provider, exc)
        diag = await MockDetector().diagnose(img, crop=crop)
        sev = await MockSeverity().estimate(img, diag)
        diag.model_version = sev.model_version = "mock-fallback"

    # --- Abstain gate: the "never give a fake answer" rule, enforced in one place ---
    predicted = ALL_LABELS.get(diag.disease, UNKNOWN)
    not_a_plant = predicted.slug == NOT_A_PLANT.slug
    too_unsure = not not_a_plant and diag.confidence < settings.vision_min_confidence

    if not_a_plant:
        shown, hint = NOT_A_PLANT, None
    elif too_unsure:
        # Keep what it leaned toward, but as a hint only — never as advice.
        shown, hint = UNKNOWN, predicted.slug if predicted.slug != UNKNOWN.slug else None
    else:
        shown, hint = predicted, diag.alternative

    identified = shown.slug not in (UNKNOWN.slug, NOT_A_PLANT.slug)
    info = lookup(shown.slug)

    # --- Capture for the dataset moat, before shaping the response ---
    # The field context (who/where/when) rides along: it is what makes a saved photo a training
    # example rather than just a picture, and it is the one part that cannot be backfilled later.
    diagnosis_id = capture.save_diagnosis(
        img,
        {
            "crop_selected": crop,
            **capture.normalize_context(body.context.model_dump() if body.context else None),
            "model_version": diag.model_version,
            "provider": settings.active_vision_provider,
            "predicted_slug": predicted.slug,
            "predicted_confidence": diag.confidence,
            "shown_slug": shown.slug,
            "identified": identified,
            "abstain_reason": (
                "not_a_plant" if not_a_plant else "low_confidence" if too_unsure else None
            ),
            "symptoms": diag.symptoms,
            "alternative": diag.alternative,
            "severity_pct": sev.severity_pct if identified else None,
            "severity_level": sev.level if identified else None,
            "severity_evidence": sev.evidence if identified else None,
        },
    )

    note = info.note
    if too_unsure and hint:
        hinted = ALL_LABELS.get(hint)
        if hinted:
            note = (
                f"कदाचित {hinted.mr} असू शकेल, पण खात्री पुरेशी नाही "
                f"({int(diag.confidence * 100)}%) — म्हणून उपचार सांगितलेले नाहीत."
            )

    return RichDiagnosisOut(
        crop=diag.crop,
        disease=shown.mr,
        disease_en=shown.en,
        disease_slug=shown.slug,
        kind=shown.kind,
        confidence=diag.confidence,
        identified=identified,
        # No severity bar on an answer we are not confident about — it would imply a measurement.
        severity=(
            SeverityOut(
                level=sev.level,
                severity_pct=sev.severity_pct,
                risk_level=sev.risk_level,
                recommended_action=sev.recommended_action,
                method=sev.method,
                evidence=sev.evidence,
            )
            if identified
            else None
        ),
        cause=info.cause,
        treatment=list(info.treatment),
        prevention=list(info.prevention),
        chemicals=list(info.chemicals) if identified else [],
        # Named a chemical => the KVK dosage disclaimer is mandatory, never optional.
        dose_note=DOSE_NOTE if (identified and info.chemicals) else None,
        curable=info.curable,
        note=note,
        symptoms=diag.symptoms,
        model_version=diag.model_version,
        diagnosis_id=diagnosis_id,
    )


@router.post("/feedback", response_model=FeedbackAck)
async def feedback(body: DiagnoseFeedbackIn) -> FeedbackAck:
    """Record whether a diagnosis was right. Every correction is a labelled field training example."""
    correct_slug: str | None = None
    if body.correct_disease:
        resolved = resolve(body.correct_disease)
        correct_slug = resolved.slug if resolved.slug != UNKNOWN.slug else None

    ok = capture.save_feedback(
        body.diagnosis_id,
        was_correct=body.was_correct,
        correct_disease=correct_slug,
        note=body.note,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="unknown diagnosis_id")
    return FeedbackAck(recorded=True, message="धन्यवाद! तुमच्या प्रतिसादाने निदान सुधारेल.")


@router.get("/dataset", response_model=dict, tags=["meta"])
async def dataset() -> dict:
    """How much labelled field data we have accumulated — the moat, as a number."""
    return {"provider": settings.active_vision_provider, **capture.stats()}
