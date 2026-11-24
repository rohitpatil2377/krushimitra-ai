"""Vision factories: detection + severity.

This is the single swap point for the whole product's image analysis. Resolution order:

    VISION_BASE_URL set            -> self-hosted multimodal model (Gemma 3 4B+/Qwen-VL/...)
    ANTHROPIC_API_KEY + !USE_MOCKS -> Claude vision
    otherwise                      -> mock (sample data, badged as such in the app)

Later a fine-tuned EfficientNet/YOLOv8-cls checkpoint plus a lesion-segmentation model slot in
here too, behind the same two Protocols. See docs/AI_ARCHITECTURE.md.
"""
from app.core.config import settings
from app.services.vision.base import (
    Diagnosis,
    DiseaseDetector,
    Severity,
    SeverityEstimator,
)
from app.services.vision.mock import MockDetector, MockSeverity

__all__ = [
    "Diagnosis",
    "DiseaseDetector",
    "Severity",
    "SeverityEstimator",
    "get_detector",
    "get_severity",
    "MockDetector",
    "MockSeverity",
]


def get_detector() -> DiseaseDetector:
    if settings.self_hosted_vision_live:
        from app.services.vision.selfhosted import SelfHostedDetector

        return SelfHostedDetector()
    if settings.claude_vision_live:
        from app.services.vision.llm import LLMDetector

        return LLMDetector()
    return MockDetector()


def get_severity() -> SeverityEstimator:
    if settings.self_hosted_vision_live:
        from app.services.vision.selfhosted import SelfHostedSeverity

        return SelfHostedSeverity()
    if settings.claude_vision_live:
        from app.services.vision.llm import LLMSeverity

        return LLMSeverity()
    return MockSeverity()
