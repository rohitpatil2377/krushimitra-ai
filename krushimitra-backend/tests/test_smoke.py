"""Smoke tests that need no database — verify the app boots and the copilot works on mocks."""

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_copilot_text():
    r = client.post("/copilot/ask", data={"text": "कांद्याला किती पाणी द्यावे?", "lang": "mr"})
    assert r.status_code == 200
    body = r.json()
    assert body["reply_text"]
    assert body["lang"] == "mr"


def test_vision_diagnose():
    """On mocks: a result comes back, keyed by slug, and is honestly badged as sample data."""
    import base64

    payload = {"image_base64": base64.b64encode(b"fake-bytes").decode(), "crop": "pomegranate"}
    r = client.post("/vision/diagnose", json=payload)
    assert r.status_code == 200
    body = r.json()
    # Assert the slug, not the display name — the slug is the stable contract.
    assert body["disease_slug"] == "pomegranate_bacterial_blight"
    assert body["severity"]["level"]
    assert body["treatment"] and body["prevention"]
    # Sample data must say so, or the app badge is a lie.
    assert body["model_version"].startswith("mock")
    # Naming a chemical obliges us to carry the KVK dosage disclaimer.
    assert body["chemicals"] and body["dose_note"]


def test_vision_rejects_bad_image():
    r = client.post("/vision/diagnose", json={"image_base64": "not base64!!", "crop": "onion"})
    assert r.status_code == 422


def test_knowledge_is_keyed_by_disease_not_crop():
    """The regression guard: two onion diseases must give different advice."""
    from app.services.knowledge import lookup

    purple = lookup("onion_purple_blotch")
    stemphylium = lookup("onion_stemphylium_blight")
    assert purple.treatment != stemphylium.treatment


def test_abstain_carries_no_advice():
    from app.services.knowledge import lookup

    for slug in ("unknown", "not_a_plant", "no-such-disease"):
        assert lookup(slug).treatment == (), f"{slug} must not carry treatment"
