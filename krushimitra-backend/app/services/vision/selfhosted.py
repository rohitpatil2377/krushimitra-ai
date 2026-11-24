"""Disease detection + severity against a SELF-HOSTED OpenAI-compatible vision model.

Built for a self-hosted Gemma 3 (4B / 12B / 27B — the multimodal sizes; Gemma 3 *1B is
text-only* and cannot do this), but it assumes nothing beyond the OpenAI
`/chat/completions` shape, so Qwen2.5-VL, InternVL or a future Gemma 4 served by
vLLM / SGLang / Ollama / TGI all work through the same adapter.

Why self-hosting is the right default here:
  * zero marginal cost per diagnosis and no rate limit, so a free farmer app stays free;
  * the farmer photographs — the only durable moat (docs/DATASET.md) — never leave our
    infrastructure, unlike a hosted free tier whose terms allow training on the inputs.

Three design choices carry the "never give a fake answer" promise:
  1. The model picks from a CLOSED label menu (app/services/vision/labels.py) that includes
     `unknown` and `not_a_plant`. It is never asked an open "what disease is this?".
  2. It must report the visible symptoms it based the call on, and its true confidence. The
     endpoint abstains below `settings.vision_min_confidence`.
  3. All model reasoning happens in ENGLISH (the pivot language). Farmer-facing Marathi comes
     from our own knowledge base and templates, so output quality never depends on the open
     model's uneven Marathi.
"""
from __future__ import annotations

import base64
import json
import logging
import re

import httpx

from app.core.config import settings
from app.services.knowledge import action_for, band_for, lookup
from app.services.vision.base import Diagnosis, Severity
from app.services.vision.labels import ALL_LABELS, prompt_menu, resolve

log = logging.getLogger(__name__)


class VisionModelError(RuntimeError):
    """The model was unreachable or unusable. Callers fall back to the mock, labelled honestly."""


# --------------------------------------------------------------------------- helpers
def _mime(image: bytes) -> str:
    if image.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if image.startswith(b"\x89PNG"):
        return "image/png"
    if image[:4] == b"RIFF" and image[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


def _data_uri(image: bytes) -> str:
    return f"data:{_mime(image)};base64,{base64.b64encode(image).decode('ascii')}"


_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.S)


def _parse_json(raw: str) -> dict:
    """Extract the JSON object from a model reply. VLMs wrap it in prose or markdown fences."""
    text = (raw or "").strip()
    if not text:
        raise VisionModelError("model returned an empty reply")

    fenced = _FENCE.search(text)
    if fenced:
        text = fenced.group(1).strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise VisionModelError(f"no JSON object in model reply: {raw[:200]!r}") from None
        try:
            parsed = json.loads(text[start : end + 1])
        except json.JSONDecodeError as exc:
            raise VisionModelError(f"unparseable JSON from model: {raw[:200]!r}") from exc

    if not isinstance(parsed, dict):
        raise VisionModelError(f"expected a JSON object, got {type(parsed).__name__}")
    return parsed


def _confidence(value: object) -> float:
    """Clamp to 0-1. Models routinely answer 85 when asked for 0.85 — treat >1 as a percentage."""
    try:
        conf = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0
    if conf > 1.0:
        conf = conf / 100.0
    return max(0.0, min(1.0, round(conf, 3)))


def _pct(value: object) -> float | None:
    try:
        pct = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if 0.0 < pct <= 1.0:
        pct *= 100.0  # answered as a fraction
    return max(0.0, min(100.0, round(pct, 1)))


async def _chat(messages: list[dict], max_tokens: int) -> str:
    """One call to the OpenAI-compatible endpoint. Retries once without JSON mode if rejected."""
    if not settings.vision_base_url:
        raise VisionModelError("VISION_BASE_URL is not set")

    url = f"{settings.vision_base_url.rstrip('/')}/chat/completions"
    headers = {"Content-Type": "application/json"}
    if settings.vision_api_key:
        headers["Authorization"] = f"Bearer {settings.vision_api_key}"

    payload: dict = {
        "model": settings.vision_model,
        "messages": messages,
        # Near-greedy: a diagnosis should be reproducible for the same photo, not creative.
        "temperature": 0.1,
        "max_tokens": max_tokens,
    }
    if settings.vision_json_mode:
        payload["response_format"] = {"type": "json_object"}

    async with httpx.AsyncClient(
        timeout=settings.vision_timeout_s, verify=settings.vision_verify_ssl
    ) as client:
        try:
            res = await client.post(url, json=payload, headers=headers)
            # Ollama and older TGI builds reject response_format outright — retry plainly.
            if res.status_code == 400 and "response_format" in payload:
                log.warning("[vision] server rejected JSON mode; retrying without it")
                payload.pop("response_format")
                res = await client.post(url, json=payload, headers=headers)
            res.raise_for_status()
        except httpx.HTTPStatusError as exc:
            body = exc.response.text[:300]
            raise VisionModelError(f"model HTTP {exc.response.status_code}: {body}") from exc
        except httpx.HTTPError as exc:
            raise VisionModelError(f"model unreachable at {url}: {exc}") from exc

    try:
        data = res.json()
        return data["choices"][0]["message"]["content"] or ""
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise VisionModelError(f"unexpected response shape: {res.text[:300]!r}") from exc


# --------------------------------------------------------------------------- detection
_DETECT_RULES = """\
Rules you must follow:
1. Base the answer ONLY on what is visible in this photograph. Do not infer a disease from the \
crop name or from what is statistically common.
2. Answer "unknown" if the photo is blurry, dark, too distant or partial, or if the symptoms \
match none of the options. A farmer acting on a wrong diagnosis buys the wrong chemical and \
loses the crop, so admitting uncertainty is strictly better than guessing.
3. Answer "not_a_plant" if no crop plant is visible.
4. Answer "healthy" only if you can see no symptoms at all.
5. "confidence" is your genuine probability that "label" is correct, between 0 and 1. Do not \
inflate it. If two options look equally likely, confidence must be at most 0.5.
6. "visible_symptoms" must describe what you actually see (colour, shape, position, pattern) \
in under 30 English words. Do not name the disease again here.

Reply with ONLY this JSON object and nothing else:
{"label": "<one slug from the list>", "confidence": <0-1>, \
"visible_symptoms": "<what you see>", "alternative": "<second-most-likely slug or null>"}"""


def _detect_prompt(crop: str | None) -> str:
    crop_line = (
        f"The farmer says the crop is: {crop}."
        if crop
        else "The farmer did not say which crop this is — identify it from the photo."
    )
    return (
        "You are a plant-pathology assistant helping smallholder farmers in Maharashtra, India.\n"
        f"{crop_line}\n\n"
        "Choose the ONE option below that best matches what is visible in the photograph.\n\n"
        f"Options:\n{prompt_menu(crop)}\n\n"
        f"{_DETECT_RULES}"
    )


class SelfHostedDetector:
    """Disease detection via a self-hosted multimodal model, constrained to our label taxonomy."""

    async def diagnose(self, image: bytes, crop: str | None = None) -> Diagnosis:
        if not image:
            raise VisionModelError("empty image")

        reply = await _chat(
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": _detect_prompt(crop)},
                        {"type": "image_url", "image_url": {"url": _data_uri(image)}},
                    ],
                }
            ],
            max_tokens=400,
        )
        parsed = _parse_json(reply)

        label = resolve(str(parsed.get("label") or ""), crop)
        confidence = _confidence(parsed.get("confidence"))
        symptoms = str(parsed.get("visible_symptoms") or "").strip() or None
        alt_raw = parsed.get("alternative")
        alternative = resolve(str(alt_raw), crop).slug if alt_raw and alt_raw != "null" else None
        if alternative in (label.slug, "unknown"):
            alternative = None

        # A model that picks a real disease but reports no symptoms has almost certainly guessed
        # from the crop name. Cap confidence so the abstain threshold catches it.
        if label.kind not in ("none",) and not symptoms:
            confidence = min(confidence, 0.4)

        return Diagnosis(
            crop=crop or "unknown",
            disease=label.slug,
            confidence=confidence,
            model_version=f"self_hosted:{settings.vision_model}",
            symptoms=symptoms,
            alternative=alternative,
        )


# --------------------------------------------------------------------------- severity
_SEVERITY_PROMPT = """\
You are assessing how far a crop problem has progressed, for a farmer in Maharashtra, India.

The identified problem is: {disease_en} ({kind}).

Estimate what PERCENTAGE of the visible plant tissue in this photograph shows symptoms \
(lesions, pustules, discolouration, wilting or chewing damage). Judge only the plant area \
visible in the frame.

Guidance: a few small spots on one leaf is roughly 1-5%. Spots scattered over most leaves but \
with green tissue dominant is roughly 10-25%. Half the tissue damaged, browning or dropping is \
roughly 50%. Nearly all tissue dead or defoliated is over 75%.

Also say whether the problem looks early or advanced, and whether it appears to be spreading \
(multiple ages of lesion, or spread beyond one leaf).

Reply with ONLY this JSON object and nothing else:
{{"affected_area_pct": <0-100>, "stage": "early|progressing|advanced", \
"spreading": true|false, "evidence": "<under 25 English words on what you measured>"}}"""


class SelfHostedSeverity:
    """Severity from the same model. v2 will be lesion-area segmentation — the real moat."""

    async def estimate(self, image: bytes, diagnosis: Diagnosis) -> Severity:
        info = lookup(diagnosis.disease)

        # Nothing to measure when the detector found nothing or declined to name a disease.
        # Spending a second model call here would only invent a number.
        if diagnosis.disease in ("healthy", "unknown", "not_a_plant"):
            return Severity(
                level="healthy",
                severity_pct=0.0,
                risk_level="low",
                recommended_action=action_for("healthy", info.curable),
                method="skipped",
                model_version=f"self_hosted:{settings.vision_model}",
            )

        label = ALL_LABELS.get(diagnosis.disease)
        reply = await _chat(
            [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": _SEVERITY_PROMPT.format(
                                disease_en=label.en if label else diagnosis.disease,
                                kind=label.kind if label else "problem",
                            ),
                        },
                        {"type": "image_url", "image_url": {"url": _data_uri(image)}},
                    ],
                }
            ],
            max_tokens=300,
        )
        parsed = _parse_json(reply)

        pct = _pct(parsed.get("affected_area_pct"))
        if pct is None:
            raise VisionModelError("model gave no usable affected_area_pct")

        level, risk = band_for(pct)
        # A spreading problem is more urgent than its current area suggests — bump the risk only,
        # never the measured percentage, so the number stays an honest observation.
        if parsed.get("spreading") is True and risk in ("low", "medium"):
            risk = "medium" if risk == "low" else "high"

        return Severity(
            level=level,
            severity_pct=pct,
            risk_level=risk,
            recommended_action=action_for(level, info.curable),
            method="vlm",
            model_version=f"self_hosted:{settings.vision_model}",
            evidence=str(parsed.get("evidence") or "").strip() or None,
        )
