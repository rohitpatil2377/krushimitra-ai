"""Copilot provider selection and the dosage policy in the prompts.

The dosage rule is the one place a chatbot can quietly undo the whole product's safety story:
the vision module refuses to print a quantity, so a chat reply inventing "२ ग्रॅम प्रति लिटर"
beside it is worse than useless. These assertions pin the rule into both system prompts.
"""
from app.core.config import settings
from app.services.llm import get_copilot
from app.services.llm.mock import MockCopilot
from app.services.llm.selfhosted import SYSTEM_TEMPLATE, SelfHostedCopilot, _context_block
from app.services.llm.base import CopilotContext


def test_no_endpoint_means_mock():
    assert isinstance(get_copilot(), MockCopilot)
    assert settings.active_copilot_provider == "mock"


def test_a_self_hosted_endpoint_is_preferred_over_a_billable_api(monkeypatch):
    monkeypatch.setattr(settings, "llm_base_url", "http://localhost:11434/v1")
    assert settings.self_hosted_llm_live is True
    assert isinstance(get_copilot(), SelfHostedCopilot)
    assert settings.active_copilot_provider.startswith("selfhosted:")


def test_self_hosted_prompt_forbids_every_dosage_unit():
    prompt = SYSTEM_TEMPLATE.format(language="Marathi")
    assert "NEVER state a pesticide or fungicide quantity" in prompt
    for unit in ("grams", "ml", "per litre", "per acre"):
        assert unit in prompt, f"the rule must name {unit} explicitly, or a model will route around it"
    assert "Krishi Vigyan Kendra" in prompt


def test_claude_prompt_carries_the_same_rule():
    """It used to say 'give a dose if you are confident' — which contradicted the vision module."""
    from app.services.llm.claude_copilot import SYSTEM_TEMPLATE as CLAUDE_PROMPT

    assert "NEVER state a quantity" in CLAUDE_PROMPT
    assert "only if it is standard and you are confident" not in CLAUDE_PROMPT


def test_context_block_grounds_the_answer_in_the_actual_field():
    block = _context_block(CopilotContext(
        crop="onion", disease="Purple Blotch", severity_level="moderate", severity_pct=24.0,
    ))
    assert "onion" in block and "Purple Blotch" in block and "moderate" in block
    assert "24%" in block


def test_empty_context_adds_no_noise():
    assert _context_block(CopilotContext()) == ""
