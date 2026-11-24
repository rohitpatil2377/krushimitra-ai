from app.services.llm.base import CopilotContext

# Minimal keyword copilot so /copilot/ask returns sensible Marathi text with no LLM key.
_TIPS = {
    "पाणी": "जमिनीतील ओलावा तपासा; वरचा थर कोरडा वाटल्यास सकाळी पाणी द्या. ठिबक सिंचन वापरल्यास बचत होते.",
    "खत": "माती परीक्षणानुसार N-P-K समतोल ठेवा आणि शेणखत/कंपोस्ट वापरा.",
    "रोग": "रोगट पाने काढून नष्ट करा, हवा खेळती ठेवा आणि गरजेनुसार योग्य फवारणी करा.",
}


class MockCopilot:
    async def answer(self, user_text: str, context: CopilotContext, lang: str = "mr") -> str:
        if context.disease:
            sev = context.severity_level or "—"
            return (
                f"फोटोनुसार बहुधा **{context.disease}** दिसतो (तीव्रता: {sev}). "
                "रोगट भाग काढा, योग्य फवारणी करा आणि ५–७ दिवसांनी पुन्हा फोटो पाठवा. "
                "खात्रीसाठी जवळच्या कृषी तज्ज्ञांचा सल्ला घ्या."
            )
        for key, tip in _TIPS.items():
            if key in user_text:
                return tip
        return (
            "नमस्कार! 🙏 मी कृषीमित्र आहे. पिकाचा फोटो पाठवा किंवा पाणी, खत, रोग, हवामान "
            "याबद्दल विचारा — मी मराठीत मदत करेन."
        )
