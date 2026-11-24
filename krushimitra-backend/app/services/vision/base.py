"""Vision service contracts. Every implementation (mock, self-hosted VLM, future PyTorch model)
returns these same two shapes, so the API layer never knows which one answered.

`model_version` is load-bearing, not decorative: it is how the app knows whether the farmer is
looking at a real analysis or sample data. Anything starting with "mock" is sample data and the
UI must badge it as such.
"""
from dataclasses import dataclass
from typing import Protocol


@dataclass
class Diagnosis:
    crop: str
    disease: str          # canonical slug from app/services/vision/labels.py
    confidence: float     # 0-1, the model's genuine probability — drives abstain
    model_version: str = "mock-0"
    symptoms: str | None = None      # what the model says it saw (English) — grounding + audit
    alternative: str | None = None   # second-most-likely slug, for the UI and later eval


@dataclass
class Severity:
    level: str  # healthy|mild|moderate|severe|critical
    severity_pct: float
    risk_level: str  # low|medium|high|critical
    recommended_action: str
    method: str = "vlm"  # vlm|segmentation|mock|skipped
    model_version: str = "mock-0"
    evidence: str | None = None  # what the model measured (English)


class DiseaseDetector(Protocol):
    """Detect crop disease from an image. mock -> self-hosted VLM -> fine-tuned model."""

    async def diagnose(self, image: bytes, crop: str | None = None) -> Diagnosis: ...


class SeverityEstimator(Protocol):
    """Estimate severity. v1 = vision-model rubric; v2 = lesion-area segmentation (the moat)."""

    async def estimate(self, image: bytes, diagnosis: Diagnosis) -> Severity: ...
