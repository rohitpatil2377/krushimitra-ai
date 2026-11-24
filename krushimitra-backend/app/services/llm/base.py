from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class CopilotContext:
    """Everything the copilot can use to ground its answer."""
    crop: str | None = None
    disease: str | None = None
    severity_level: str | None = None
    severity_pct: float | None = None
    kb_snippets: list[str] = field(default_factory=list)
    citations: list[dict] = field(default_factory=list)


class Copilot(Protocol):
    """Generates the farmer-facing answer. mock -> Claude + RAG.

    `lang` is the user's language; the real impl reasons in English internally and outputs `lang`.
    """

    async def answer(self, user_text: str, context: CopilotContext, lang: str = "mr") -> str: ...
