"""End-to-end check of /vision/diagnose against the stub self-hosted model.

See tests/README.md. Usage: PYTHONPATH=. .venv/bin/python tests/test_vision_pipeline.py <tmpdir>
"""
import base64, json, os, pathlib, sys

CAP = pathlib.Path(sys.argv[1]) / "captures"
os.environ.update(
    VISION_BASE_URL="http://127.0.0.1:8077/v1",
    VISION_MODEL="gemma-3-27b-it",
    VISION_API_KEY="stub-key",
    CAPTURE_DIR=str(CAP),
)

import httpx
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
JPEG = base64.b64encode(b"\xff\xd8\xff\xe0" + b"\x00" * 2048 + b"\xff\xd9").decode()


def scenario(**kw):
    httpx.post("http://127.0.0.1:8077/scenario", json=kw, timeout=10).raise_for_status()


def diagnose(crop="onion"):
    r = client.post("/vision/diagnose", json={"image_base64": JPEG, "crop": crop})
    r.raise_for_status()
    return r.json()


def show(title, d, *keys):
    print(f"\n── {title}")
    for k in keys:
        v = d.get(k)
        if isinstance(v, list):
            v = f"[{len(v)} items]" + (f" first={v[0][:48]!r}" if v else "")
        elif isinstance(v, dict):
            v = {kk: v[kk] for kk in ("level", "severity_pct", "risk_level") if kk in v}
        elif isinstance(v, str) and len(v) > 70:
            v = v[:70] + "…"
        print(f"   {k:16} = {v}")


fails: list[str] = []


def check(cond, msg):
    if not cond:
        fails.append(msg)
        print(f"   ✗ FAIL: {msg}")

# 1. Confident call for a disease that is NOT the crop's demo default.
#    This is the regression test for the crop-keyed-advice defect.
scenario(
    detect=json.dumps({
        "label": "onion_stemphylium_blight", "confidence": 0.82,
        "visible_symptoms": "elongated dark olive lesions from the leaf tip downward",
        "alternative": "onion_purple_blotch",
    }),
    severity=json.dumps({
        "affected_area_pct": 18, "stage": "progressing", "spreading": True,
        "evidence": "lesions on roughly a fifth of visible leaf area",
    }),
)
d = diagnose()
show("confident diagnosis", d, "disease_slug", "disease", "confidence", "identified",
     "severity", "treatment", "chemicals", "dose_note", "model_version", "diagnosis_id")
check(d["disease_slug"] == "onion_stemphylium_blight", "advice must follow the DETECTED disease")
check("स्टेम्फिलियम" in d["disease"], "Marathi name must match the detected disease")
check(d["identified"] is True, "confident call should be identified")
check(d["severity"]["level"] == "moderate", "18% should band to moderate")
check(d["severity"]["risk_level"] == "high", "spreading should escalate risk medium->high")
check("मॅन्कोझेब" in " ".join(d["treatment"]), "treatment must be Stemphylium's, not purple blotch's")
check(d["dose_note"] is not None, "naming a chemical requires the KVK dose note")
check(all("प्रमाण" not in t or "KVK" in t for t in d["treatment"]), "no dose in treatment steps")
check(d["model_version"] == "self_hosted:gemma-3-27b-it", "model_version must name the real engine")
check(d["diagnosis_id"] is not None, "photo must be captured for the dataset")
captured_id = d["diagnosis_id"]

# 2. Low confidence -> must abstain, with no treatment and no severity.
scenario(detect=json.dumps({
    "label": "onion_downy_mildew", "confidence": 0.41,
    "visible_symptoms": "faint pale patches, photo is dim", "alternative": None,
}))
d = diagnose()
show("low confidence (0.41)", d, "disease_slug", "disease", "identified", "severity",
     "treatment", "chemicals", "note", "prevention")
check(d["identified"] is False, "below threshold must abstain")
check(d["disease_slug"] == "unknown", "abstain must not name a disease")
check(d["treatment"] == [], "abstain must carry NO treatment")
check(d["chemicals"] == [], "abstain must name no chemicals")
check(d["severity"] is None, "abstain must not show a severity measurement")
check(d["note"] and "खात्री" in d["note"], "abstain must explain itself in Marathi")
check(len(d["prevention"]) >= 3, "abstain should tell the farmer how to retake the photo")

# 3. Not a crop photo.
scenario(detect=json.dumps({"label": "not_a_plant", "confidence": 0.95,
                            "visible_symptoms": "a brick wall", "alternative": None}))
d = diagnose()
show("photo of a wall", d, "disease_slug", "disease", "identified", "treatment", "note")
check(d["identified"] is False and d["disease_slug"] == "not_a_plant", "must report no crop")
check(d["treatment"] == [], "no crop => no treatment")

# 4. Messy real-world reply: markdown fence + confidence as a percentage.
scenario(detect='```json\n{"label": "Purple Blotch", "confidence": 88, '
                '"visible_symptoms": "purple-brown oval lesions with concentric rings", '
                '"alternative": "onion_stemphylium_blight"}\n```',
         severity='Sure! Here is the assessment:\n'
                  '{"affected_area_pct": 0.62, "stage": "advanced", "spreading": false, '
                  '"evidence": "most leaves browning"}')
d = diagnose()
show("fenced JSON + pct confidence", d, "disease_slug", "confidence", "identified", "severity")
check(d["disease_slug"] == "onion_purple_blotch", "free-text label must resolve to a slug")
check(d["confidence"] == 0.88, "confidence 88 must normalise to 0.88")
check(d["severity"]["severity_pct"] == 62.0, "0.62 must normalise to 62%")
check(d["severity"]["level"] == "critical", "62% should band to critical")

# 5. A model that names a disease but reports no symptoms = guessing from the crop name.
scenario(detect=json.dumps({"label": "onion_purple_blotch", "confidence": 0.9,
                            "visible_symptoms": "", "alternative": None}))
d = diagnose()
show("high confidence, no symptoms", d, "disease_slug", "confidence", "identified")
check(d["identified"] is False, "a symptom-free claim must be capped and abstain")

# 6. Healthy crop -> no spray advice.
scenario(detect=json.dumps({"label": "healthy", "confidence": 0.9,
                            "visible_symptoms": "uniform green leaves, no lesions",
                            "alternative": None}))
d = diagnose()
show("healthy", d, "disease_slug", "identified", "severity", "treatment", "chemicals")
check(d["chemicals"] == [], "healthy crop must not be sold chemicals")
check("गरज नाही" in " ".join(d["treatment"]), "healthy must say no spray needed")

# 7. Model server down -> labelled mock, never a crash.
scenario(status=500)
d = diagnose()
show("model server down (HTTP 500)", d, "disease_slug", "identified", "model_version")
check(d["model_version"].startswith("mock"), "degraded answer must be badged as mock")

# 8. Server rejects JSON mode (Ollama behaviour) -> transparent retry.
scenario(status=200, reject_json_mode=True,
         detect=json.dumps({"label": "soybean_rust", "confidence": 0.78,
                            "visible_symptoms": "tan pustules on the lower leaf surface",
                            "alternative": None}),
         severity=json.dumps({"affected_area_pct": 8, "stage": "early", "spreading": False,
                              "evidence": "pustules on two lower leaves"}))
d = diagnose(crop="soybean")
show("server rejects JSON mode", d, "disease_slug", "identified", "severity", "model_version")
check(d["disease_slug"] == "soybean_rust", "must succeed after retrying without JSON mode")
check(d["severity"]["level"] == "mild", "8% should band to mild")

# 9. Feedback loop: the farmer corrects us -> a labelled training example.
r = client.post("/vision/feedback", json={
    "diagnosis_id": captured_id, "was_correct": False,
    "correct_disease": "Purple Blotch", "note": "शेजारी शेतकऱ्याने जांभळा करपा सांगितला",
})
print("\n── feedback")
print("   POST /vision/feedback ->", r.status_code, r.json())
check(r.status_code == 200, "feedback must be accepted")
bad = client.post("/vision/feedback", json={"diagnosis_id": "../../etc/passwd",
                                            "was_correct": True})
print("   path-traversal id    ->", bad.status_code)
check(bad.status_code == 404, "malformed diagnosis_id must be rejected")

stats = client.get("/vision/dataset").json()
print("   GET /vision/dataset  ->", stats)
check(stats["captured"] >= 8, "every diagnosed photo must be captured")
check(stats["corrections"] == 1, "the correction must be recorded")

saved = json.loads(next(CAP.rglob(f"{captured_id}.json")).read_text(encoding="utf-8"))
print("\n── captured record (abridged)")
for k in ("predicted_slug", "predicted_confidence", "shown_slug", "identified",
          "abstain_reason", "severity_pct", "provider"):
    print(f"   {k:22} = {saved.get(k)}")
fb = json.loads(next(CAP.rglob(f"{captured_id}.feedback.json")).read_text(encoding="utf-8"))
print("   farmer correction      =", fb["correct_disease"], "| was_correct:", fb["was_correct"])
check(fb["correct_disease"] == "onion_purple_blotch", "free-text correction must resolve to a slug")

print("\n" + "=" * 62)
print(f"RESULT: {'ALL CHECKS PASSED' if not fails else str(len(fails)) + ' FAILED'}")
for f in fails:
    print("  ✗", f)
sys.exit(1 if fails else 0)
