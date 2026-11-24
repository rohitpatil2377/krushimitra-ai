"""Mock vision services — SAMPLE DATA, not analysis.

This exists so the backend and app run end-to-end with zero keys (the repo's mock-first
convention). It is important to be blunt about what it is: **the image is never looked at.**
The disease is a fixed per-crop demo value, so two different photos of the same crop return the
same answer.

Its honesty contract is `model_version="mock-0"`. The API copies that through to the app, which
shows the "नमुना माहिती" (sample data) badge whenever it starts with "mock". Earlier the badge
tracked whether the backend was *reachable*, which meant a running backend serving mock data
appeared to the farmer as a real diagnosis. That was the bug; this is the fix.
"""
from app.services.knowledge import action_for, band_for, lookup
from app.services.vision.base import Diagnosis, Severity

MOCK_VERSION = "mock-0"

# Crop -> a representative disease slug, purely for the demo.
_DISEASE_BY_CROP: dict[str, tuple[str, float]] = {
    "onion": ("onion_purple_blotch", 0.78),
    "soybean": ("soybean_rust", 0.74),
    "pomegranate": ("pomegranate_bacterial_blight", 0.83),
}
_FALLBACK = ("unknown", 0.3)


class MockDetector:
    async def diagnose(self, image: bytes, crop: str | None = None) -> Diagnosis:
        disease, conf = _DISEASE_BY_CROP.get(crop or "", _FALLBACK)
        return Diagnosis(
            crop=crop or "unknown",
            disease=disease,
            confidence=conf,
            model_version=MOCK_VERSION,
            symptoms="(sample data — this photo was not analysed)",
        )


class MockSeverity:
    async def estimate(self, image: bytes, diagnosis: Diagnosis) -> Severity:
        info = lookup(diagnosis.disease)
        if diagnosis.disease in ("healthy", "unknown", "not_a_plant"):
            pct = 0.0
        else:
            # Deterministic placeholder so the field is populated end-to-end. Not a measurement.
            pct = round(min(0.95, diagnosis.confidence) * 30, 1)
        level, risk = band_for(pct)
        return Severity(
            level=level,
            severity_pct=pct,
            risk_level=risk,
            recommended_action=action_for(level, info.curable),
            method="mock",
            model_version=MOCK_VERSION,
        )
