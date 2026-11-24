"""Real copilot via Claude (Anthropic SDK).

Uses the official `anthropic` async SDK; the model comes from settings.anthropic_model.

The dosage rule below is the same locked policy `knowledge.py` enforces in data. It used to read
"give a dose if you are confident", which quietly contradicted the vision module: the diagnosis
screen refused to print a quantity while the chatbot beside it would happily invent one. Adaptive thinking is on so Claude self-moderates reasoning depth per
question; `effort: medium` keeps latency/cost reasonable for farmers on weak networks.

The Anthropic key stays server-side (this runs in the FastAPI backend, never in the app).
RAG grounding (context.kb_snippets) is wired through; retrieval itself is implemented in rag.py.
"""
from functools import lru_cache

from anthropic import AsyncAnthropic

from app.core.config import settings
from app.services.llm.base import CopilotContext

LANG_NAMES = {"mr": "Marathi", "hi": "Hindi", "en": "English"}

SYSTEM_TEMPLATE = (
    "You are KrushiMitra, an expert AI agronomist helping smallholder farmers in Maharashtra, "
    "India who grow onion (कांदा), soybean (सोयाबीन), and pomegranate (डाळिंब).\n"
    "- Reply ONLY in {language}. Use simple, everyday words a farmer understands; short sentences.\n"
    "- Be concise and practical: say WHAT to do, HOW MUCH, and WHEN.\n"
    "- DOSAGES: NEVER state a quantity, dilution or spray volume — not grams, not ml, not "
    "'per litre', not 'per acre'. Name the ACTIVE INGREDIENT and the cultural steps, then send the "
    "farmer to their Krishi Vigyan Kendra (KVK) or Krishi Seva Kendra for the number. The right "
    "dose depends on the formulation percentage printed on a bottle you cannot see; a wrong number "
    "poisons a crop or a person. Never invent a chemical name.\n"
    "- For a serious disease, end by advising them to confirm with a local agriculture expert."
)


@lru_cache
def _client() -> AsyncAnthropic:
    # Cached singleton; reused across requests.
    return AsyncAnthropic(api_key=settings.anthropic_api_key)


def _build_grounding(context: CopilotContext) -> str:
    parts: list[str] = []
    if context.crop:
        parts.append(f"crop = {context.crop}")
    if context.disease:
        parts.append(f"likely disease (from photo) = {context.disease}")
    if context.severity_level:
        pct = f" ({context.severity_pct}%)" if context.severity_pct is not None else ""
        parts.append(f"severity = {context.severity_level}{pct}")
    if context.kb_snippets:
        parts.append("Reference facts:\n" + "\n".join(f"- {s}" for s in context.kb_snippets))
    if not parts:
        return ""
    return (
        "[Context from the crop photo analysis and knowledge base — use this in your answer]\n"
        + "\n".join(parts)
        + "\n\nFarmer's question: "
    )


class ClaudeCopilot:
    async def answer(self, user_text: str, context: CopilotContext, lang: str = "mr") -> str:
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")

        language = LANG_NAMES.get(lang, "Marathi")
        grounding = _build_grounding(context)
        user_content = f"{grounding}{user_text}".strip() or "नमस्कार"

        response = await _client().messages.create(
            model=settings.anthropic_model,
            max_tokens=4096,
            system=SYSTEM_TEMPLATE.format(language=language),
            thinking={"type": "adaptive"},
            output_config={"effort": "medium"},
            messages=[{"role": "user", "content": user_content}],
        )

        if response.stop_reason == "refusal":
            return "माफ करा, या प्रश्नाचे उत्तर मी देऊ शकत नाही. कृपया जवळच्या कृषी तज्ज्ञांचा सल्ला घ्या."

        # Concatenate text blocks (thinking blocks are separate and skipped).
        return "".join(b.text for b in response.content if b.type == "text").strip()
