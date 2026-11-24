from app.core.config import settings
from app.services.vision.base import Diagnosis, Severity

# Vision-LLM implementations (Claude vision) for the first *live* version, before trained models.
#
# TODO (vision pass):
#   - LLMDetector: send the image to Claude with a structured prompt -> {crop, disease, confidence}.
#   - LLMSeverity: send the image + diagnosis with a severity rubric -> ordinal level + %.
#   - Later replace both with fine-tuned PyTorch models (EfficientNet/YOLOv8-cls) and a
#     segmentation model for severity. See docs/AI_ARCHITECTURE.md.


class LLMDetector:
    async def diagnose(self, image: bytes, crop: str | None = None) -> Diagnosis:
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        raise NotImplementedError("Claude-vision detection not implemented yet — wire in the vision pass.")


class LLMSeverity:
    async def estimate(self, image: bytes, diagnosis: Diagnosis) -> Severity:
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        raise NotImplementedError("Claude-vision severity not implemented yet — wire in the vision pass.")
