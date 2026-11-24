"""Treatment advisor. v1 templated; becomes LLM + RAG over the agronomy KB (see services/llm)."""
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


class RecommendIn(BaseModel):
    crop: str
    disease: str
    severity_level: str | None = None
    crop_stage: str | None = None
    lang: str = "mr"


@router.post("")
async def recommend(body: RecommendIn) -> dict:
    # TODO (RAG pass): retrieve crop/disease package-of-practices + pesticide labels (dosages ONLY
    # from retrieved sources), condition on severity + stage, generate via Claude in body.lang.
    return {
        "treatment_plan": [
            "रोगट पाने/फळे काढून शेताबाहेर नष्ट करा.",
            "शिफारशीनुसार योग्य बुरशीनाशक/जिवाणूनाशकाची फवारणी करा.",
        ],
        "spray": {"note": "मात्रा (dosage) फक्त अधिकृत लेबलनुसार — KVK चा सल्ला घ्या."},
        "prevention": ["पीक फेरपालट", "योग्य अंतर व निचरा", "रोगमुक्त रोपांची निवड"],
        "followup_days": 7,
        "source_citations": [],
        "disclaimer": "हा सल्ला प्राथमिक आहे. खात्रीसाठी कृषी तज्ज्ञांचा सल्ला घ्या.",
    }
