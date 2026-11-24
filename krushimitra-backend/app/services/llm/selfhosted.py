"""Copilot via a SELF-HOSTED OpenAI-compatible model (vLLM / SGLang / Ollama / TGI).

This is the text side. It is NOT the vision side: `app/services/vision/selfhosted.py` handles
photos and needs a multimodal model. A text-only model such as **Gemma 3 1B** can run this
copilot and cannot run that one, which is the distinction that decides what a given endpoint is
good for.

Quality warning, stated here because it shapes expectations rather than code: small models write
poor Marathi. The system prompt makes the model reason in English and answer in the farmer's
language, which helps, but a 1B model's Marathi will still read awkwardly next to the templated
Marathi in `knowledge.py`. Probe it with real questions before trusting it in front of a farmer —
and note that `model_version` flows to the app, so a weak answer is at least attributable.

The dosage policy is enforced in the prompt exactly as `knowledge.py` enforces it in data: name
the active ingredient, never a quantity, always point at the KVK. A chatbot that invents
"२ ग्रॅम प्रति लिटर" undoes the whole reason the vision module refuses to.
"""
from __future__ import annotations

import logging

import httpx

from app.core.config import settings
from app.services.llm.base import CopilotContext

log = logging.getLogger(__name__)

LANG_NAMES = {"mr": "Marathi", "hi": "Hindi", "en": "English"}

SYSTEM_TEMPLATE = (
    "You are KrushiMitra, an expert agronomist advising smallholder farmers in Maharashtra, "
    "India who grow onion (कांदा), soybean (सोयाबीन) and pomegranate (डाळिंब).\n"
    "\n"
    "Think in English. Write your ANSWER only in {language}, in short, simple sentences a "
    "farmer with little schooling can read aloud.\n"
    "\n"
    "HARD RULES — these are not style preferences:\n"
    "1. NEVER state a pesticide or fungicide quantity, dilution, or spray volume. Not grams, not "
    "ml, not 'per litre', not 'per acre'. Name the ACTIVE INGREDIENT and the cultural steps, then "
    "tell the farmer to get the exact dose from their Krishi Vigyan Kendra (KVK) or Krishi Seva "
    "Kendra. The correct dose depends on the formulation percentage printed on the bottle, which "
    "you cannot see. A wrong number poisons a crop or a person.\n"
    "2. NEVER invent a chemical name, a scheme name, a price, or a statistic. If you do not know, "
    "say you do not know and suggest who would.\n"
    "3. If the question is outside farming, say briefly that you only help with farming.\n"
    "4. Do not promise outcomes ('this will cure it'). Say what to do and what to watch for.\n"
    "\n"
    "Be practical: WHAT to do, WHEN, and what to look for afterwards."
)


class SelfHostedCopilotError(RuntimeError):
    """Endpoint unreachable or refused — the API layer falls back to the mock, labelled."""


def _context_block(context: CopilotContext) -> str:
    bits: list[str] = []
    if context.crop:
        bits.append(f"Crop: {context.crop}")
    if context.disease:
        bits.append(f"Diagnosed problem: {context.disease}")
    if context.severity_level:
        pct = f" ({context.severity_pct:.0f}% affected)" if context.severity_pct else ""
        bits.append(f"Severity: {context.severity_level}{pct}")
    for snippet in context.kb_snippets[:5]:
        bits.append(f"Reference: {snippet}")
    if not bits:
        return ""
    return (
        "Known facts about this farmer's field. Use them; do not contradict them:\n"
        + "\n".join(f"- {b}" for b in bits)
    )


class SelfHostedCopilot:
    """Any OpenAI-compatible chat endpoint."""

    def __init__(self) -> None:
        self.base_url = (settings.llm_base_url or "").rstrip("/")
        self.api_key = settings.llm_api_key
        self.model = settings.llm_model
        self.timeout_s = settings.llm_timeout_s

    @property
    def model_version(self) -> str:
        return f"selfhosted:{self.model}"

    async def answer(self, user_text: str, context: CopilotContext, lang: str = "mr") -> str:
        if not self.base_url:
            raise SelfHostedCopilotError("LLM_BASE_URL is not set")

        system = SYSTEM_TEMPLATE.format(language=LANG_NAMES.get(lang, "Marathi"))
        block = _context_block(context)
        messages = [{"role": "system", "content": system}]
        if block:
            messages.append({"role": "system", "content": block})
        messages.append({"role": "user", "content": user_text})

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.3,          # advice, not creative writing
            "max_tokens": settings.llm_max_tokens,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_s, verify=settings.llm_verify_ssl) as client:
                res = await client.post(
                    f"{self.base_url}/chat/completions", headers=headers, json=payload
                )
        except httpx.HTTPError as exc:
            raise SelfHostedCopilotError(f"llm unreachable: {exc}") from exc

        if res.status_code in (401, 403):
            raise SelfHostedCopilotError(f"llm rejected the API key ({res.status_code})")
        if res.status_code != 200:
            raise SelfHostedCopilotError(f"llm returned {res.status_code}: {res.text[:200]}")

        try:
            text = res.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError, TypeError) as exc:
            raise SelfHostedCopilotError("llm returned an unexpected body") from exc

        text = (text or "").strip()
        if not text:
            raise SelfHostedCopilotError("llm returned an empty answer")
        return text
