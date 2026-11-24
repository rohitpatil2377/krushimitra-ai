"""Copilot factory: Claude + RAG when configured, else mock."""
from app.core.config import settings
from app.services.llm.base import Copilot, CopilotContext
from app.services.llm.mock import MockCopilot

__all__ = ["Copilot", "CopilotContext", "get_copilot"]


def get_copilot() -> Copilot:
    # A self-hosted endpoint is explicit and free; prefer it over a billable API.
    if settings.self_hosted_llm_live:
        from app.services.llm.selfhosted import SelfHostedCopilot

        return SelfHostedCopilot()
    if settings.llm_live:
        from app.services.llm.claude_copilot import ClaudeCopilot

        return ClaudeCopilot()
    return MockCopilot()
